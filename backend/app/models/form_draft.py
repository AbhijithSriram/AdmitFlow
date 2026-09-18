import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class FormDraft(db.Model):
    __tablename__ = "form_drafts"
    __table_args__ = (db.UniqueConstraint("application_id", "step_number", name="uq_form_drafts_app_step"),)

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = db.Column(db.String(36), db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    data = db.Column(JSONB, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
