"""Admin-portal tests run against REAL PostgreSQL so they exercise schema.sql, the
ON DELETE CASCADE chain and the audit_log trigger exactly as production will.

Setup:  createdb admitflow_test   then   TEST_DATABASE_URL=postgresql://user:pw@host:port/admitflow_test pytest
(The test database is wiped and rebuilt from migrations/ on every run - never point it at real data.)
"""
import os
import pathlib
from datetime import date

import psycopg2
import pytest

MIGRATIONS = pathlib.Path(__file__).resolve().parents[1] / "migrations"
TEST_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture(scope="session")
def _schema():
    if not TEST_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    conn = psycopg2.connect(TEST_URL.replace("postgresql+psycopg2://", "postgresql://"))
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    for name in ("schema.sql", "002_admin_portal.sql"):
        cur.execute((MIGRATIONS / name).read_text())
    conn.close()


@pytest.fixture(scope="session")
def _app(_schema):
    # create_app() can only be called once per process: Flask-Session registers its
    # `sessions` table on the shared SQLAlchemy metadata each time (existing team behaviour).
    os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
    from app import create_app
    from app.extensions import limiter

    app = create_app("testing")
    limiter.enabled = False  # re-enabled explicitly in the rate-limit test
    return app


@pytest.fixture
def app(_app):
    from app.extensions import db

    with _app.app_context():
        yield _app
        db.session.remove()
        # wipe data between tests (TRUNCATE is not blocked by the append-only row trigger)
        db.session.execute(db.text(
            "TRUNCATE students, admins, audit_log, admin_sessions RESTART IDENTITY CASCADE"))
        db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_admin(app):
    from app.extensions import bcrypt, db
    from app.models import Admin

    def _make(email="asha@college.edu", password="correct-horse-9", name="Asha"):
        a = Admin(name=name, email=email, password_hash=bcrypt.generate_password_hash(password).decode())
        db.session.add(a)
        db.session.commit()
        return a
    return _make


@pytest.fixture
def admin(make_admin):
    return make_admin()


@pytest.fixture
def login(client):
    def _login(email="asha@college.edu", password="correct-horse-9"):
        return client.post("/api/admin/login", json={"email": email, "password": password})
    return _login


@pytest.fixture
def logged_in(client, admin, login):
    assert login().status_code == 200
    return client


@pytest.fixture
def make_student(app):
    """Create a student, optionally with an application, drafts, payments and file names."""
    from app.extensions import db
    from app.models import Application, FormDraft, OtpToken, Payment, Student
    from datetime import datetime, timedelta

    counter = {"n": 0}

    def _make(name="Test Student", status=None, payment=None, files=True, created=None):
        counter["n"] += 1
        n = counter["n"]
        s = Student(full_name=name, date_of_birth=date(2004, 1, 1), gender="Female",
                    email=f"s{n}@example.com", phone=f"9{n:09d}", email_verified=True,
                    created_at=created or datetime.utcnow())
        db.session.add(s)
        db.session.flush()
        db.session.add(OtpToken(student_id=s.id, otp_hash="x", purpose="email_verification",
                                expires_at=datetime.utcnow() + timedelta(minutes=10)))
        if status:
            a = Application(student_id=s.id, status=status, programme="B.Tech", specialisation="CSE")
            if files:
                a.photo_url, a.signature_url = f"applications/{n}/photo.png", f"applications/{n}/signature.png"
                a.id_proof_url, a.pdf_url = f"applications/{n}/id.pdf", f"applications/{n}/application.pdf"
            db.session.add(a)
            db.session.flush()
            db.session.add(FormDraft(application_id=a.id, step_number=1, data={"father_name": "R"}))
            db.session.add(FormDraft(application_id=a.id, step_number=2, data={"city": "Chennai"}))
            if payment:
                db.session.add(Payment(application_id=a.id, amount=500, status="FAILED", razorpay_order_id="o1"))
                if payment == "SUCCESS":
                    db.session.add(Payment(application_id=a.id, amount=500, status="SUCCESS",
                                           razorpay_order_id="o2", razorpay_payment_id="p2"))
        db.session.commit()
        return s
    return _make


@pytest.fixture
def fake_minio(monkeypatch):
    """Replace MinIO with an in-memory recorder."""
    from app.services import minio_service

    class Fake:
        deleted: list = []
        fail_on: set = set()

    def delete_object(name):
        if name in Fake.fail_on:
            raise RuntimeError("minio down")
        Fake.deleted.append(name)

    Fake.deleted, Fake.fail_on = [], set()
    monkeypatch.setattr(minio_service, "delete_object", delete_object)
    monkeypatch.setattr(minio_service, "get_presigned_url", lambda name: f"http://minio.test/{name}?sig=abc")
    return Fake
