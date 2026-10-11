import logging
import re
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request, session

from app.extensions import db, limiter
from app.middleware.auth_guard import login_required
from app.models import OtpToken, Student
from app.services import email_service, otp_service, recaptcha_service

log = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

OTP_PURPOSES = {"email_verification", "password_reset"}
OTP_RESEND_COOLDOWN_SECONDS = 60
GENDERS = {"Male", "Female", "Other"}
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_PATTERN = re.compile(r"^\d{10}$")


def _ok(data=None, status=200):
    return jsonify({"success": True, "data": data if data is not None else {}}), status


def _fail(message, status=400, field=None):
    body = {"success": False, "error": message}
    if field:
        body["field"] = field
    return jsonify(body), status


def _clean_str(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _validate_signup(body: dict):
    """Returns (cleaned_fields, error_message, error_field)."""
    full_name = _clean_str(body.get("full_name"))
    email = _clean_str(body.get("email")).lower()
    phone = _clean_str(body.get("phone"))
    gender = _clean_str(body.get("gender"))

    if not full_name or len(full_name) > 255:
        return None, "Enter your full name.", "full_name"
    try:
        dob = datetime.strptime(_clean_str(body.get("date_of_birth")), "%Y-%m-%d").date()
    except ValueError:
        return None, "Enter a valid date of birth.", "date_of_birth"
    if dob >= date.today():
        return None, "Date of birth must be in the past.", "date_of_birth"
    if gender not in GENDERS:
        return None, "Select a gender.", "gender"
    if len(email) > 255 or not EMAIL_PATTERN.match(email):
        return None, "Enter a valid email address.", "email"
    if not PHONE_PATTERN.match(phone):
        return None, "Enter a 10-digit mobile number.", "phone"

    return {"full_name": full_name, "date_of_birth": dob, "gender": gender, "email": email, "phone": phone}, None, None


@auth_bp.route("/signup", methods=["POST"])
@limiter.limit("10 per minute")
def signup():
    """Register a new applicant. Requires a valid reCAPTCHA token."""
    body = request.get_json(silent=True) or {}
    fields, error, field = _validate_signup(body)
    if error:
        return _fail(error, 400, field)

    if not recaptcha_service.verify_token(body.get("recaptcha_token"), request.remote_addr):
        return _fail("Please complete the reCAPTCHA check.", 400, "recaptcha")

    student = Student.query.filter_by(email=fields["email"]).first()
    if student is not None and student.email_verified:
        return _fail("An account with this email already exists. Please log in.", 409, "email")

    phone_owner = Student.query.filter_by(phone=fields["phone"]).first()
    if phone_owner is not None and (student is None or phone_owner.id != student.id):
        return _fail("This mobile number is already registered.", 409, "phone")

    if student is None:
        student = Student(**fields)
        db.session.add(student)
    else:
        # Same email registered earlier but never verified: let them correct their details.
        for key, value in fields.items():
            setattr(student, key, value)
    db.session.commit()

    log.info("signup student_id=%s", student.id)
    return _ok({"student_id": str(student.id), "email": student.email}, 201)


def _otp_target(body: dict):
    """Resolve the (student, purpose) a send/verify request is about, or (None, purpose)."""
    purpose = _clean_str(body.get("purpose")) or "email_verification"
    if purpose not in OTP_PURPOSES:
        return None, None
    email = _clean_str(body.get("email")).lower()
    student = Student.query.filter_by(email=email).first() if email else None
    if student is not None:
        # An OTP is only meaningful in the state the purpose expects.
        if purpose == "email_verification" and student.email_verified:
            student = None
        if purpose == "password_reset" and student.password_hash is None:
            student = None
    return student, purpose


@auth_bp.route("/send-otp", methods=["POST"])
@limiter.limit("10 per minute")
def send_otp():
    """Send or resend a 6-digit OTP to the registered email."""
    body = request.get_json(silent=True) or {}
    student, purpose = _otp_target(body)
    if purpose is None:
        return _fail("Invalid request.", 400)

    # Identical response whether or not the account exists, so this can't be used to probe emails.
    generic = {"message": "If this email is registered, a verification code has been sent."}
    if student is None:
        return _ok(generic)

    latest = (
        OtpToken.query.filter_by(student_id=student.id, purpose=purpose)
        .order_by(OtpToken.created_at.desc())
        .first()
    )
    if latest is not None:
        wait = OTP_RESEND_COOLDOWN_SECONDS - (datetime.utcnow() - latest.created_at).total_seconds()
        if wait > 0:
            return _fail(f"Please wait {int(wait) + 1} seconds before requesting another code.", 429)

    raw_otp = otp_service.create_otp_token(str(student.id), purpose)
    try:
        if purpose == "email_verification":
            email_service.send_otp_email(student.email, raw_otp)
        else:
            email_service.send_password_reset_email(student.email, raw_otp)
    except Exception:
        log.exception("could not send OTP email student_id=%s", student.id)
        return _fail("We couldn't send the email right now. Please try again shortly.", 503)

    return _ok(generic)


@auth_bp.route("/verify-otp", methods=["POST"])
@limiter.limit("5 per minute")
def verify_otp():
    """Verify the submitted OTP and mark the email as confirmed."""
    body = request.get_json(silent=True) or {}
    student, purpose = _otp_target(body)
    otp = _clean_str(body.get("otp"))
    invalid = _fail("Invalid or expired code.", 400, "otp")
    if purpose is None or student is None or not re.fullmatch(r"\d{6}", otp):
        return invalid
    if not otp_service.verify_otp(str(student.id), purpose, otp):
        return invalid

    if purpose == "email_verification":
        student.email_verified = True
        db.session.commit()

    # Server-side proof that this browser just passed the OTP; /set-password requires it.
    session.clear()
    session["otp_verified"] = {
        "student_id": str(student.id),
        "purpose": purpose,
        "expires": (datetime.utcnow() + timedelta(minutes=15)).isoformat(),
    }
    session.permanent = True
    return _ok({"verified": True, "purpose": purpose})


@auth_bp.route("/set-password", methods=["POST"])
def set_password():
    """Set the account password after OTP verification."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    """Authenticate with email + password and create a student session."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Invalidate the current student session."""
    return jsonify({"success": False, "error": "Not implemented"}), 501
