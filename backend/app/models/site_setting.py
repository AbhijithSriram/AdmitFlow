from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class SiteSetting(db.Model):
    """One editable section of the site content (migration 007). See services/content_service.py."""

    __tablename__ = "site_settings"

    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(JSONB, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_by = db.Column(db.String(36), db.ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
