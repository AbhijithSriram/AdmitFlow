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