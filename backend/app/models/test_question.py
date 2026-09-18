import uuid

from app.extensions import db


class TestQuestion(db.Model):
    __tablename__ = "test_questions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_paper_id = db.Column(db.String(36), db.ForeignKey("test_papers.id", ondelete="CASCADE"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'A' | 'B' | 'C' | 'D'
