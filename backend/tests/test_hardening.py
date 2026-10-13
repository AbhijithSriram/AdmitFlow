"""Regression tests for fixes found while reviewing and browser-testing the slices together."""
import datetime
import io

import pytest
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

    resp = client.patch(f"/api/app/draft/{application.id}/step/3", json={"programme": {"nested": 1}})

    assert resp.status_code == 400
    assert db.session.get(Application, application.id).programme != {"nested": 1}


# ------------------------------------------- text-only fields refuse digits and symbols
@pytest.mark.parametrize("step, field, bad", [
    (1, "father_name", "Vijayakumar 2"),
    (1, "mother_name", "Krishna<script>"),
    (1, "religion", "Hindu1"),
    (1, "mother_tongue", "12345"),
    (1, "country", "Country 9"),
    (2, "perm_district", "Chennai 600"),
    (2, "comm_state", "TN-7"),
    (2, "perm_town", "123"),
    (4, "college", "98765"),
    (4, "ug_specialisation", "CSE 2"),
    (4, "xii_school", "12345"),
    (4, "x_school", "Chennai<b>"),
])
def test_text_fields_refuse_digits_and_symbols(client, make_student, step, field, bad):
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.patch(f"/api/app/draft/{application.id}/step/{step}", json={field: bad})

    assert resp.status_code == 400
    assert "can contain" in resp.json["error"]
    saved = FormDraft.query.filter_by(application_id=application.id, step_number=step).first()
    assert saved is None or (saved.data or {}).get(field) != bad


def test_real_names_and_places_are_accepted(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)
    url = f"/api/app/draft/{application.id}/step"

    assert client.patch(f"{url}/1", json={
        "father_name": "K. Vijaya-Kumar", "mother_name": "Krishnapriya", "guardian_name": "D'Souza",
        "religion": "Hindu", "mother_tongue": "தமிழ்", "country": "United States (USA)",
    }).status_code == 200
    assert client.patch(f"{url}/2", json={
        "perm_town": "Sector 5", "perm_district": "Dadra & Nagar Haveli", "perm_state": "Tamil Nadu",
        "perm_country": "India", "perm_line1": "12/3, 4th Cross Street",   # address lines may hold numbers
    }).status_code == 200
    assert client.patch(f"{url}/4", json={
        "college": "Anna University, Chennai - 25", "ug_specialisation": "Computer Science (AI)",
        "xii_school": "St. Joseph's Matriculation Hr. Sec. School", "x_school": "Government High School No. 2",
        "score": "8.5", "passing_year": "2024", "xii_percentage": "91.5",   # numeric fields are untouched
    }).status_code == 200


def test_the_programme_chosen_in_step_3_is_copied_onto_the_application(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.patch(f"/api/app/draft/{application.id}/step/3", json={"programme": "B.Tech", "specialisation": "CSE"})

    assert resp.status_code == 200
    saved = db.session.get(Application, application.id)
    assert (saved.programme, saved.specialisation) == ("B.Tech", "CSE")
    # Step 4 (academic details) must not touch it, whatever it carries.
    client.patch(f"/api/app/draft/{application.id}/step/4", json={"programme": "MCA"})
    db.session.expire_all()
    assert db.session.get(Application, application.id).programme == "B.Tech"


def test_empty_text_fields_are_still_saved(client, make_student):
    """Autosave sends half-filled steps; an empty box is not an invalid one."""
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.patch(f"/api/app/draft/{application.id}/step/1", json={"father_name": "", "guardian_name": ""})

    assert resp.status_code == 200


def test_signup_refuses_a_name_with_digits(client):
    resp = _signup(client, full_name="Real Owner 2")

    assert resp.status_code == 400 and resp.json["field"] == "full_name"
    assert Student.query.filter_by(email="real.owner@example.com").count() == 0


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


# ------------------------------------------------- photo and signature: any common image format
def _image(fmt, width=300, height=400, colour=(20, 90, 160)):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buf, fmt)
    return buf.getvalue()


@pytest.mark.parametrize("fmt, ext, content_type", [
    ("PNG", "png", "image/png"),
    ("JPEG", "jpg", "image/jpeg"),
    ("WEBP", "webp", "image/webp"),
    ("GIF", "gif", "image/gif"),
    ("BMP", "bmp", "image/bmp"),
])
@pytest.mark.parametrize("doc_type", ["photo", "signature"])
def test_photo_and_signature_accept_common_image_formats(client, make_student, monkeypatch, fmt, ext, content_type, doc_type):
    from app.services import minio_service

    size = (300, 400) if doc_type == "photo" else (200, 80)   # an uncompressed BMP signature must stay under 200 KB
    stored = {}
    monkeypatch.setattr(minio_service, "upload_object", lambda name, data, ctype: stored.update(name=name, ctype=ctype))
    monkeypatch.setattr(minio_service, "delete_object", lambda name: None)
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.post(
        f"/api/app/upload/{application.id}/{doc_type}",
        data={"file": (io.BytesIO(_image(fmt, *size)), "whatever.bin")},   # the filename is irrelevant: the contents decide
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200
    assert stored["name"] == f"applications/{application.id}/{doc_type}.{ext}"
    assert stored["ctype"] == content_type
    assert getattr(db.session.get(Application, application.id), f"{doc_type}_url") == stored["name"]


@pytest.mark.parametrize("fmt", ["TIFF", "ICO"])
def test_unsupported_image_formats_are_still_refused(client, make_student, monkeypatch, fmt):
    from app.services import minio_service

    monkeypatch.setattr(minio_service, "upload_object", lambda *a, **k: pytest.fail("must not be stored"))
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.post(
        f"/api/app/upload/{application.id}/photo",
        data={"file": (io.BytesIO(_image(fmt, 256, 256)), "photo.jpg")},   # a TIFF named .jpg is still a TIFF
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400 and "JPEG, PNG, WebP, GIF or BMP" in resp.json["error"]


def test_a_non_image_named_jpg_is_refused(client, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    application = _application_of(student)
    _login_as(client, student)

    resp = client.post(
        f"/api/app/upload/{application.id}/photo",
        data={"file": (io.BytesIO(b"<html><script>alert(1)</script></html>"), "photo.jpg")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400


@pytest.mark.parametrize("fmt, mime", [
    ("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp"), ("GIF", "image/gif"), ("BMP", "image/bmp"),
])
def test_the_application_pdf_embeds_every_accepted_format(fmt, mime):
    import base64

    from app.services import pdf_service

    # Two different pictures: WeasyPrint stores identical ones once.
    photo = f"data:{mime};base64," + base64.b64encode(_image(fmt)).decode()
    signature = f"data:{mime};base64," + base64.b64encode(_image(fmt, 200, 80, (200, 30, 30))).decode()
    pdf = pdf_service.render_application_pdf({
        "photo_url": photo, "signature_url": signature, "full_name": "Real Owner", "programme": "MCA",
        "payment_reference": "pay_x", "form_data": {},
    })

    assert pdf.startswith(b"%PDF")
    assert pdf.count(b"/Subtype /Image") >= 2   # photo and signature both made it in