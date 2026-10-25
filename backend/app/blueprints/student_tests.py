"""Student side of the online aptitude test (SRD FR-10). Owner: Person 1.

Registered at /api/student/tests. Every route needs a student session and a PAID application, and
only tests assigned to that application (a test_submissions row) on a published paper are visible.
The timer is the server's: start sets started_at once and the deadline is computed from it, never
trusted from the browser. The contract is in REMAINING_WORK.md section 3.
"""
import logging
from datetime import datetime

from flask import Blueprint, jsonify, session

from app.extensions import db
from app.middleware.auth_guard import login_required
from app.models import Application, TestPaper, TestQuestion, TestSubmission
from app.services import test_service
from app.services.admin_service import is_uuid

log = logging.getLogger(__name__)

student_tests_bp = Blueprint("student_tests", __name__)


def _ok(data, status=200):
    return jsonify({"success": True, "data": data}), status


def _fail(message, status):
    return jsonify({"success": False, "error": message}), status


def _not_implemented():
    return _fail("Not implemented", 501)


def _iso_utc(value):
    """The server stores naive UTC; the trailing Z tells the browser so its countdown is right."""
    return value.isoformat() + "Z" if value else None


def _paid_application():
    """The signed-in student's application if it is PAID, else None (tests are for paid applicants)."""
    application = Application.query.filter_by(student_id=session["student_id"]).first()
    return application if application is not None and application.status == "PAID" else None


NOT_PAID = "Aptitude tests are available once your application fee has been paid."


@student_tests_bp.route("", methods=["GET"])
@login_required
def list_my_tests():
    """Tests assigned to me, each with a status: ASSIGNED, IN_PROGRESS or SUBMITTED."""
    application = _paid_application()
    if application is None:
        return _fail(NOT_PAID, 403)

    rows = (
        db.session.query(TestSubmission, TestPaper)
        .join(TestPaper, TestPaper.id == TestSubmission.test_paper_id)
        .filter(TestSubmission.application_id == application.id, TestPaper.is_published.is_(True))
        .order_by(TestSubmission.assigned_at)
        .all()
    )
    now = datetime.utcnow()
    if any([test_service.finalise_if_expired(sub, paper, now) for sub, paper in rows]):
        db.session.commit()

    # Scores are for admins only (team decision 3), so they never appear here.
    tests = [{
        "paper_id": paper.id,
        "title": paper.title,
        "duration_minutes": paper.duration_minutes,
        "question_count": len(paper.questions),
        "status": test_service.status(sub),
        "deadline": _iso_utc(test_service.deadline(sub, paper)),
    } for sub, paper in rows]
    return _ok({"tests": tests})


@student_tests_bp.route("/<paper_id>/start", methods=["POST"])
@login_required
def start_test(paper_id):
    """Start once (idempotent): returns the questions WITHOUT correct options, and the deadline."""
    application = _paid_application()
    if application is None:
        return _fail(NOT_PAID, 403)
    if not is_uuid(paper_id):
        return _fail("Test not found.", 404)

    # Lock the row so two tabs starting at once can't both set started_at.
    found = (
        db.session.query(TestSubmission, TestPaper)
        .join(TestPaper, TestPaper.id == TestSubmission.test_paper_id)
        .filter(TestSubmission.application_id == application.id, TestSubmission.test_paper_id == paper_id,
                TestPaper.is_published.is_(True))
        .with_for_update(of=TestSubmission)
        .first()
    )
    if found is None:
        return _fail("Test not found.", 404)
    sub, paper = found

    now = datetime.utcnow()
    if test_service.finalise_if_expired(sub, paper, now):
        db.session.commit()
        log.info("test closed at deadline paper_id=%s application_id=%s", paper.id, application.id)
    if sub.submitted_at is not None:
        db.session.commit()  # release the row lock
        return _fail("You have already submitted this test.", 409)

    if sub.started_at is None:
        sub.started_at = now
        log.info("test started paper_id=%s application_id=%s", paper.id, application.id)
    db.session.commit()

    closes = test_service.deadline(sub, paper)
    questions = TestQuestion.query.filter_by(test_paper_id=paper.id).order_by(TestQuestion.id).all()
    return _ok({
        "paper": {"id": paper.id, "title": paper.title, "duration_minutes": paper.duration_minutes},
        # Never correct_option or marks: the browser only ever sees the question and its options.
        "questions": [{
            "id": q.id,
            "text": q.question_text,
            "options": {"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d},
        } for q in questions],
        "answers": sub.answers or {},
        "deadline": _iso_utc(closes),
        "seconds_left": max(0, int((closes - now).total_seconds())),
    })


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
