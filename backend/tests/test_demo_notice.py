"""AdmitFlow runs publicly as an academic project, so everything that leaves the site (emails and PDFs)
must say so, and a test-mode receipt must say no real money was charged."""
import pytest

from app.services import email_service, pdf_service


class _FakeSMTP:
    sent = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        pass

    def login(self, *args):
        pass

    def send_message(self, message):
        _FakeSMTP.sent.append(message)


@pytest.fixture
def smtp(app, monkeypatch):
    _FakeSMTP.sent = []
    monkeypatch.setattr(email_service.smtplib, "SMTP", _FakeSMTP)
    for key, value in {"SMTP_HOST": "smtp.test", "SMTP_PORT": 587, "SMTP_USERNAME": "noreply@test",
                       "SMTP_PASSWORD": "x"}.items():
        monkeypatch.setitem(app.config, key, value)
    return _FakeSMTP


def _html(message):
    return message.get_body(preferencelist=("html",)).get_content()


@pytest.mark.parametrize("send", [
    lambda: email_service.send_otp_email("a@example.com", "123456"),
    lambda: email_service.send_password_reset_email("a@example.com", "123456"),
    lambda: email_service.send_payment_confirmation_email("a@example.com", b"%PDF-1", b"%PDF-1", {"full_name": "A"}),
])
def test_every_email_says_it_is_an_academic_project(app, smtp, send):
    with app.app_context():
        send()
    body = _html(smtp.sent[0])
    assert "academic project" in body
    assert "no admission is offered" in body


@pytest.mark.parametrize("template, context", [
    (pdf_service._application_template, {"full_name": "A", "form_data": {}}),
    (pdf_service._receipt_template, {"full_name": "A"}),
    (pdf_service._applicants_template, {"headers": ["Name"], "rows": [], "filters": "all", "generated_at": "now"}),
])
def test_every_pdf_carries_the_disclaimer_footer(template, context):
    assert pdf_service.DEMO_FOOTER in template(context)


def test_a_test_mode_receipt_says_no_real_money_was_charged():
    assert "No real money was charged" in pdf_service._receipt_template({"test_mode": True})
    assert "No real money was charged" not in pdf_service._receipt_template({"test_mode": False})


def test_the_receipt_pdf_still_renders_with_the_footer():
    assert pdf_service.render_receipt_pdf({"full_name": "A", "test_mode": True}).startswith(b"%PDF")
