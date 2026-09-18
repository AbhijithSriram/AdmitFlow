from flask import Blueprint, jsonify

from app.middleware.auth_guard import login_required

payment_bp = Blueprint("payment", __name__)


@payment_bp.route("/student/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Return application status and navigation data for the logged-in student."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@payment_bp.route("/app/payment/create-order", methods=["POST"])
@login_required
def create_payment_order():
    """Create a Razorpay order and return the order ID."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@payment_bp.route("/app/payment/confirm", methods=["POST"])
@login_required
def confirm_payment():
    """Verify the Razorpay signature server-side and mark payment SUCCESS."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@payment_bp.route("/app/payment/failed", methods=["POST"])
@login_required
def payment_failed():
    """Record a failed payment attempt; application status becomes PAYMENT_PENDING."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@payment_bp.route("/app/receipt/<application_id>", methods=["GET"])
@login_required
def get_receipt(application_id):
    """Return a presigned URL to the receipt / application PDF."""
    return jsonify({"success": False, "error": "Not implemented"}), 501
