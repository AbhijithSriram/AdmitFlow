from flask import Blueprint, jsonify

from app.middleware.auth_guard import login_required

application_bp = Blueprint("application", __name__)


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
