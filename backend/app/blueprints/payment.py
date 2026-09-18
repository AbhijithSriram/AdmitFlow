import os
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, request, session

from app.extensions import db
from app.middleware.auth_guard import login_required
from app.models import Application, FormDraft, Payment, Student
from app.services import email_service, minio_service, payment_service, pdf_service

payment_bp = Blueprint("payment", __name__)

# Application fee in paise (Razorpay's smallest currency unit for INR). Overridable via
# .env so the team can change it without touching code; defaults to Rs. 1000.
APPLICATION_FEE_PAISE = int(os.environ.get("APPLICATION_FEE_PAISE", 100000))


def _current_student_and_application():
    student_id = session["student_id"]
    student = db.session.get(Student, student_id)
    application = Application.query.filter_by(student_id=student_id).first()
    return student, application


def _collect_form_data(application_id: str) -> dict:
    """Merge every saved step's JSONB draft into one dict, for the PDF and the
    frontend's read-only preview. Deliberately generic: it doesn't assume any
    particular field names, since those belong to Steps 1-6 (Person 2's file)."""
    drafts = FormDraft.query.filter_by(application_id=application_id).order_by(FormDraft.step_number).all()
    merged: dict = {}
    for draft in drafts:
        merged.update(draft.data or {})
    return merged


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
    _, application = _current_student_and_application()

    if application is None:
        return jsonify({"success": False, "error": "Start your application before paying"}), 400
    if application.status == "PAID":
        return jsonify({"success": False, "error": "This application has already been paid for"}), 400

    # Razorpay is an external service — a bad key, network blip, or Razorpay-side outage
    # must not crash the request with a raw 500. It's logged and reported cleanly instead,
    # consistent with every other endpoint's {success, error} envelope (SRD NFR-4).
    try:
        order = payment_service.create_order(
            amount_paise=APPLICATION_FEE_PAISE,
            receipt=f"admitflow-{application.id}",
        )
    except Exception:
        current_app.logger.exception("Razorpay order creation failed for application %s", application.id)
        return jsonify({"success": False, "error": "Payment gateway unavailable. Try again shortly."}), 502

    payment = Payment(
        application_id=application.id,
        razorpay_order_id=order["id"],
        amount=Decimal(APPLICATION_FEE_PAISE) / 100,
        status="CREATED",
    )
    db.session.add(payment)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "data": {"id": order["id"], "amount": order["amount"], "currency": order["currency"]},
            }
        ),
        201,
    )


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

    if not payment_service.verify_signature(order_id, razorpay_payment_id, signature):
        payment.status = "FAILED"
        application.status = "PAYMENT_PENDING"
        db.session.commit()
        return jsonify({"success": False, "error": "Payment verification failed"}), 400

    # Payment.status and Application.status flip together, committed once, so a
    # half-applied state (paid in one table but not the other) can never be observed.
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = signature
    payment.status = "SUCCESS"
    application.status = "PAID"
    db.session.commit()

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

    if order_id:
        payment = Payment.query.filter_by(application_id=application.id, razorpay_order_id=order_id).first()
        if payment:
            payment.status = "FAILED"

    application.status = "PAYMENT_PENDING"
    db.session.commit()

    return jsonify({"success": True, "data": {"status": application.status}})


@payment_bp.route("/app/receipt/<application_id>", methods=["GET"])
@login_required
def get_receipt(application_id):
    """Return a presigned URL to the receipt / application PDF."""
    student_id = session["student_id"]
    # Scoped to the logged-in student's own id, not just the application id in the
    # URL, so one student can't read another's receipt by guessing a UUID.
    application = Application.query.filter_by(id=application_id, student_id=student_id).first()

    if application is None:
        return jsonify({"success": False, "error": "Application not found"}), 404
    if not application.pdf_url:
        return jsonify({"success": False, "error": "Receipt not available yet"}), 404

    url = minio_service.get_presigned_url(application.pdf_url)
    return jsonify({"success": True, "data": {"url": url}})


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
                "institution_name": "AdmitFlow Institute",
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
            {
                "institution_name": "AdmitFlow Institute",
                "full_name": student.full_name,
                "programme": application.programme,
                "amount": payment.amount,
                "payment_id": payment.razorpay_payment_id,
                "order_id": payment.razorpay_order_id,
                "paid_on": datetime.utcnow().strftime("%d %b %Y, %H:%M UTC"),
            }
        )

        email_service.send_payment_confirmation_email(
            student.email,
            pdf_bytes,
            receipt_bytes,
            context={"full_name": student.full_name, "programme": application.programme},
        )
    except Exception:
        current_app.logger.exception("Post-payment PDF/email delivery failed for application %s", application.id)
