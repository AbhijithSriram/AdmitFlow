from datetime import timedelta
from io import BytesIO

from flask import current_app
from minio import Minio


def _client() -> Minio:
    return Minio(
        current_app.config["MINIO_ENDPOINT"],
        access_key=current_app.config["MINIO_ACCESS_KEY"],
        secret_key=current_app.config["MINIO_SECRET_KEY"],
        secure=False,
    )


def upload_object(object_name: str, data: bytes, content_type: str) -> str:
    """Upload bytes to the configured bucket and return the object name (not a public URL)."""
    client = _client()
    bucket = current_app.config["MINIO_BUCKET"]
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    client.put_object(bucket, object_name, BytesIO(data), length=len(data), content_type=content_type)
    return object_name


def delete_object(object_name: str) -> None:
    """Delete an object from the bucket. No-op if it does not exist."""
    client = _client()
    bucket = current_app.config["MINIO_BUCKET"]
    client.remove_object(bucket, object_name)


def get_presigned_url(object_name: str) -> str:
    """Return a time-limited presigned URL for a private object (default 15 minutes)."""
    client = _client()
    bucket = current_app.config["MINIO_BUCKET"]
    expiry_seconds = current_app.config["MINIO_PRESIGNED_URL_EXPIRY_SECONDS"]
    return client.presigned_get_object(bucket, object_name, expires=timedelta(seconds=expiry_seconds))
