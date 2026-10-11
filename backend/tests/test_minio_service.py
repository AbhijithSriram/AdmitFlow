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
