import uuid
from datetime import datetime

from app.extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id = db.Column(db.String(36), db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    razorpay_order_id = db.Column(db.String(255), nullable=True)
    razorpay_payment_id = db.Column(db.String(255), nullable=True)
    razorpay_signature = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="CREATED")  # CREATED | SUCCESS | FAILED
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
