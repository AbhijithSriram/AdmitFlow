"""Applicant data export, CSV and PDF (SRD FR-11). Owner: Person 3.

Registered at /api/admin/export. Takes the same filter parameters as GET /api/admin/students.
Exports contain personal data: every export must write an audit_log row, and CSV cells that start
with = + - or @ must be neutralised (formula injection). The contract is in REMAINING_WORK.md
section 3.
"""

from flask import Blueprint, jsonify

from app.middleware.admin_guard import admin_required

admin_export_bp = Blueprint("admin_export", __name__)


def _not_implemented():
    return jsonify({"success": False, "error": "Not implemented"}), 501


@admin_export_bp.route("/applicants.csv", methods=["GET"])
@admin_required
def export_csv():
    """Filtered applicants as a CSV download."""
    return _not_implemented()


@admin_export_bp.route("/applicants.pdf", methods=["GET"])
@admin_required
def export_pdf():
    """Filtered applicants as a PDF table (WeasyPrint)."""
    return _not_implemented()
