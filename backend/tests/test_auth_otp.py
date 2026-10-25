from datetime import datetime, timedelta

import pytest

EMAIL = "priya@example.com"


@pytest.fixture
def outbox(monkeypatch):
    """Capture OTP emails instead of talking to SMTP."""
    from app.services import email_service

    sent = []
    monkeypatch.setattr(email_service, "send_otp_email", lambda to, otp: sent.append(("verify", to, otp)))
    monkeypatch.setattr(email_service, "send_password_reset_email", lambda to, otp: sent.append(("reset", to, otp)))
    return sent


@pytest.fixture
def pending(app):
    """An unverified, password-less student (what signup leaves behind)."""
    from datetime import date

    from app.extensions import db
    from app.models import Student

    s = Student(full_name="Priya", date_of_birth=date(2005, 4, 12), gender="Female", email=EMAIL, phone="9876543210")
    db.session.add(s)
    db.session.commit()
    return s


def _send(client, **body):
    return client.post("/api/auth/send-otp", json={"email": EMAIL, **body})


def _verify(client, otp, **body):
    return client.post("/api/auth/verify-otp", json={"email": EMAIL, "otp": otp, **body})


def test_send_otp_emails_a_six_digit_code_and_stores_only_its_hash(client, pending, outbox):
    from app.models import OtpToken

    assert _send(client).status_code == 200
    kind, to, otp = outbox[0]
    assert kind == "verify" and to == EMAIL and len(otp) == 6 and otp.isdigit()
    token = OtpToken.query.one()
    assert token.otp_hash != otp and token.purpose == "email_verification"
    assert token.expires_at > datetime.utcnow()


def test_unknown_email_gets_same_response_and_no_email(client, outbox):
    r = client.post("/api/auth/send-otp", json={"email": "ghost@example.com"})
    assert r.status_code == 200 and outbox == []


def test_resend_within_cooldown_is_429(client, pending, outbox):
    assert _send(client).status_code == 200
    assert _send(client).status_code == 429
    assert len(outbox) == 1


def test_resend_after_cooldown_works(client, pending, outbox):
    from app.extensions import db
    from app.models import OtpToken

    _send(client)
    token = OtpToken.query.one()
    token.created_at = datetime.utcnow() - timedelta(seconds=120)
    db.session.commit()
    assert _send(client).status_code == 200 and len(outbox) == 2


def test_smtp_failure_is_503_not_500(client, pending, monkeypatch):
    from app.services import email_service

    def boom(*a):
        raise OSError("smtp down")

    monkeypatch.setattr(email_service, "send_otp_email", boom)
    assert _send(client).status_code == 503


def test_invalid_purpose_is_400(client, pending, outbox):
    assert _send(client, purpose="admin_takeover").status_code == 400


def test_password_reset_otp_not_sent_to_account_without_password(client, pending, outbox):
    assert _send(client, purpose="password_reset").status_code == 200
    assert outbox == []


def test_verify_marks_email_verified_and_is_single_use(client, pending, outbox):
    from app.models import Student

    _send(client)
    otp = outbox[0][2]
    r = _verify(client, otp)
    assert r.status_code == 200 and r.json["data"]["verified"] is True
    assert Student.query.one().email_verified is True
    # replaying the same code, now that the email is verified, must fail
    assert _verify(client, otp).status_code == 400


def test_wrong_code_is_400_and_does_not_verify(client, pending, outbox):
    from app.models import Student

    _send(client)
    wrong = "000000" if outbox[0][2] != "000000" else "111111"
    r = _verify(client, wrong)
    assert r.status_code == 400 and r.json["field"] == "otp"
    assert Student.query.one().email_verified is False


def test_expired_code_is_rejected(client, pending, outbox):
    from app.extensions import db
    from app.models import OtpToken

    _send(client)
    token = OtpToken.query.one()
    token.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    assert _verify(client, outbox[0][2]).status_code == 400


@pytest.mark.parametrize("otp", ["", "12345", "1234567", "abcdef", None, 123456])
def test_malformed_code_is_400(client, pending, outbox, otp):
    _send(client)
    assert _verify(client, otp).status_code == 400


def test_verify_stores_server_side_proof_in_session(client, pending, outbox):
    _send(client)
    _verify(client, outbox[0][2])
    with client.session_transaction() as sess:
        assert sess["otp_verified"]["student_id"] == str(pending.id)
        assert sess["otp_verified"]["purpose"] == "email_verification"


def test_otp_dispatch_is_logged_without_the_code_or_email(client, pending, outbox, caplog):
    caplog.set_level("INFO")
    assert _send(client).status_code == 200
    otp = outbox[0][2]
    text = "\n".join(r.getMessage() for r in caplog.records if r.name == "app.blueprints.auth")
    assert f"otp sent student_id={pending.id} purpose=email_verification" in text
    assert otp not in text and EMAIL not in text
