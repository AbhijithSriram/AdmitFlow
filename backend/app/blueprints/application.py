from flask import Blueprint, jsonify

from app.middleware.auth_guard import login_required

application_bp = Blueprint("application", __name__)


@application_bp.route("/student/dashboard", methods=["GET"])
@login_required
def dashboard():
    """Return application status and navigation data for the logged-in student."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@application_bp.route("/app/start", methods=["POST"])
@login_required
def start_application():
    """Accept guidelines and create the application record."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@application_bp.route("/app/draft/<application_id>/step/<int:step_number>", methods=["PATCH"])
@login_required
def save_draft_step(application_id, step_number):
    """Auto-save a partial step update (JSONB upsert)."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@application_bp.route("/app/draft/<application_id>", methods=["GET"])
@login_required
def get_draft(application_id):
    """Retrieve all saved step data for form rehydration."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@application_bp.route("/app/upload/<application_id>/<doc_type>", methods=["POST"])
@login_required
def upload_document(application_id, doc_type):
    """Validate and upload a document (photo / signature / id_proof) to MinIO."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@application_bp.route("/app/payment/create-order", methods=["POST"])
@login_required
def create_payment_order():
    """Create a Razorpay order and return the order ID."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@application_bp.route("/app/payment/confirm", methods=["POST"])
@login_required
def confirm_payment():
    """Verify the Razorpay signature server-side and mark payment SUCCESS."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@application_bp.route("/app/payment/failed", methods=["POST"])
@login_required
def payment_failed():
    """Record a failed payment attempt; application status becomes PAYMENT_PENDING."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@application_bp.route("/app/receipt/<application_id>", methods=["GET"])
@login_required
def get_receipt(application_id):
    """Return a presigned URL to the receipt / application PDF."""
    return jsonify({"success": False, "error": "Not implemented"}), 501
