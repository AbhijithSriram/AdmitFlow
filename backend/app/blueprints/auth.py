from flask import Blueprint, jsonify, request

from app.extensions import limiter
from app.middleware.auth_guard import login_required
from app.services import email_service, otp_service

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["POST"])
@limiter.limit("10 per minute")
def signup():
    """Register a new applicant. Requires a valid reCAPTCHA token."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    """Send or resend a 6-digit OTP to the registered email."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """Verify the submitted OTP and mark the email as confirmed."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


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
