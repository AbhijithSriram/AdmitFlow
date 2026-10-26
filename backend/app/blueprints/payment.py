import logging
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, abort, current_app, jsonify, make_response, redirect, request, session

from app.extensions import db, limiter
from app.middleware.auth_guard import login_required
from app.models import Application, FormDraft, Payment, Student
from app.services import content_service, email_service, form_fields, minio_service, payment_service, pdf_service
from app.services.admin_service import is_uuid

log = logging.getLogger(__name__)
payment_bp = Blueprint("payment", __name__)

# The application fee is site content an admin edits (content_service, section "fee"), in rupees;
# Razorpay wants paise (its smallest unit for INR).


def _current_student_and_application():
    student_id = session["student_id"]
    student = db.session.get(Student, student_id)
    if student is None:
        # The session outlived the student (e.g. an admin hard-deleted them while they
        # were still logged in). Treat it as logged out, like /api/auth/me does.
        session.clear()
        abort(make_response(jsonify({"success": False, "error": "Not authenticated"}), 401))
    application = Application.query.filter_by(student_id=student_id).first()
    return student, application


STEP_TITLES = {
    1: "Personal Details",
    2: "Address Details",
    3: "Programme Preference",
    4: "Academic Details",
    5: "Entrance / Test Details",
    6: "Documents",
}


def _collect_form_data(application_id: str) -> dict:
    """Each saved step's fields, grouped under that step's title, for the PDF.

    Grouped rather than merged: different steps reuse field names (e.g. `score` in Steps 3
    and 5, `state` in Steps 1 and 2), and merging would silently overwrite one with the
    other. Still generic about the fields themselves, which belong to Person 2's steps."""
    drafts = FormDraft.query.filter_by(application_id=application_id).order_by(FormDraft.step_number).all()
    sections = {}
    for draft in drafts:
        # `*_url` entries are internal storage keys (applications/<id>/photo.png), not
        # something an applicant should see printed on their application.
        # form_fields also puts them back in the form's order with readable labels (JSONB sorts keys).
        rows = form_fields.ordered_rows(draft.step_number, draft.data)
        if rows:
            sections[STEP_TITLES.get(draft.step_number, f"Step {draft.step_number}")] = rows
    return sections


@payment_bp.route("/student/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Return application status and navigation data for the logged-in student."""
    student, application = _current_student_and_application()

    return jsonify(
        {
            "success": True,
            "data": {
                "full_name": student.full_name,
                "status": application.status if application else "NOT_STARTED",
                "application_id": application.id if application else None,
                "programme": application.programme if application else None,
                "specialisation": application.specialisation if application else None,
                "has_receipt": bool(application and application.pdf_url),
            },
        }
    )


@payment_bp.route("/app/payment/create-order", methods=["POST"])
@login_required
def create_payment_order():
    """Create a Razorpay order and return the order ID."""
    student, application = _current_student_and_application()

    if application is None:
        return jsonify({"success": False, "error": "Start your application before paying"}), 400
    if application.status == "PAID":
        return jsonify({"success": False, "error": "This application has already been paid for"}), 400

    # Razorpay is an external service — a bad key, network blip, or Razorpay-side outage
    # must not crash the request with a raw 500. It's logged and reported cleanly instead,
    # consistent with every other endpoint's {success, error} envelope (SRD NFR-4).
    fee_paise = content_service.fee_paise()
    try:
        order = payment_service.create_order(
            amount_paise=fee_paise,
            receipt=f"admitflow-{application.id}",
        )
    except Exception:
        current_app.logger.exception("Razorpay order creation failed for application %s", application.id)
        return jsonify({"success": False, "error": "Payment gateway unavailable. Try again shortly."}), 502

    payment = Payment(
        application_id=application.id,
        razorpay_order_id=order["id"],
        amount=Decimal(fee_paise) / 100,
        status="CREATED",
    )
    db.session.add(payment)
    db.session.commit()
    log.info("payment order created order=%s application=%s amount_paise=%s",
             order["id"], application.id, fee_paise)

    return (
        jsonify(
            {
                "success": True,
                "data": {
                    "id": order["id"],
                    "amount": order["amount"],
                    "currency": order["currency"],
                    # Lets the checkout pre-fill these instead of asking the student again.
                    "prefill": {"name": student.full_name, "email": student.email, "contact": student.phone},
                },
            }
        ),
        201,
    )


def _mark_attempt_failed(application: Application, payment) -> bool:
    """Record a failed attempt without ever undoing a success. The payment becomes FAILED only if it
    is still just CREATED, and an IN_PROGRESS application becomes PAYMENT_PENDING (a PAID one is left
    alone, a PAYMENT_PENDING one already is). Returns True if anything changed."""
    changed = False
    if payment is not None and payment.status == "CREATED":
        payment.status = "FAILED"
        changed = True
    if application.status == "IN_PROGRESS":
        application.status = "PAYMENT_PENDING"
        changed = True
    return changed


@payment_bp.route("/app/payment/confirm", methods=["POST"])
@login_required
def confirm_payment():
    """Verify the Razorpay signature server-side and mark payment SUCCESS."""
    body = request.get_json(silent=True) or {}
    order_id = body.get("razorpay_order_id")
    razorpay_payment_id = body.get("razorpay_payment_id")
    signature = body.get("razorpay_signature")

    if not (order_id and razorpay_payment_id and signature):
        return jsonify({"success": False, "error": "Missing payment fields"}), 400

    student, application = _current_student_and_application()
    if application is None:
        return jsonify({"success": False, "error": "No application found"}), 404

    payment = Payment.query.filter_by(application_id=application.id, razorpay_order_id=order_id).first()
    if payment is None:
        return jsonify({"success": False, "error": "Unknown order"}), 404

    # A repeat of a confirmation we already processed (double click, a retried request): answer
    # the same way and do nothing again, so the applicant is not emailed a second time.
    if payment.status == "SUCCESS":
        log.info("payment confirm repeated order=%s application=%s", order_id, application.id)
        return jsonify({"success": True, "data": {"status": application.status}})

    if not payment_service.verify_signature(order_id, razorpay_payment_id, signature):
        log.warning("payment signature verification failed order=%s application=%s", order_id, application.id)
        _mark_attempt_failed(application, payment)
        db.session.commit()
        return jsonify({"success": False, "error": "Payment verification failed"}), 400

    # Payment.status and Application.status flip together, committed once, so a
    # half-applied state (paid in one table but not the other) can never be observed.
    first_payment = application.status != "PAID"
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = signature
    payment.status = "SUCCESS"
    application.status = "PAID"
    db.session.commit()

    if not first_payment:
        # The application was already paid through another order, so this applicant was charged twice.
        # The payment is recorded (so it can be refunded) but nothing is generated or sent again.
        log.warning("second successful payment for an already paid application order=%s application=%s",
                    order_id, application.id)
        return jsonify({"success": True, "data": {"status": application.status}})

    log.info("payment confirmed order=%s payment=%s application=%s", order_id, razorpay_payment_id, application.id)
    _generate_and_deliver_confirmation(student, application, payment)

    return jsonify({"success": True, "data": {"status": application.status}})


@payment_bp.route("/app/payment/failed", methods=["POST"])
@login_required
def payment_failed():
    """Record a failed payment attempt; application status becomes PAYMENT_PENDING."""
    body = request.get_json(silent=True) or {}
    order_id = body.get("razorpay_order_id") or body.get("order_id")

    _, application = _current_student_and_application()
    if application is None:
        return jsonify({"success": False, "error": "No application found"}), 404

    payment = None
    if order_id:
        payment = Payment.query.filter_by(application_id=application.id, razorpay_order_id=order_id).first()

    # The checkout can report a dismissal or failure after the payment already went through (or a
    # request can simply be replayed): a paid application and a successful payment never go backwards.
    if _mark_attempt_failed(application, payment):
        log.info("payment attempt failed order=%s application=%s", order_id, application.id)
    db.session.commit()

    return jsonify({"success": True, "data": {"status": application.status}})


@payment_bp.route("/app/receipt/<application_id>", methods=["GET"])
@login_required
def get_receipt(application_id):
    """Return a presigned URL to the receipt / application PDF."""
    student_id = session["student_id"]
    # Scoped to the logged-in student's own id, not just the application id in the
    # URL, so one student can't read another's receipt by guessing a UUID.
    application = _own_application(application_id, student_id)

    if application is None:
        return jsonify({"success": False, "error": "Application not found"}), 404
    if not application.pdf_url:
        return jsonify({"success": False, "error": "Receipt not available yet"}), 404

    url = minio_service.get_presigned_url(application.pdf_url)
    return jsonify({"success": True, "data": {"url": url}})


@payment_bp.route("/app/application-pdf/<application_id>", methods=["GET"])
@login_required
def open_application_pdf(application_id):
    """The application PDF (SRD FR-8: downloadable from the dashboard), as a plain link: redirects to
    a 15-minute presigned URL, so the browser opens it directly and no popup blocker gets in the way."""
    application = _own_application(application_id, session["student_id"])
    if application is None or not application.pdf_url:
        return jsonify({"success": False, "error": "Application PDF not available yet"}), 404
    return redirect(minio_service.get_presigned_url(application.pdf_url), code=302)


@payment_bp.route("/app/receipt/<application_id>/pdf", methods=["GET"])
@login_required
@limiter.limit("20 per minute")  # rendered on every request, like the brochure
def get_fee_receipt_pdf(application_id):
    """The fee receipt (amount, payment and order ids), built from the successful payment each time
    it is asked for, so every paid applicant has one and nothing extra is stored. A plain link opens
    it: no popup, and the session cookie scopes it to its owner."""
    application = _own_application(application_id, session["student_id"])
    payment = None
    if application is not None:
        payment = (Payment.query.filter_by(application_id=application.id, status="SUCCESS")
                   .order_by(Payment.created_at.desc()).first())
    if payment is None:
        return jsonify({"success": False, "error": "Receipt not available yet"}), 404

    student = db.session.get(Student, application.student_id)
    pdf = pdf_service.render_receipt_pdf(_receipt_context(student, application, payment, payment.created_at))
    response = make_response(pdf)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = 'inline; filename="admitflow-fee-receipt.pdf"'
    return response


def _own_application(application_id, student_id):
    """The signed-in student's application with this id, or None. A malformed id is just "not
    found": passed to PostgreSQL it would fail the uuid cast and surface as a 500."""
    if not is_uuid(application_id):
        return None
    return Application.query.filter_by(id=application_id, student_id=student_id).first()


def _receipt_context(student: Student, application: Application, payment: Payment, paid_on: datetime) -> dict:
    return {
        "institution_name": content_service.institution_name(),
        "demo_footer": content_service.demo_footer(),
        "full_name": student.full_name,
        "programme": application.programme,
        "amount": payment.amount,
        "payment_id": payment.razorpay_payment_id,
        "order_id": payment.razorpay_order_id,
        "paid_on": paid_on.strftime("%d %b %Y, %H:%M UTC"),
        # Razorpay test keys start rzp_test_: the receipt then says no real money was charged.
        "test_mode": str(current_app.config.get("RAZORPAY_KEY_ID") or "").startswith("rzp_test_"),
    }


def _generate_and_deliver_confirmation(student: Student, application: Application, payment: Payment) -> None:
    """Render the application PDF + receipt, store the PDF in MinIO, and email both.

    Best-effort by design: the payment was already committed above, so a failure here
    (MinIO or SMTP briefly unreachable) must not undo a successful payment. It's logged
    instead, so delivery can be retried/investigated without re-charging the applicant.
    """
    try:
        form_data = _collect_form_data(application.id)
        photo_url = minio_service.get_presigned_url(application.photo_url) if application.photo_url else None
        signature_url = (
            minio_service.get_presigned_url(application.signature_url) if application.signature_url else None
        )

        pdf_bytes = pdf_service.render_application_pdf(
            {
                "institution_name": content_service.institution_name(),
                "demo_footer": content_service.demo_footer(),
                "full_name": student.full_name,
                "programme": application.programme,
                "specialisation": application.specialisation,
                "payment_reference": payment.razorpay_payment_id,
                "photo_url": photo_url,
                "signature_url": signature_url,
                "form_data": form_data,
            }
        )

        object_name = f"applications/{application.id}/application.pdf"
        minio_service.upload_object(object_name, pdf_bytes, "application/pdf")
        application.pdf_url = object_name
        db.session.commit()

        receipt_bytes = pdf_service.render_receipt_pdf(
            _receipt_context(student, application, payment, datetime.utcnow()))

        email_service.send_payment_confirmation_email(
            student.email,
            pdf_bytes,
            receipt_bytes,
            context={"full_name": student.full_name, "programme": application.programme},
        )
    except Exception:
        current_app.logger.exception("Post-payment PDF/email delivery failed for application %s", application.id)
