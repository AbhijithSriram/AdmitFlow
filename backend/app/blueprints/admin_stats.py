"""ERP statistics view (SRD FR-11). Owner: Person 2.

Registered at /api/admin (so the admin session cookie, which is scoped to that path, is sent).
The contract is in REMAINING_WORK.md section 3.
"""
import logging

from flask import Blueprint, g, jsonify, request

from app.extensions import db
from app.middleware.admin_guard import admin_required
from app.services import admin_service, stats_service

log = logging.getLogger(__name__)
admin_stats_bp = Blueprint("admin_stats", __name__)


def _ok(data=None, status=200):
    return jsonify({"success": True, "data": data if data is not None else {}}), status


def _fail(message, status=400):
    return jsonify({"success": False, "error": message}), status


@admin_stats_bp.route("/stats/summary", methods=["GET"])
@admin_required
def stats_summary():
    """Registrations, applications started, paid, pending."""
    return _ok(stats_service.get_summary())


@admin_stats_bp.route("/stats/programmes", methods=["GET"])
@admin_required
def stats_programmes():
    """Per programme and specialisation: seats, applied, paid, shortlisted."""
    return _ok({"programmes": stats_service.get_programmes()})


@admin_stats_bp.route("/stats/registrations", methods=["GET"])
@admin_required
def stats_registrations():
    """Registrations per day between ?from= and ?to= (days with none included, as zero)."""
    try:
        start, end = stats_service.parse_range(request.args.get("from"), request.args.get("to"))
    except stats_service.RangeError as exc:
        return _fail(str(exc), 400)
    return _ok({"registrations": stats_service.get_registrations(start, end),
                "from": start.isoformat(), "to": end.isoformat()})


@admin_stats_bp.route("/seats", methods=["GET"])
@admin_required
def get_seats():
    """The seat matrix (programme, specialisation, seats)."""
    return _ok({"seats": stats_service.get_seats()})


@admin_stats_bp.route("/seats", methods=["PUT"])
@admin_required
def set_seats():
    """Set seat numbers for the rows sent: body {"seats": [{programme, specialisation, seats}]}."""
    try:
        rows = stats_service.validate_seats(request.get_json(silent=True))
    except stats_service.SeatValidationError as exc:
        return _fail(str(exc), 400)

    try:
        changes = stats_service.set_seats(rows)
    except Exception:
        db.session.rollback()
        log.exception("seat update failed")
        return _fail("Could not save the seat numbers. Please try again.", 500)

    if changes:
        try:
            admin_service.write_audit(g.admin.id, "UPDATE_SEATS", details={"changes": changes})
        except Exception:
            # The seats are already saved: don't report a failure for a change that worked.
            log.exception("could not write the UPDATE_SEATS audit entry")
    return _ok({"seats": stats_service.get_seats(), "changed": len(changes)})
