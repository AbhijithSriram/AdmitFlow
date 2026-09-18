import uuid
from datetime import datetime

from app.extensions import db


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(
        db.String(36), db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status = db.Column(db.String(30), nullable=False, default="NOT_STARTED", index=True)
    guidelines_accepted_at = db.Column(db.DateTime, nullable=True)

    programme = db.Column(db.String(255), nullable=True)
    specialisation = db.Column(db.String(255), nullable=True)

    photo_url = db.Column(db.String(500), nullable=True)
    signature_url = db.Column(db.String(500), nullable=True)
    id_proof_url = db.Column(db.String(500), nullable=True)
    pdf_url = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    form_drafts = db.relationship("FormDraft", cascade="all, delete-orphan", backref="application")
    payments = db.relationship("Payment", cascade="all, delete-orphan", backref="application")
    test_submissions = db.relationship("TestSubmission", cascade="all, delete-orphan", backref="application")
