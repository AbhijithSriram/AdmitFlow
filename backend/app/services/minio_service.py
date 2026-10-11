from datetime import timedelta
from io import BytesIO
from flask import current_app
from minio import Minio


def get_minio_client():
    endpoint = current_app.config["MINIO_ENDPOINT"]
    access_key = current_app.config["MINIO_ACCESS_KEY"]
    secret_key = current_app.config["MINIO_SECRET_KEY"]
    secure = current_app.config.get("MINIO_SECURE", False)

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def upload_object(object_name: str, data_bytes: bytes, content_type: str) -> str:
    """Upload raw bytes to MinIO and return object_name contract."""
    client = get_minio_client()
    bucket = current_app.config["MINIO_BUCKET"]

    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    stream = BytesIO(data_bytes)
    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=stream,
        length=len(data_bytes),
        content_type=content_type,
    )
    return object_name


def delete_object(object_name: str) -> None:
    """Delete an object from MinIO."""
    client = get_minio_client()
    bucket = current_app.config["MINIO_BUCKET"]
    try:
        client.remove_object(bucket, object_name)
    except Exception:
        pass


def get_presigned_url(object_name: str, expires_minutes: int = 15) -> str:
    """Generate a 15-minute presigned download URL."""
    client = get_minio_client()
    bucket = current_app.config["MINIO_BUCKET"]
    return client.presigned_get_object(
        bucket_name=bucket,
        object_name=object_name,
        expires=timedelta(minutes=expires_minutes),
    )