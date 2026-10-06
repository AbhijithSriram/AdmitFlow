import uuid
from datetime import datetime

from app.extensions import db


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AdminSession(db.Model):
    """Server-side admin session. `token_hash` is the SHA-256 of the cookie token."""

    __tablename__ = "admin_sessions"

    token_hash = db.Column(db.String(64), primary_key=True)
    admin_id = db.Column(db.String(36), db.ForeignKey("admins.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
