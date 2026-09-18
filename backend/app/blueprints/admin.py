from flask import Blueprint, jsonify

from app.middleware.admin_guard import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/login", methods=["POST"])
def admin_login():
    """Authenticate an admin account (no registration flow; seeded accounts only)."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@admin_bp.route("/logout", methods=["POST"])
@admin_required
def admin_logout():
    """Invalidate the current admin session."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@admin_bp.route("/students", methods=["GET"])
@admin_required
def list_students():
    """Paginated, filterable, searchable list of all applicants."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@admin_bp.route("/students/<student_id>", methods=["GET"])
@admin_required
def get_student(student_id):
    """Full application detail for one student."""
    return jsonify({"success": False, "error": "Not implemented"}), 501


@admin_bp.route("/students/<student_id>", methods=["DELETE"])
@admin_required
def delete_student(student_id):
    """Hard delete a student: MinIO cleanup, audit log entry, then cascading DB delete."""
    return jsonify({"success": False, "error": "Not implemented"}), 501
