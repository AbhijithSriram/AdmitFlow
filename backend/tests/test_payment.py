"""Payment, dashboard and receipt routes (SRD FR-5, FR-6.9, FR-8, FR-9) against real PostgreSQL."""
import hashlib
import hmac
import io

import pytest

from app.extensions import db
from app.models import Application, FormDraft, Payment, Student

SECRET = "test_secret"


def _login_as(client, student):
    with client.session_transaction() as sess:
        sess["student_id"] = student.id


def _sign(order_id, payment_id):
    return hmac.new(SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def _application_of(student):
    return Application.query.filter_by(student_id=student.id).first()


def _add_created_payment(student, order_id="order_1"):
    application = _application_of(student)
    db.session.add(Payment(application_id=application.id, razorpay_order_id=order_id, amount=1000, status="CREATED"))
    db.session.commit()
    return application


@pytest.fixture(autouse=True)
def razorpay_secret(app, monkeypatch):
    monkeypatch.setitem(app.config, "RAZORPAY_KEY_SECRET", SECRET)


@pytest.fixture
def no_delivery(monkeypatch):
    """Skip PDF generation / MinIO / SMTP for tests that only care about payment state."""
    from app.blueprints import payment

    monkeypatch.setattr(payment, "_generate_and_deliver_confirmation", lambda *a, **k: None)


# ---------------------------------------------------------------- dashboard
def test_dashboard_requires_login(client):
    assert client.get("/api/student/dashboard").status_code == 401


def test_dashboard_for_student_who_has_not_started(client, make_student):
    student = make_student(status=None)
    _login_as(client, student)

    data = client.get("/api/student/dashboard").get_json()["data"]

    assert data["status"] == "NOT_STARTED"
    assert data["application_id"] is None
    assert data["has_receipt"] is False


def test_dashboard_reports_status_and_programme(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    _login_as(client, student)

    data = client.get("/api/student/dashboard").get_json()["data"]

    assert data["status"] == "IN_PROGRESS"
    assert data["programme"] == "B.Tech"
    assert data["application_id"] == str(_application_of(student).id)
    assert data["has_receipt"] is False


def test_session_of_a_deleted_student_is_treated_as_logged_out(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    _login_as(client, student)
    db.session.delete(db.session.get(Student, student.id))  # e.g. an admin hard-delete
    db.session.commit()

    assert client.get("/api/student/dashboard").status_code == 401
    assert client.get("/api/auth/me").status_code == 401  # the stale session was cleared, not just rejected


# ------------------------------------------------------------- create-order
def test_create_order_records_a_created_payment(client, make_student, monkeypatch):
    from app.services import payment_service

    monkeypatch.setattr(payment_service, "create_order",
                        lambda amount_paise, receipt: {"id": "order_1", "amount": amount_paise, "currency": "INR"})
    student = make_student(status="IN_PROGRESS", files=False)
    _login_as(client, student)

    resp = client.post("/api/app/payment/create-order")

    assert resp.status_code == 201
    data = resp.get_json()["data"]
    assert (data["id"], data["amount"], data["currency"]) == ("order_1", 100000, "INR")
    # the checkout pre-fills these so the student isn't asked for them again
    assert data["prefill"] == {"name": student.full_name, "email": student.email, "contact": student.phone}
    payment = Payment.query.filter_by(razorpay_order_id="order_1").one()
    assert payment.status == "CREATED"
    assert float(payment.amount) == 1000.0


def test_create_order_needs_an_application(client, make_student):
    _login_as(client, make_student(status=None))
    assert client.post("/api/app/payment/create-order").status_code == 400


def test_create_order_refused_when_already_paid(client, make_student):
    _login_as(client, make_student(status="PAID", files=False))
    resp = client.post("/api/app/payment/create-order")
    assert resp.status_code == 400
    assert "already" in resp.get_json()["error"]


def test_gateway_failure_is_a_clean_502_and_creates_no_payment(client, make_student, monkeypatch):
    from app.services import payment_service

    def boom(amount_paise, receipt):
        raise RuntimeError("razorpay down")

    monkeypatch.setattr(payment_service, "create_order", boom)
    _login_as(client, make_student(status="IN_PROGRESS", files=False))

    resp = client.post("/api/app/payment/create-order")

    assert resp.status_code == 502
    assert resp.get_json()["success"] is False
    assert Payment.query.count() == 0


# ------------------------------------------------------------------ confirm
def test_confirm_needs_all_fields(client, make_student):
    _login_as(client, make_student(status="IN_PROGRESS", files=False))
    assert client.post("/api/app/payment/confirm", json={"razorpay_order_id": "order_1"}).status_code == 400


def test_forged_signature_is_rejected_and_nothing_is_marked_paid(client, make_student, no_delivery):
    student = make_student(status="IN_PROGRESS", files=False)
    _add_created_payment(student)
    _login_as(client, student)

    resp = client.post("/api/app/payment/confirm", json={
        "razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1", "razorpay_signature": "deadbeef"})

    assert resp.status_code == 400
    assert _application_of(student).status == "PAYMENT_PENDING"
    assert Payment.query.filter_by(razorpay_order_id="order_1").one().status == "FAILED"


def test_valid_signature_marks_payment_and_application_paid_together(client, make_student, no_delivery):
    student = make_student(status="IN_PROGRESS", files=False)
    _add_created_payment(student)
    _login_as(client, student)

    resp = client.post("/api/app/payment/confirm", json={
        "razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1",
        "razorpay_signature": _sign("order_1", "pay_1")})

    assert resp.status_code == 200
    assert _application_of(student).status == "PAID"
    payment = Payment.query.filter_by(razorpay_order_id="order_1").one()
    assert (payment.status, payment.razorpay_payment_id) == ("SUCCESS", "pay_1")


def test_a_student_cannot_confirm_someone_elses_order(client, make_student, no_delivery):
    owner = make_student(status="IN_PROGRESS", files=False)
    _add_created_payment(owner)
    attacker = make_student(status="IN_PROGRESS", files=False)
    _login_as(client, attacker)

    resp = client.post("/api/app/payment/confirm", json={
        "razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1",
        "razorpay_signature": _sign("order_1", "pay_1")})

    assert resp.status_code == 404
    assert _application_of(owner).status == "IN_PROGRESS"
    assert _application_of(attacker).status == "IN_PROGRESS"


def test_pdf_failure_after_payment_does_not_undo_the_payment(client, make_student, fake_minio, monkeypatch):
    from app.services import pdf_service

    def boom(context):
        raise RuntimeError("pdf engine broke")

    monkeypatch.setattr(pdf_service, "render_application_pdf", boom)
    student = make_student(status="IN_PROGRESS", files=False)
    _add_created_payment(student)
    _login_as(client, student)

    resp = client.post("/api/app/payment/confirm", json={
        "razorpay_order_id": "order_1", "razorpay_payment_id": "pay_1",
        "razorpay_signature": _sign("order_1", "pay_1")})

    assert resp.status_code == 200
    assert _application_of(student).status == "PAID"


# ------------------------------------------------------------------- failed
def test_failed_payment_sets_payment_pending(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    _add_created_payment(student)
    _login_as(client, student)

    resp = client.post("/api/app/payment/failed", json={"order_id": "order_1", "dismissed": True})

    assert resp.status_code == 200
    assert _application_of(student).status == "PAYMENT_PENDING"
    assert Payment.query.filter_by(razorpay_order_id="order_1").one().status == "FAILED"


# ------------------------------------------------------------------ receipt
def test_receipt_returns_a_presigned_url_to_the_owner_only(client, make_student, fake_minio):
    owner = make_student(status="PAID", files=True)
    other = make_student(status="PAID", files=True)
    application = _application_of(owner)

    _login_as(client, owner)
    resp = client.get(f"/api/app/receipt/{application.id}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["url"].startswith("http://minio.test/")

    _login_as(client, other)
    assert client.get(f"/api/app/receipt/{application.id}").status_code == 404


def test_receipt_not_available_before_a_pdf_exists(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    _login_as(client, student)
    assert client.get(f"/api/app/receipt/{_application_of(student).id}").status_code == 404


# ------------------------------------------------- PDF content and edit lock
def test_form_data_is_grouped_by_step_so_repeated_field_names_survive(client, make_student):
    from app.blueprints.payment import _collect_form_data
    from app.services import pdf_service

    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    FormDraft.query.filter_by(application_id=application.id).delete()
    db.session.add(FormDraft(application_id=application.id, step_number=4, data={"score": "8.7"}))
    db.session.add(FormDraft(application_id=application.id, step_number=5, data={"score": "88"}))
    db.session.commit()

    grouped = _collect_form_data(application.id)

    assert grouped == {"Academic Details": {"score": "8.7"}, "Entrance / Test Details": {"score": "88"}}
    html = pdf_service._rows_html(grouped)
    assert "8.7" in html and "88" in html  # a flat merge would have kept only one of them


def test_pdf_labels_are_readable_and_values_are_escaped():
    from app.services import pdf_service

    html = pdf_service._rows_html({"Personal Details": {"father_name": "<b>R</b> & S", "address": {"line_1": "x"}}})

    assert "Father name" in html and "Address / Line 1" in html
    assert "&lt;b&gt;R&lt;/b&gt; &amp; S" in html
    assert "<b>R</b>" not in html


def test_paid_application_can_no_longer_be_edited(client, make_student, fake_minio):
    student = make_student(status="PAID", files=False)
    application = _application_of(student)
    _login_as(client, student)

    patch = client.patch(f"/api/app/draft/{application.id}/step/1", json={"full_name": "Changed after paying"})
    upload = client.post(
        f"/api/app/upload/{application.id}/photo",
        data={"file": (io.BytesIO(b"x"), "a.png")},
        content_type="multipart/form-data",
    )

    assert patch.status_code == 409
    assert upload.status_code == 409
    assert FormDraft.query.filter_by(application_id=application.id, step_number=1).one().data == {"father_name": "R"}


def test_unpaid_application_can_still_be_edited(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.patch(f"/api/app/draft/{application.id}/step/1", json={"father_name": "Updated"})

    assert resp.status_code == 200


def test_internal_storage_keys_are_not_printed_on_the_application(client, make_student):
    from app.blueprints.payment import _collect_form_data

    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    FormDraft.query.filter_by(application_id=application.id).delete()
    db.session.add(FormDraft(application_id=application.id, step_number=6, data={
        "id_proof_type": "Aadhaar",
        "photo_url": "applications/abc/photo.png",
        "signature_url": "applications/abc/signature.png",
        "id_proof_url": "applications/abc/id_proof.pdf",
    }))
    db.session.commit()

    assert _collect_form_data(application.id) == {"Documents": {"id_proof_type": "Aadhaar"}}


def test_pdf_labels_expand_abbreviations():
    from app.services import pdf_service

    html = pdf_service._rows_html({"Address Details": {"comm_line1": "x", "perm_pincode": "600001"},
                                   "Personal Details": {"ews": "No"},
                                   "Academic Details": {"ug_degree": "B.E."},
                                   "Documents": {"id_proof_type": "Aadhaar"}})

    for label in ("Communication line 1", "Permanent pincode", "EWS", "UG degree", "ID proof type"):
        assert f"<td class='label'>{label}</td>" in html
