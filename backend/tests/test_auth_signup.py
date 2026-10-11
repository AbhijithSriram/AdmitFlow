import pytest

VALID = {
    "full_name": "Priya Raman",
    "date_of_birth": "2005-04-12",
    "gender": "Female",
    "email": "Priya@Example.com",
    "phone": "9876543210",
}


def _signup(client, **overrides):
    return client.post("/api/auth/signup", json={**VALID, **overrides})


def test_signup_creates_unverified_student_without_password(client):
    from app.models import Student

    r = _signup(client)
    assert r.status_code == 201 and r.json["success"] is True
    student = Student.query.one()
    assert r.json["data"]["student_id"] == str(student.id)
    assert student.email == "priya@example.com"  # normalised
    assert student.email_verified is False and student.password_hash is None


@pytest.mark.parametrize(
    "overrides, field",
    [
        ({"full_name": "  "}, "full_name"),
        ({"date_of_birth": "not-a-date"}, "date_of_birth"),
        ({"date_of_birth": "2999-01-01"}, "date_of_birth"),
        ({"gender": "Robot"}, "gender"),
        ({"email": "nope"}, "email"),
        ({"phone": "12345"}, "phone"),
        ({"phone": "98765abcde"}, "phone"),
    ],
)
def test_invalid_fields_are_rejected_with_field_name(client, overrides, field):
    from app.models import Student

    r = _signup(client, **overrides)
    assert r.status_code == 400 and r.json["field"] == field
    assert Student.query.count() == 0


def test_non_json_body_is_400(client):
    assert client.post("/api/auth/signup", data="x").status_code == 400


def test_duplicate_verified_email_is_409(client, make_student):
    make_student()  # s1@example.com, email_verified=True
    r = _signup(client, email="s1@example.com")
    assert r.status_code == 409 and r.json["field"] == "email"


def test_duplicate_phone_is_409(client, make_student):
    other = make_student()
    r = _signup(client, phone=other.phone)
    assert r.status_code == 409 and r.json["field"] == "phone"


def test_unverified_email_can_re_register_with_corrected_details(client):
    from app.models import Student

    first = _signup(client)
    second = _signup(client, full_name="Priya R", phone="9123456780")
    assert second.status_code == 201
    assert second.json["data"]["student_id"] == first.json["data"]["student_id"]
    student = Student.query.one()
    assert student.full_name == "Priya R" and student.phone == "9123456780"


def test_recaptcha_failure_blocks_signup(app, client, monkeypatch):
    from app.models import Student
    from app.services import recaptcha_service

    monkeypatch.setattr(recaptcha_service, "verify_token", lambda token, ip=None: False)
    r = _signup(client, recaptcha_token="bad")
    assert r.status_code == 400 and r.json["field"] == "recaptcha"
    assert Student.query.count() == 0


def test_recaptcha_token_is_forwarded_to_verifier(app, client, monkeypatch):
    from app.services import recaptcha_service

    seen = []
    monkeypatch.setattr(recaptcha_service, "verify_token", lambda token, ip=None: seen.append(token) or True)
    assert _signup(client, recaptcha_token="tok-123").status_code == 201
    assert seen == ["tok-123"]


def test_verifier_fails_closed_when_secret_set_but_token_missing(app, monkeypatch):
    from app.services import recaptcha_service

    monkeypatch.setitem(app.config, "RECAPTCHA_SECRET_KEY", "secret")
    assert recaptcha_service.verify_token(None) is False
    assert recaptcha_service.verify_token("") is False


def test_verifier_fails_closed_on_network_error(app, monkeypatch):
    from app.services import recaptcha_service

    def boom(*args, **kwargs):
        raise OSError("network down")

    monkeypatch.setitem(app.config, "RECAPTCHA_SECRET_KEY", "secret")
    monkeypatch.setattr(recaptcha_service.urllib.request, "urlopen", boom)
    assert recaptcha_service.verify_token("tok") is False


def test_verifier_fails_closed_in_production_without_secret(app, monkeypatch):
    from app.services import recaptcha_service

    monkeypatch.setitem(app.config, "RECAPTCHA_SECRET_KEY", None)
    monkeypatch.setitem(app.config, "TESTING", False)
    monkeypatch.setitem(app.config, "DEBUG", False)
    assert recaptcha_service.verify_token("tok") is False
