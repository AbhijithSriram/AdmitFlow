"""Admin side of the online aptitude test (SRD FR-10). Owner: Person 4.

Registered at /api/admin/tests. Every route needs an admin session. The contract (request and
response shapes, rules) is in REMAINING_WORK.md section 3; each stub below is replaced in place.
"""

from flask import Blueprint, jsonify

from app.middleware.admin_guard import admin_required

admin_tests_bp = Blueprint("admin_tests", __name__)


def _not_implemented():
    return jsonify({"success": False, "error": "Not implemented"}), 501


@admin_tests_bp.route("", methods=["GET"])
@admin_required
def list_tests():
    """List test papers (title, duration, marks, published flag, how many are assigned/submitted)."""
    return _not_implemented()


@admin_tests_bp.route("", methods=["POST"])
@admin_required
def create_test():
    """Create a paper together with its questions in one transaction."""
    return _not_implemented()


@admin_tests_bp.route("/<paper_id>", methods=["GET"])
@admin_required
def get_test(paper_id):
    """One paper with all its questions, including the correct options (admin only)."""
    return _not_implemented()


@admin_tests_bp.route("/<paper_id>", methods=["PUT"])
@admin_required
def update_test(paper_id):
    """Edit a paper. Only allowed while it is unpublished."""
    return _not_implemented()


@admin_tests_bp.route("/<paper_id>", methods=["DELETE"])
@admin_required
def delete_test(paper_id):
    """Delete a paper. Refused once it has submissions (un-publish it instead)."""
    return _not_implemented()


@admin_tests_bp.route("/<paper_id>/publish", methods=["POST"])
@admin_required
def publish_test(paper_id):
    """Check the questions' marks add up to total_marks, then publish."""
    return _not_implemented()


@admin_tests_bp.route("/<paper_id>/assign", methods=["POST"])
@admin_required
def assign_test(paper_id):
    """Assign to PAID applicants, optionally filtered by programme and specialisation."""
    return _not_implemented()


@admin_tests_bp.route("/<paper_id>/results", methods=["GET"])
@admin_required
def test_results(paper_id):
    """Paginated results: applicant, score, pass/fail, submitted_at."""
    return _not_implemented()


@admin_tests_bp.route("/<paper_id>/reset/<application_id>", methods=["POST"])
@admin_required
def reset_attempt(paper_id, application_id):
    """Allow one applicant one more attempt (clears answers, score and timer)."""
    return _not_implemented()
