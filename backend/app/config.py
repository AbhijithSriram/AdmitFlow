import os


class BaseConfig:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_TYPE = "sqlalchemy"
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("SESSION_TIMEOUT_SECONDS", 1800))
    SESSION_COOKIE_NAME = "admitflow_student_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    ADMIN_SESSION_COOKIE_NAME = "admitflow_admin_session"

    # Academic-project disclaimer on every page, email and PDF. A per-deployment server setting (not
    # site content), so no admin can switch it off on the public demo. A real college deployment sets
    # ADMITFLOW_DEMO_MODE=0.
    DEMO_MODE = os.environ.get("ADMITFLOW_DEMO_MODE", "1") == "1"

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
    MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "admitflow")
    MINIO_PRESIGNED_URL_EXPIRY_SECONDS = 15 * 60
    # On a server MINIO_ENDPOINT is a loopback address that visitors' browsers cannot reach.
    # When this is set, signed download links use this public host instead (nginx forwards
    # it to MinIO). Unset on a laptop, where the browser can reach MINIO_ENDPOINT directly.
    MINIO_PUBLIC_ENDPOINT = os.environ.get("MINIO_PUBLIC_ENDPOINT")
    MINIO_PUBLIC_SECURE = os.environ.get("MINIO_PUBLIC_SECURE", "1") == "1"

    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")

    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

    RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY")

    OTP_EXPIRY_MINUTES = 10
    BCRYPT_LOG_ROUNDS = 12
    LOGIN_LOCKOUT_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL")


_CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str | None):
    name = name or os.environ.get("FLASK_ENV", "development")
    return _CONFIGS.get(name, DevelopmentConfig)
