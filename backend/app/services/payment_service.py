import hmac
import hashlib

import razorpay
from flask import current_app


def _client() -> razorpay.Client:
    return razorpay.Client(auth=(current_app.config["RAZORPAY_KEY_ID"], current_app.config["RAZORPAY_KEY_SECRET"]))


def create_order(amount_paise: int, receipt: str) -> dict:
    """Create a Razorpay order and return the order payload (contains the order id)."""
    return _client().order.create({"amount": amount_paise, "currency": "INR", "receipt": receipt})


def verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify the HMAC-SHA256 signature Razorpay returns on the client callback. Never trust the client alone."""
    payload = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(
        current_app.config["RAZORPAY_KEY_SECRET"].encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
