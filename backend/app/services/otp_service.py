import secrets
from datetime import datetime, timedelta

from flask import current_app

from app.extensions import bcrypt, db
from app.models import OtpToken


MAX_OTP_ATTEMPTS = 5


def generate_otp() -> str:
    """Return a cryptographically random 6-digit numeric OTP string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def create_otp_token(student_id: str, purpose: str) -> str:
    """Create and persist a bcrypt-hashed OTP for the student; returns the raw OTP to send by email."""
    raw_otp = generate_otp()
    otp_hash = bcrypt.generate_password_hash(raw_otp).decode("utf-8")
    expiry_minutes = current_app.config["OTP_EXPIRY_MINUTES"]

    # Only the newest code for this purpose is ever valid. Without this, burning the newest
    # code would just fall back to an older one that is still inside its 10 minutes, and an
    # attacker would get a fresh 5 guesses per outstanding code.
    OtpToken.query.filter_by(student_id=student_id, purpose=purpose, consumed_at=None).update(
        {"consumed_at": datetime.utcnow()}
    )

    token = OtpToken(
        student_id=student_id,
        otp_hash=otp_hash,
        purpose=purpose,
        expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
    )
    db.session.add(token)
    db.session.commit()
    return raw_otp


def verify_otp(student_id: str, purpose: str, submitted_otp: str) -> bool:
    """Check the submitted OTP against the latest unexpired, unconsumed token for this purpose."""
    token = (
        OtpToken.query.filter_by(student_id=student_id, purpose=purpose, consumed_at=None)
        .order_by(OtpToken.created_at.desc())
        .first()
    )
    if token is None or token.expires_at < datetime.utcnow():
        return False
    if not bcrypt.check_password_hash(token.otp_hash, submitted_otp):
        # A six-digit code has only a million possibilities, so wrong guesses are counted
        # per code and the code is burned after MAX_OTP_ATTEMPTS (the student requests a new one).
        token.failed_attempts += 1
        if token.failed_attempts >= MAX_OTP_ATTEMPTS:
            token.consumed_at = datetime.utcnow()
        db.session.commit()
        return False

    token.consumed_at = datetime.utcnow()
    db.session.commit()
    return True
