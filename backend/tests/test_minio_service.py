"""minio_service contracts that other slices rely on."""
import pytest

from app.services import minio_service


def test_delete_object_raises_when_minio_is_unreachable(app, monkeypatch):
    """Admin hard-delete aborts (instead of orphaning files) only if this raises."""

    class Down:
        def remove_object(self, bucket, name):
            raise ConnectionError("minio down")

    monkeypatch.setattr(minio_service, "get_minio_client", lambda: Down())

    with pytest.raises(ConnectionError):
        minio_service.delete_object("applications/1/photo.png")


def test_delete_object_removes_from_the_configured_bucket(app, monkeypatch):
    removed = []

    class Ok:
        def remove_object(self, bucket, name):
            removed.append((bucket, name))

    monkeypatch.setattr(minio_service, "get_minio_client", lambda: Ok())

    minio_service.delete_object("applications/1/photo.png")

    assert removed == [(app.config["MINIO_BUCKET"], "applications/1/photo.png")]


def test_signed_links_use_the_public_host_when_one_is_configured(app, monkeypatch):
    """On a server the browser cannot reach MINIO_ENDPOINT (127.0.0.1), so links must be
    signed for the public host. This also proves signing makes no network call: the host
    below does not exist."""
    monkeypatch.setitem(app.config, "MINIO_ACCESS_KEY", "test-access")  # without keys MinIO returns an unsigned link
    monkeypatch.setitem(app.config, "MINIO_SECRET_KEY", "test-secret-key")
    monkeypatch.setitem(app.config, "MINIO_PUBLIC_ENDPOINT", "files.example.test")
    monkeypatch.setitem(app.config, "MINIO_PUBLIC_SECURE", True)

    url = minio_service.get_presigned_url("applications/abc/photo.png")

    assert url.startswith(f"https://files.example.test/{app.config['MINIO_BUCKET']}/applications/abc/photo.png?")
    assert "X-Amz-Signature=" in url and "X-Amz-Expires=900" in url
    assert "127.0.0.1" not in url and "localhost" not in url


def test_public_host_can_be_plain_http_for_a_lan_setup(app, monkeypatch):
    monkeypatch.setitem(app.config, "MINIO_ACCESS_KEY", "test-access")
    monkeypatch.setitem(app.config, "MINIO_SECRET_KEY", "test-secret-key")
    monkeypatch.setitem(app.config, "MINIO_PUBLIC_ENDPOINT", "files.example.test:8088")
    monkeypatch.setitem(app.config, "MINIO_PUBLIC_SECURE", False)

    assert minio_service.get_presigned_url("applications/abc/photo.png").startswith("http://files.example.test:8088/")
