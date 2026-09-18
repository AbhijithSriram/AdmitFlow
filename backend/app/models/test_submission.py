import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class TestSubmission(db.Model):
    __tablename__ = "test_submissions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = db.Column(db.String(36), db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    test_paper_id = db.Column(db.String(36), db.ForeignKey("test_papers.id"), nullable=False)
    answers = db.Column(JSONB, nullable=False, default=dict)  # {question_id: selected_option}
    score = db.Column(db.Numeric(6, 2), nullable=True)
    submitted_at = db.Column(db.DateTime, nullable=True)
