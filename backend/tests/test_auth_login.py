from datetime import datetime, timedelta

import pytest

PASSWORD = "sunrise-42!"
EMAIL = "login@example.com"


@pytest.fixture
def student(app):
    from datetime import date

    from app.extensions import bcrypt, db
    from app.models import Student

    s = Student(
        full_name="Login Test", date_of_birth=date(2005, 1, 1), gender="Male", email=EMAIL,
        phone="9000000001", email_verified=True,
        password_hash=bcrypt.generate_password_hash(PASSWORD).decode(),
    )
    db.session.add(s)
    db.session.commit()
    return s


def _login(client, password=PASSWORD, email=EMAIL):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_creates_session_and_me_restores_it(client, student):
    r = _login(client)
    assert r.status_code == 200 and r.json["data"]["student"]["email"] == EMAIL
    assert "password" not in str(r.json)
    cookie = r.headers["Set-Cookie"]
    assert "admitflow_student_session=" in cookie and "HttpOnly" in cookie
    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json["data"]["student"]["id"] == str(student.id)


def test_email_is_case_insensitive(client, student):
    assert _login(client, email=EMAIL.upper()).status_code == 200


def test_wrong_password_and_unknown_email_look_identical(client, student):
    a, b = _login(client, "nope"), _login(client, email="ghost@example.com")
    assert a.status_code == b.status_code == 401
    assert a.json == b.json


def test_missing_fields_400(client, student):
    assert client.post("/api/auth/login", json={"email": EMAIL}).status_code == 400


def test_unverified_or_passwordless_account_cannot_log_in(client, student):
    from app.extensions import db

    student.email_verified = False
    db.session.commit()
    assert _login(client).status_code == 401


def test_five_failures_lock_the_account_even_for_correct_password(client, student):
    from app.models import Student

    for _ in range(4):
        assert _login(client, "wrong").status_code == 401
    assert _login(client, "wrong").status_code == 401  # 5th failure triggers the lock
    assert Student.query.one().locked_until is not None
    r = _login(client)  # correct password, still locked
    assert r.status_code == 423 and "minute" in r.json["error"]
    assert client.get("/api/auth/me").status_code == 401


def test_lock_expires_after_fifteen_minutes(client, student):
    from app.extensions import db

    for _ in range(5):
        _login(client, "wrong")
    student.locked_until = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    assert _login(client).status_code == 200


def test_expired_lock_restarts_the_failure_count(client, student):
    from app.extensions import db
    from app.models import Student

    for _ in range(5):
        _login(client, "wrong")
    student.locked_until = datetime.utcnow() - timedelta(seconds=1)
    db.session.commit()
    assert _login(client, "wrong").status_code == 401
    assert Student.query.one().failed_login_attempts == 1


def test_success_resets_failure_counter(client, student):
    from app.models import Student

    _login(client, "wrong")
    _login(client, "wrong")
    assert _login(client).status_code == 200
    assert Student.query.one().failed_login_attempts == 0


def test_logout_invalidates_session(client, student):
    _login(client)
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_logout_requires_login(client):
    assert client.post("/api/auth/logout").status_code == 401


def test_me_requires_login(client):
    assert client.get("/api/auth/me").status_code == 401


def test_login_discards_pre_login_otp_proof(client, student):
    with client.session_transaction() as sess:
        sess["otp_verified"] = {"student_id": "x", "purpose": "password_reset", "expires": "2999-01-01T00:00:00"}
    _login(client)
    with client.session_transaction() as sess:
        assert "otp_verified" not in sess and sess["student_id"] == str(student.id)


def test_forgot_password_flow_changes_password_and_clears_lockout(client, student, monkeypatch):
    from app.extensions import db
    from app.services import email_service

    sent = []
    monkeypatch.setattr(email_service, "send_password_reset_email", lambda to, otp: sent.append(otp))
    for _ in range(5):
        _login(client, "wrong")  # lock the account first

    assert client.post("/api/auth/send-otp", json={"email": EMAIL, "purpose": "password_reset"}).status_code == 200
    r = client.post("/api/auth/verify-otp", json={"email": EMAIL, "otp": sent[0], "purpose": "password_reset"})
    assert r.status_code == 200
    new_password = "brand-new-77#"
    r = client.post("/api/auth/set-password", json={"password": new_password, "confirm_password": new_password})
    assert r.status_code == 200

    assert _login(client, PASSWORD).status_code == 401  # old password no longer works
    assert _login(client, new_password).status_code == 200  # and the lock is gone
