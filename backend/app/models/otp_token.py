import uuid
from datetime import datetime

from app.extensions import db


class OtpToken(db.Model):
    __tablename__ = "otp_tokens"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    otp_hash = db.Column(db.String(255), nullable=False)
    purpose = db.Column(db.String(30), nullable=False)  # email_verification | password_reset
    expires_at = db.Column(db.DateTime, nullable=False)
    consumed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
