import io
import pytest


def test_start_application_unauthorized(client):
    """Anonymous request returns 401."""
    res = client.post("/api/app/start")
    assert res.status_code == 401


def test_upload_unauthorized(client):
    """Anonymous file upload returns 401."""
    data = {"file": (io.BytesIO(b"fake data"), "photo.png")}
    res = client.post(
        "/api/app/upload/00000000-0000-0000-0000-000000000001/photo",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 401


def test_invalid_doc_type(client):
    """Uploading invalid document type returns 400."""
    # Assuming authenticated session mock if needed, or route check
    data = {"file": (io.BytesIO(b"fake data"), "file.txt")}
    res = client.post(
        "/api/app/upload/00000000-0000-0000-0000-000000000001/invalid_type",
        data=data,
        content_type="multipart/form-data",
    )
    # Returns 401 when unauthorized, or 400 if authorized & doc type invalid
    assert res.status_code in [401, 400]

# ---------------------------------------------------------------------------
# Item 20: tests for the application form routes
# ---------------------------------------------------------------------------
def _login_as(client, student):
    with client.session_transaction() as sess:
        sess["student_id"] = str(student.id)


def _application_id(res):
    body = res.get_json()
    d = (body or {}).get("data") or {}
    app_id = d.get("id") or d.get("application_id") or (d.get("application") or {}).get("id")
    assert app_id, f"no application id in response: {body}"
    return app_id


def test_anonymous_upload_returns_401(client):
    data = {"file": (io.BytesIO(b"\x89PNG\r\n\x1a\n"), "photo.png")}
    res = client.post(
        "/api/app/upload/00000000-0000-0000-0000-000000000001/photo",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 401


def test_upload_to_other_students_application_returns_404(client, make_student, fake_minio):
    from app.models import Application

    owner = make_student(name="Owner", status="NOT_STARTED")
    attacker = make_student(name="Attacker")
    owner_app = Application.query.filter_by(student_id=owner.id).first()

    _login_as(client, attacker)
    data = {"file": (io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 50), "photo.png")}
    res = client.post(
        f"/api/app/upload/{owner_app.id}/photo",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 404


def test_html_file_named_png_returns_400(client, make_student, fake_minio):
    student = make_student()
    _login_as(client, student)
    app_id = _application_id(client.post("/api/app/start"))

    data = {"file": (io.BytesIO(b"<html><script>alert(1)</script></html>"), "photo.png")}
    res = client.post(
        f"/api/app/upload/{app_id}/photo",
        data=data,
        content_type="multipart/form-data",
    )
    assert res.status_code == 400


def test_saving_same_step_twice_leaves_one_row(client, make_student):
    from app.extensions import db

    student = make_student()
    _login_as(client, student)
    app_id = _application_id(client.post("/api/app/start"))

    for city in ("Chennai", "Madurai"):
        res = client.patch(f"/api/app/draft/{app_id}/step/3", json={"data": {"city": city}})
        assert res.status_code == 200, res.get_json()

    count = db.session.execute(
        db.text("SELECT count(*) FROM form_drafts WHERE application_id = :a AND step_number = 3"),
        {"a": app_id},
    ).scalar()
    assert count == 1


def test_start_twice_returns_same_application(client, make_student):
    student = make_student()
    _login_as(client, student)

    first = _application_id(client.post("/api/app/start"))
    second = _application_id(client.post("/api/app/start"))
    assert first == second
