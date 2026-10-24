"""Student side of the online aptitude test (SRD FR-10). Owner: Person 1.

Registered at /api/student/tests. Every route needs a student session; the real routes must also
check that the applicant's application is PAID and that the test is assigned to them. The timer is
the server's: it is started once and enforced here, never trusted from the browser. The contract
is in REMAINING_WORK.md section 3.
"""

from flask import Blueprint, jsonify

from app.middleware.auth_guard import login_required

student_tests_bp = Blueprint("student_tests", __name__)


def _not_implemented():
    return jsonify({"success": False, "error": "Not implemented"}), 501


@student_tests_bp.route("", methods=["GET"])
@login_required
def list_my_tests():
    """Tests assigned to me, each with a status: ASSIGNED, IN_PROGRESS or SUBMITTED."""
    return _not_implemented()


@student_tests_bp.route("/<paper_id>/start", methods=["POST"])
@login_required
def start_test(paper_id):
    """Start once (idempotent): returns the questions WITHOUT correct options, and the deadline."""
    return _not_implemented()


@student_tests_bp.route("/<paper_id>/answers", methods=["PUT"])
@login_required
def save_answers(paper_id):
    """Save {question_id: "A".."D"}. Refused after the deadline."""
    return _not_implemented()


@student_tests_bp.route("/<paper_id>/submit", methods=["POST"])
@login_required
def submit_test(paper_id):
    """Grade the saved answers, store the score and set submitted_at."""
    return _not_implemented()
