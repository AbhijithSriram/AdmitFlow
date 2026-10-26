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


def test_the_application_pdf_link_redirects_its_owner_to_a_presigned_url(client, make_student, fake_minio):
    owner = make_student(status="PAID", files=True)
    application = _application_of(owner)
    _login_as(client, owner)
    resp = client.get(f"/api/app/application-pdf/{application.id}")
    assert resp.status_code == 302 and resp.headers["Location"].startswith("http://minio.test/")

    _login_as(client, make_student(status="PAID", files=True))
    assert client.get(f"/api/app/application-pdf/{application.id}").status_code == 404


@pytest.mark.parametrize("bad_id", ["not-a-uuid", "x'or'1'='1"])
def test_the_application_pdf_link_is_a_json_404_without_a_pdf_or_with_a_bad_id(client, make_student, bad_id):
    student = make_student(status="IN_PROGRESS", files=False)
    _login_as(client, student)
    for app_id in (_application_of(student).id, bad_id):
        resp = client.get(f"/api/app/application-pdf/{app_id}")
        assert resp.status_code == 404 and resp.get_json()["success"] is False


def test_the_application_pdf_link_needs_a_login(client, make_student):
    student = make_student(status="PAID", files=True)
    assert client.get(f"/api/app/application-pdf/{_application_of(student).id}").status_code == 401


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

    assert grouped == {"Academic Details": [("UG score", "8.7")], "Entrance / Test Details": [("Score", "88")]}
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

    assert _collect_form_data(application.id) == {"Documents": [("ID proof type", "Aadhaar")]}


def test_pdf_labels_expand_abbreviations():
    from app.services import pdf_service

    html = pdf_service._rows_html({"Address Details": {"comm_line1": "x", "perm_pincode": "600001"},
                                   "Personal Details": {"ews": "No"},
                                   "Academic Details": {"ug_degree": "B.E."},
                                   "Documents": {"id_proof_type": "Aadhaar"}})

    for label in ("Communication line 1", "Permanent pincode", "EWS", "UG degree", "ID proof type"):
        assert f"<td class='label'>{label}</td>" in html

# ------------------------------------------- a success is never undone, a retry works, events are logged
def _confirm(client, order_id="order_1", payment_id="pay_1", signature=None):
    return client.post("/api/app/payment/confirm", json={
        "razorpay_order_id": order_id, "razorpay_payment_id": payment_id,
        "razorpay_signature": signature if signature is not None else _sign(order_id, payment_id)})


def _paid_student(make_student):
    """A student whose application is PAID through order_1."""
    student = make_student(status="IN_PROGRESS", files=False)
    application = _add_created_payment(student)
    application.status = "PAID"
    payment = Payment.query.filter_by(razorpay_order_id="order_1").one()
    payment.status, payment.razorpay_payment_id = "SUCCESS", "pay_1"
    db.session.commit()
    return student


def test_a_late_failed_report_cannot_unpay_a_paid_application(client, make_student):
    student = _paid_student(make_student)
    _login_as(client, student)

    resp = client.post("/api/app/payment/failed", json={"order_id": "order_1", "dismissed": True})

    assert resp.status_code == 200 and resp.json["data"]["status"] == "PAID"
    assert _application_of(student).status == "PAID"
    assert Payment.query.filter_by(razorpay_order_id="order_1").one().status == "SUCCESS"


def test_a_bad_signature_sent_after_success_changes_nothing(client, make_student, no_delivery):
    student = _paid_student(make_student)
    _login_as(client, student)

    # order_1 is already SUCCESS, so this is treated as a repeat and acknowledged without being re-judged
    assert _confirm(client, signature="deadbeef").status_code == 200
    assert _application_of(student).status == "PAID"
    assert Payment.query.filter_by(razorpay_order_id="order_1").one().status == "SUCCESS"

    # and a bad signature on a different, unpaid order cannot downgrade the paid application either
    db.session.add(Payment(application_id=_application_of(student).id, razorpay_order_id="order_2",
                           amount=1000, status="CREATED"))
    db.session.commit()
    assert _confirm(client, order_id="order_2", payment_id="pay_2", signature="deadbeef").status_code == 400
    assert _application_of(student).status == "PAID"


def test_repeating_a_confirmation_delivers_only_once(client, make_student, monkeypatch):
    from app.blueprints import payment

    calls = []
    monkeypatch.setattr(payment, "_generate_and_deliver_confirmation", lambda *a, **k: calls.append(1))
    student = make_student(status="IN_PROGRESS", files=False)
    _add_created_payment(student)
    _login_as(client, student)

    assert _confirm(client).status_code == 200
    assert _confirm(client).status_code == 200   # double click / retried request

    assert len(calls) == 1
    assert _application_of(student).status == "PAID"


def test_a_second_payment_for_a_paid_application_is_recorded_not_delivered_again(client, make_student, monkeypatch):
    from app.blueprints import payment

    calls = []
    monkeypatch.setattr(payment, "_generate_and_deliver_confirmation", lambda *a, **k: calls.append(1))
    student = _paid_student(make_student)
    db.session.add(Payment(application_id=_application_of(student).id, razorpay_order_id="order_2",
                           amount=1000, status="CREATED"))
    db.session.commit()
    _login_as(client, student)

    resp = _confirm(client, order_id="order_2", payment_id="pay_2")

    assert resp.status_code == 200
    assert Payment.query.filter_by(razorpay_order_id="order_2").one().status == "SUCCESS"   # kept, so it can be refunded
    assert _application_of(student).status == "PAID"
    assert calls == []


def test_a_failed_payment_can_be_retried_and_then_succeeds(client, make_student, no_delivery, monkeypatch):
    from app.services import payment_service

    orders = iter(["order_1", "order_2"])
    monkeypatch.setattr(payment_service, "create_order",
                        lambda amount_paise, receipt: {"id": next(orders), "amount": amount_paise, "currency": "INR"})
    student = make_student(status="IN_PROGRESS", files=False)
    _login_as(client, student)

    assert client.post("/api/app/payment/create-order").status_code == 201
    client.post("/api/app/payment/failed", json={"order_id": "order_1", "dismissed": True})
    assert _application_of(student).status == "PAYMENT_PENDING"

    assert client.post("/api/app/payment/create-order").status_code == 201   # allowed again while PAYMENT_PENDING
    assert _confirm(client, order_id="order_2", payment_id="pay_2").status_code == 200

    assert _application_of(student).status == "PAID"
    assert [p.status for p in Payment.query.order_by(Payment.razorpay_order_id).all()] == ["FAILED", "SUCCESS"]


def test_payment_events_are_logged_without_secrets(client, make_student, no_delivery, monkeypatch, caplog):
    import logging

    from app.services import payment_service

    monkeypatch.setattr(payment_service, "create_order",
                        lambda amount_paise, receipt: {"id": "order_1", "amount": amount_paise, "currency": "INR"})
    student = make_student(status="IN_PROGRESS", files=False)
    _login_as(client, student)
    signature = _sign("order_1", "pay_1")

    with caplog.at_level(logging.INFO, logger="app.blueprints.payment"):
        client.post("/api/app/payment/create-order")
        _confirm(client, signature="deadbeef")                      # a forged one first
        db.session.add(Payment(application_id=_application_of(student).id, razorpay_order_id="order_2",
                               amount=1000, status="CREATED"))
        db.session.commit()
        _confirm(client, order_id="order_2", payment_id="pay_2", signature=_sign("order_2", "pay_2"))

    text = caplog.text
    assert "payment order created order=order_1" in text
    assert "payment signature verification failed order=order_1" in text
    assert "payment confirmed order=order_2 payment=pay_2" in text
    for secret in (signature, _sign("order_2", "pay_2"), "deadbeef", SECRET):
        assert secret not in text


# ------------------------------------------------- malformed ids and the fee receipt
@pytest.mark.parametrize("bad_id", ["not-a-uuid", "123", "x'or'1'='1"])
def test_a_malformed_application_id_is_a_json_404_not_a_500(client, make_student, bad_id):
    _login_as(client, make_student(status="PAID", payment="SUCCESS"))
    for method, path in (("get", f"/api/app/draft/{bad_id}"),
                         ("patch", f"/api/app/draft/{bad_id}/step/1"),
                         ("post", f"/api/app/upload/{bad_id}/photo"),
                         ("get", f"/api/app/receipt/{bad_id}"),
                         ("get", f"/api/app/receipt/{bad_id}/pdf")):
        resp = getattr(client, method)(path, json={}) if method == "patch" else getattr(client, method)(path)
        assert resp.status_code == 404, (method, path, resp.status_code)
        assert resp.is_json and resp.get_json()["success"] is False, (method, path)


@pytest.fixture
def receipts(monkeypatch):
    """Record what the fee receipt is rendered with, without running WeasyPrint."""
    from app.services import pdf_service

    rendered = []
    monkeypatch.setattr(pdf_service, "render_receipt_pdf", lambda ctx: rendered.append(ctx) or b"%PDF-receipt")
    return rendered


def test_the_fee_receipt_is_a_pdf_with_the_amount_paid(client, make_student, receipts):
    student = make_student(status="PAID", payment="SUCCESS")
    _login_as(client, student)

    resp = client.get(f"/api/app/receipt/{_application_of(student).id}/pdf")

    assert resp.status_code == 200 and resp.mimetype == "application/pdf"
    assert resp.data == b"%PDF-receipt"
    assert "inline" in resp.headers["Content-Disposition"] and "receipt" in resp.headers["Content-Disposition"]
    ctx = receipts[0]
    assert (ctx["full_name"], ctx["programme"], ctx["payment_id"], ctx["order_id"]) == (
        "Test Student", "B.Tech", "p2", "o2")
    assert str(ctx["amount"]) == "500.00"           # the successful payment, not the failed attempt before it


def test_the_fee_receipt_belongs_to_its_owner_only(client, make_student, receipts):
    owner = make_student(status="PAID", payment="SUCCESS")
    _login_as(client, make_student(status="PAID", payment="SUCCESS"))
    assert client.get(f"/api/app/receipt/{_application_of(owner).id}/pdf").status_code == 404
    assert receipts == []


def test_no_fee_receipt_before_a_successful_payment(client, make_student, receipts):
    student = make_student(status="PAYMENT_PENDING", payment="FAILED")
    _login_as(client, student)
    resp = client.get(f"/api/app/receipt/{_application_of(student).id}/pdf")
    assert resp.status_code == 404 and resp.get_json()["success"] is False
    assert receipts == []


def test_the_fee_receipt_needs_a_login(client, make_student):
    student = make_student(status="PAID", payment="SUCCESS")
    assert client.get(f"/api/app/receipt/{_application_of(student).id}/pdf").status_code == 401


def test_the_fee_receipt_really_renders(client, make_student):
    student = make_student(status="PAID", payment="SUCCESS")
    _login_as(client, student)
    resp = client.get(f"/api/app/receipt/{_application_of(student).id}/pdf")
    assert resp.status_code == 200 and resp.data.startswith(b"%PDF")
