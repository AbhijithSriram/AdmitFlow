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
