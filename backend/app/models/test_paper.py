import uuid
from datetime import datetime

from app.extensions import db


class TestPaper(db.Model):
    __tablename__ = "test_papers"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    pass_marks = db.Column(db.Integer, nullable=False)
    created_by = db.Column(db.String(36), db.ForeignKey("admins.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    questions = db.relationship("TestQuestion", cascade="all, delete-orphan", backref="test_paper")
