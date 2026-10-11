import io
import os
from minio import Minio

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "admitflow-documents")


def get_minio_client():
  try:
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )
    if not client.bucket_exists(BUCKET_NAME):
      client.make_bucket(BUCKET_NAME)
    return client
  except Exception as e:
    print(f"MinIO Client warning: {e}")
    return None


def upload_file(file_data, object_name, content_type):
  """Uploads a file object to MinIO and returns its public access URL."""
  client = get_minio_client()
  if not client:
    # Local dev fallback URL if MinIO instance is offline
    return f"http://localhost:9000/{BUCKET_NAME}/{object_name}"

  try:
    file_bytes = file_data.read()
    file_length = len(file_bytes)
    file_stream = io.BytesIO(file_bytes)

    client.put_object(
        bucket_name=BUCKET_NAME,
        object_name=object_name,
        data=file_stream,
        length=file_length,
        content_type=content_type,
    )
    return f"http://{MINIO_ENDPOINT}/{BUCKET_NAME}/{object_name}"
  except Exception as e:
    print(f"MinIO Upload Error: {e}")
    return f"http://localhost:9000/{BUCKET_NAME}/{object_name}"