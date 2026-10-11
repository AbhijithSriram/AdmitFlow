"""Payment, dashboard and receipt routes (SRD FR-5, FR-6.9, FR-8, FR-9) against real PostgreSQL."""
import hashlib
import hmac

import pytest

from app.extensions import db
from app.models import Application, Payment, Student

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
    assert resp.get_json()["data"] == {"id": "order_1", "amount": 100000, "currency": "INR"}
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
