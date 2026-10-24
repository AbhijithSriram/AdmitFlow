"""ERP statistics view (SRD FR-11). Owner: Person 2.

Registered at /api/admin (so the admin session cookie, which is scoped to that path, is sent).
The contract is in REMAINING_WORK.md section 3.
"""

from flask import Blueprint, jsonify

from app.middleware.admin_guard import admin_required

admin_stats_bp = Blueprint("admin_stats", __name__)


def _not_implemented():
    return jsonify({"success": False, "error": "Not implemented"}), 501


@admin_stats_bp.route("/stats/summary", methods=["GET"])
@admin_required
def stats_summary():
    """Registrations, applications started, paid, pending."""
    return _not_implemented()


@admin_stats_bp.route("/stats/programmes", methods=["GET"])
@admin_required
def stats_programmes():
    """Per programme and specialisation: seats, applied, paid, shortlisted."""
    return _not_implemented()


@admin_stats_bp.route("/stats/registrations", methods=["GET"])
@admin_required
def stats_registrations():
    """Registrations per day between ?from= and ?to= (days with none included, as zero)."""
    return _not_implemented()


@admin_stats_bp.route("/seats", methods=["GET"])
@admin_required
def get_seats():
    """The seat matrix (programme, specialisation, seats)."""
    return _not_implemented()


@admin_stats_bp.route("/seats", methods=["PUT"])
@admin_required
def set_seats():
    """Replace seat numbers."""
    return _not_implemented()
