"""Admin side of the online aptitude test (SRD FR-10). Owner: Person 4.

Registered at /api/admin/tests. Every route needs an admin session. The contract (request and
response shapes, rules) is in REMAINING_WORK.md section 3; the logic is in services/admin_test_service.py.
"""
import logging

from flask import Blueprint, g, jsonify, request

from app.middleware.admin_guard import admin_required
from app.services import admin_test_service as svc

log = logging.getLogger(__name__)
admin_tests_bp = Blueprint("admin_tests", __name__)


def _ok(data=None, status=200):
    return jsonify({"success": True, "data": data if data is not None else {}}), status


def _fail(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _run(action, status=200):
    """Run a service call and turn a ServiceError into the standard error response."""
    try:
        return _ok(action(), status)
    except svc.ServiceError as e:
        return _fail(e.message, e.status)


@admin_tests_bp.route("", methods=["GET"])
@admin_required
def list_tests():
    """List test papers (title, duration, marks, published flag, how many are assigned/submitted)."""
    return _run(lambda: {"tests": svc.list_papers()})


@admin_tests_bp.route("", methods=["POST"])
@admin_required
def create_test():
    """Create a paper together with its questions in one transaction."""
    return _run(lambda: svc.create_paper(request.get_json(silent=True), g.admin), 201)


@admin_tests_bp.route("/<paper_id>", methods=["GET"])
@admin_required
def get_test(paper_id):
    """One paper with all its questions, including the correct options (admin only)."""
    return _run(lambda: svc.get_paper(paper_id))


@admin_tests_bp.route("/<paper_id>", methods=["PUT"])
@admin_required
def update_test(paper_id):
    """Edit a paper. Only allowed while it is unpublished."""
    return _run(lambda: svc.update_paper(paper_id, request.get_json(silent=True)))


@admin_tests_bp.route("/<paper_id>", methods=["DELETE"])
@admin_required
def delete_test(paper_id):
    """Delete a paper. Refused (409) once it has submissions."""
    return _run(lambda: svc.delete_paper(paper_id) or {"deleted": True})


@admin_tests_bp.route("/<paper_id>/publish", methods=["POST"])
@admin_required
def publish_test(paper_id):
    """Check the questions' marks add up to total_marks, then publish."""
    return _run(lambda: svc.publish_paper(paper_id, g.admin))


@admin_tests_bp.route("/<paper_id>/assign", methods=["POST"])
@admin_required
def assign_test(paper_id):
    """Assign a published paper to PAID applicants. Body {programme?, specialisation?}. Safe to repeat."""
    return _run(lambda: svc.assign_paper(paper_id, request.get_json(silent=True), g.admin))


@admin_tests_bp.route("/<paper_id>/results", methods=["GET"])
@admin_required
def test_results(paper_id):
    """Paginated results: applicant, status, score, pass/fail, submitted_at."""
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        return _fail("Invalid page number.", 400)
    return _run(lambda: svc.results(paper_id, page))


@admin_tests_bp.route("/<paper_id>/reset/<application_id>", methods=["POST"])
@admin_required
def reset_test_attempt(paper_id, application_id):
    """Allow one applicant another attempt (clears their answers and score)."""
    return _run(lambda: svc.reset_attempt(paper_id, application_id, g.admin))
