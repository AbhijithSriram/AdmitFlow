import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id = db.Column(db.String(36), db.ForeignKey("admins.id"), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)
    target_student_id = db.Column(db.String(36), nullable=True)
    target_email = db.Column(db.String(255), nullable=True)  # denormalised: survives student deletion
    details = db.Column(JSONB, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
