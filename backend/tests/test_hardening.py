"""Regression tests for fixes found while reviewing and browser-testing the slices together."""
import datetime
import io

from PIL import Image

from app.extensions import db
from app.models import Application, FormDraft, OtpToken, Student
from app.services import otp_service


def _login_as(client, student):
    with client.session_transaction() as sess:
        sess["student_id"] = student.id


def _application_of(student):
    return Application.query.filter_by(student_id=student.id).first()


def _png(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (20, 90, 160)).save(buf, "PNG")
    return buf.getvalue()


# ----------------------------------------------------- one-time-code brute force
def test_a_code_is_burned_after_five_wrong_guesses(app, make_student):
    student = make_student()
    code = otp_service.create_otp_token(str(student.id), "email_verification")
    wrong = "000000" if code != "000000" else "111111"

    for _ in range(otp_service.MAX_OTP_ATTEMPTS):
        assert otp_service.verify_otp(str(student.id), "email_verification", wrong) is False

    # even the correct code no longer works: the attacker cannot keep guessing one code
    assert otp_service.verify_otp(str(student.id), "email_verification", code) is False
    newest = OtpToken.query.filter_by(student_id=student.id).order_by(OtpToken.created_at.desc()).first()
    assert newest.failed_attempts == otp_service.MAX_OTP_ATTEMPTS
    assert newest.consumed_at is not None


def test_fewer_than_five_wrong_guesses_do_not_lock_the_real_code(app, make_student):
    student = make_student()
    code = otp_service.create_otp_token(str(student.id), "email_verification")
    wrong = "000000" if code != "000000" else "111111"

    for _ in range(otp_service.MAX_OTP_ATTEMPTS - 1):
        assert otp_service.verify_otp(str(student.id), "email_verification", wrong) is False

    assert otp_service.verify_otp(str(student.id), "email_verification", code) is True


def test_requesting_a_new_code_retires_the_old_one(app, make_student):
    student = make_student()
    old = otp_service.create_otp_token(str(student.id), "email_verification")
    new = otp_service.create_otp_token(str(student.id), "email_verification")

    # only the newest code counts, so an attacker can't fall back to an older live code
    if old != new:
        assert otp_service.verify_otp(str(student.id), "email_verification", old) is False
    assert otp_service.verify_otp(str(student.id), "email_verification", new) is True


def test_failed_guesses_are_counted_per_code_not_per_student(app, make_student):
    student = make_student()
    first = otp_service.create_otp_token(str(student.id), "email_verification")
    wrong = "000000" if first != "000000" else "111111"
    for _ in range(otp_service.MAX_OTP_ATTEMPTS):
        otp_service.verify_otp(str(student.id), "email_verification", wrong)

    fresh = otp_service.create_otp_token(str(student.id), "email_verification")

    assert otp_service.verify_otp(str(student.id), "email_verification", fresh) is True


# ------------------------------------------------------------ phone squatting
def _signup(client, **overrides):
    body = {"full_name": "Real Owner", "date_of_birth": "2004-03-09", "gender": "Female",
            "email": "real.owner@example.com", "phone": "9000000099", "recaptcha_token": "x"}
    body.update(overrides)
    return client.post("/api/auth/signup", json=body)


def test_an_unverified_signup_cannot_hold_someone_elses_phone_number(client):
    squatter = Student(full_name="Squatter", date_of_birth=datetime.date(2000, 1, 1), gender="Male",
                       email="throwaway@example.com", phone="9000000099", email_verified=False)
    db.session.add(squatter)
    db.session.commit()

    resp = _signup(client)  # the real owner registers with their own email and number

    assert resp.status_code == 201
    owner = Student.query.filter_by(phone="9000000099").one()
    assert owner.email == "real.owner@example.com"
    assert Student.query.filter_by(email="throwaway@example.com").count() == 0


def test_a_verified_account_still_keeps_its_phone_number(client, make_student):
    taken = make_student()
    resp = _signup(client, phone=taken.phone)
    assert resp.status_code == 409 and resp.json["field"] == "phone"
    assert Student.query.filter_by(email=taken.email).count() == 1


# ------------------------------------------- application routes: size and errors
def test_an_oversized_step_is_refused_and_nothing_is_saved(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.patch(f"/api/app/draft/{application.id}/step/3", json={"junk": "x" * 30_000})

    assert resp.status_code == 413
    saved = FormDraft.query.filter_by(application_id=application.id, step_number=3).first()
    assert saved is None or "junk" not in (saved.data or {})


def test_programme_must_be_text(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.patch(f"/api/app/draft/{application.id}/step/4", json={"programme": {"nested": 1}})

    assert resp.status_code == 400
    assert db.session.get(Application, application.id).programme != {"nested": 1}


def test_a_save_failure_does_not_leak_internals(client, make_student, monkeypatch):
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    def boom(*args, **kwargs):
        raise RuntimeError("psycopg2 password=hunter2 host=10.0.0.5")

    monkeypatch.setattr("app.blueprints.application.insert", boom)

    resp = client.patch(f"/api/app/draft/{application.id}/step/1", json={"father_name": "R"})

    assert resp.status_code == 500
    assert "hunter2" not in resp.get_data(as_text=True)
    assert "10.0.0.5" not in resp.get_data(as_text=True)


def test_a_storage_failure_does_not_leak_internals(client, make_student, monkeypatch):
    from app.services import minio_service

    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    def boom(*args, **kwargs):
        raise RuntimeError("could not connect to 10.0.0.5:9000 with key AKIA-SECRET")

    monkeypatch.setattr(minio_service, "upload_object", boom)

    resp = client.post(
        f"/api/app/upload/{application.id}/photo",
        data={"file": (io.BytesIO(_png(300, 400)), "photo.png")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 502
    assert "AKIA-SECRET" not in resp.get_data(as_text=True)
    assert "10.0.0.5" not in resp.get_data(as_text=True)
