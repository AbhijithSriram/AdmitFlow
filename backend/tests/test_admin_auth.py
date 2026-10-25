import pytest


def test_login_sets_separate_httponly_cookie(client, admin, login):
    r = login()
    assert r.status_code == 200 and r.json["success"] is True
    cookie = r.headers["Set-Cookie"]
    assert "admitflow_admin_session=" in cookie and "HttpOnly" in cookie and "SameSite=Strict" in cookie
    assert "admitflow_student_session" not in cookie  # not the student cookie


def test_me_restores_session(logged_in):
    assert logged_in.get("/api/admin/me").json["data"]["admin"]["email"] == "asha@college.edu"


def test_wrong_password_and_unknown_email_look_identical(client, admin, login):
    a, b = login(password="nope"), login(email="ghost@x.com")
    assert a.status_code == b.status_code == 401
    assert a.json["error"] == b.json["error"] == "Incorrect email or password."


def test_missing_fields_400(client, admin):
    assert client.post("/api/admin/login", json={"email": "a@b.c"}).status_code == 400


def test_no_session_401_on_every_admin_route(client):
    for method, url in [("get", "/api/admin/me"), ("get", "/api/admin/students"),
                        ("get", "/api/admin/students/00000000-0000-4000-8000-000000000000"),
                        ("delete", "/api/admin/students/00000000-0000-4000-8000-000000000000"),
                        ("post", "/api/admin/logout")]:
        assert getattr(client, method)(url).status_code == 401, url


def test_student_cookie_alone_is_403(client, admin):
    client.set_cookie("admitflow_student_session", "some-student-session")
    assert client.get("/api/admin/students").status_code == 403


def test_student_cookie_does_not_grant_admin_access(logged_in):
    # an admin session AND a student cookie: admin cookie still wins, student cookie is irrelevant
    logged_in.set_cookie("admitflow_student_session", "x")
    assert logged_in.get("/api/admin/me").status_code == 200


def test_logout_invalidates_session_on_the_server(client, admin, login):
    login()
    token = client.get_cookie("admitflow_admin_session", path="/api/admin").value
    assert client.post("/api/admin/logout").status_code == 200
    client.set_cookie("admitflow_admin_session", token, path="/api/admin")  # replay old cookie
    assert client.get("/api/admin/me").status_code == 401


def test_idle_timeout(app, logged_in):
    from datetime import timedelta
    from app.extensions import db
    from app.models import AdminSession

    sess = AdminSession.query.one()
    sess.last_seen_at = sess.last_seen_at - timedelta(seconds=app.config["PERMANENT_SESSION_LIFETIME"] + 5)
    db.session.commit()
    assert logged_in.get("/api/admin/me").status_code == 401


def test_session_is_stored_hashed(logged_in):
    from app.models import AdminSession
    token = logged_in.get_cookie("admitflow_admin_session", path="/api/admin").value
    assert AdminSession.query.one().token_hash != token


def test_security_headers_on_responses(client):
    h = client.get("/api/admin/me").headers
    for k in ("Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options", "Strict-Transport-Security"):
        assert k in h


def test_login_is_rate_limited_with_json_429(app, client, admin):
    from app.extensions import limiter
    limiter.enabled = True
    try:
        codes = [client.post("/api/admin/login", json={"email": "a@b.c", "password": "x"}).status_code
                 for _ in range(12)]
        assert codes[:10] == [401] * 10 and codes[10:] == [429, 429]
        r = client.post("/api/admin/login", json={"email": "a@b.c", "password": "x"})
        assert r.json == {"success": False, "error": "Too many requests. Please wait a minute and try again."}
    finally:
        limiter.enabled = False
        limiter.reset()


def test_log_redaction():
    import logging
    from app.logging_config import RedactFilter
    r = logging.LogRecord("x", 30, "", 0, "login password=hunter2 otp: 123456 token=abc", (), None)
    RedactFilter().filter(r)
    assert not any(s in r.msg for s in ("hunter2", "123456", "abc"))


def test_log_redaction_catches_passwords_and_otps_in_json_and_prefixed_keys():
    import logging
    from app.logging_config import RedactFilter
    line = 'body={"password": "hunter2", "otp": "654321"} new_password=s3cret-pw raw_otp=111222'
    r = logging.LogRecord("x", 20, "", 0, "request %s", (line,), None)
    RedactFilter().filter(r)
    assert not any(s in r.msg for s in ("hunter2", "654321", "s3cret-pw", "111222"))
    assert r.msg.count("[REDACTED]") == 4
