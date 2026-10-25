"""Admin side of the online aptitude test (SRD FR-10). Routes live in blueprints/admin_tests.py.

A test_submissions row IS the assignment: assigning inserts it with started_at and submitted_at
empty, and the student side (Person 1) fills them in. Scores are never shown to students.
"""
import logging
import math
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.extensions import db
from app.models import Application, Student
from app.models.test_paper import TestPaper
from app.models.test_question import TestQuestion
from app.models.test_submission import TestSubmission
from app.services import admin_service

log = logging.getLogger(__name__)

PER_PAGE = admin_service.PER_PAGE  # 20, same as the applicant list
MAX_QUESTIONS = 200
# test_submissions.score is NUMERIC(6,2): it cannot hold 10000 or more. A published paper's questions
# add up to exactly total_marks, so capping total_marks keeps every possible score storable.
MAX_TOTAL_MARKS = 9999
_INSERT_CHUNK = 1000  # rows per INSERT when assigning to many applicants


class ServiceError(Exception):
    """A rule the admin broke. The route turns it into {success: false, error: message} + status."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# ---------------------------------------------------------------- validation
def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)  # True/False are ints in Python


def _text(value, max_len: int) -> str | None:
    """A non-empty, trimmed string of at most max_len characters, else None."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if 0 < len(value) <= max_len else None


def parse_paper(body) -> dict:
    """Validate a paper + its questions. Raises ServiceError(400, ...) with a message saying what to fix.

    Rules: 4 options (A-D) per question, exactly one correct option, marks per question,
    1 to MAX_QUESTIONS questions, 1 <= total_marks <= MAX_TOTAL_MARKS, and 0 <= pass_marks <= total_marks.
    Whether the question marks add up to total_marks is checked when the paper is PUBLISHED.
    """
    if not isinstance(body, dict):
        raise ServiceError(400, "Send the test as JSON.")
    title = _text(body.get("title"), 255)
    if title is None:
        raise ServiceError(400, "Enter a title (up to 255 characters).")
    duration, total, pass_marks = body.get("duration_minutes"), body.get("total_marks"), body.get("pass_marks")
    if not _is_int(duration) or not 1 <= duration <= 600:
        raise ServiceError(400, "Duration must be a whole number of minutes between 1 and 600.")
    if not _is_int(total) or not 1 <= total <= MAX_TOTAL_MARKS:
        raise ServiceError(400, f"Total marks must be a whole number from 1 to {MAX_TOTAL_MARKS}.")
    if not _is_int(pass_marks) or not 0 <= pass_marks <= total:
        raise ServiceError(400, "Pass marks must be between 0 and the total marks.")

    raw = body.get("questions")
    if not isinstance(raw, list) or not raw:
        raise ServiceError(400, "Add at least one question.")
    if len(raw) > MAX_QUESTIONS:
        raise ServiceError(400, f"A test can have at most {MAX_QUESTIONS} questions.")

    questions = []
    for n, q in enumerate(raw, start=1):
        if not isinstance(q, dict):
            raise ServiceError(400, f"Question {n}: invalid format.")
        text = _text(q.get("question_text"), 5000)
        options = [_text(q.get(f"option_{k}"), 500) for k in "abcd"]
        marks = q.get("marks", 1)
        if text is None:
            raise ServiceError(400, f"Question {n}: enter the question text.")
        if any(o is None for o in options):
            raise ServiceError(400, f"Question {n}: all four options (A to D) need text (up to 500 characters).")
        if q.get("correct_option") not in ("A", "B", "C", "D"):
            raise ServiceError(400, f"Question {n}: choose exactly one correct option (A, B, C or D).")
        if not _is_int(marks) or not 1 <= marks <= 100:
            raise ServiceError(400, f"Question {n}: marks must be a whole number from 1 to 100.")
        questions.append({"question_text": text, "option_a": options[0], "option_b": options[1],
                          "option_c": options[2], "option_d": options[3],
                          "correct_option": q["correct_option"], "marks": marks})
    return {"title": title, "duration_minutes": duration, "total_marks": total,
            "pass_marks": pass_marks, "questions": questions}


def _question_id(position: int) -> str:
    """test_questions has no position column, so rows would come back in random order.
    Putting the position in the first 8 hex digits of the id makes ORDER BY id the authoring order."""
    return str(uuid.UUID(f"{position:08x}" + uuid.uuid4().hex[8:]))


def _build_questions(parsed: list[dict]) -> list[TestQuestion]:
    return [TestQuestion(id=_question_id(i), **q) for i, q in enumerate(parsed)]


# ------------------------------------------------------------------ read side
def _question_dict(q: TestQuestion) -> dict:
    return {"id": str(q.id), "question_text": q.question_text, "option_a": q.option_a, "option_b": q.option_b,
            "option_c": q.option_c, "option_d": q.option_d, "correct_option": q.correct_option, "marks": q.marks}


def _paper_dict(paper: TestPaper, assigned: int = 0, submitted: int = 0, questions: list | None = None) -> dict:
    data = {"id": str(paper.id), "title": paper.title, "duration_minutes": paper.duration_minutes,
            "total_marks": paper.total_marks, "pass_marks": paper.pass_marks,
            "is_published": paper.is_published, "created_at": paper.created_at.isoformat(),
            "assigned": assigned, "submitted": submitted}
    if questions is not None:
        data["questions"] = [_question_dict(q) for q in questions]
    return data


def _submission_counts(paper_ids: list[str]) -> dict[str, tuple[int, int]]:
    if not paper_ids:
        return {}
    rows = db.session.execute(
        select(TestSubmission.test_paper_id, func.count(), func.count(TestSubmission.submitted_at))
        .where(TestSubmission.test_paper_id.in_(paper_ids)).group_by(TestSubmission.test_paper_id)).all()
    return {str(r[0]): (r[1], r[2]) for r in rows}


def _ordered_questions(paper_id: str) -> list[TestQuestion]:
    return db.session.execute(
        select(TestQuestion).where(TestQuestion.test_paper_id == paper_id).order_by(TestQuestion.id)).scalars().all()


def get_paper_or_404(paper_id: str) -> TestPaper:
    paper_id = str(paper_id)
    paper = db.session.get(TestPaper, paper_id) if admin_service.is_uuid(paper_id) else None
    if paper is None:
        raise ServiceError(404, "Test not found.")
    return paper


def list_papers() -> list[dict]:
    """All papers, newest first, with how many applicants are assigned / have submitted."""
    papers = db.session.execute(select(TestPaper).order_by(TestPaper.created_at.desc())).scalars().all()
    counts = _submission_counts([str(p.id) for p in papers])
    qcounts = {str(k): v for k, v in db.session.execute(
        select(TestQuestion.test_paper_id, func.count()).group_by(TestQuestion.test_paper_id)).all()}
    out = []
    for p in papers:
        assigned, submitted = counts.get(str(p.id), (0, 0))
        d = _paper_dict(p, assigned, submitted)
        d["question_count"] = qcounts.get(str(p.id), 0)
        out.append(d)
    return out


def get_paper(paper_id: str) -> dict:
    """One paper with all its questions, correct options included (admin only)."""
    paper = get_paper_or_404(paper_id)
    pid = str(paper.id)
    assigned, submitted = _submission_counts([pid]).get(pid, (0, 0))
    return _paper_dict(paper, assigned, submitted, _ordered_questions(pid))


# ----------------------------------------------------------------- write side
def _commit_with_audit(admin_id: str, action: str, details: dict,
                       student_id: str | None = None, student_email: str | None = None) -> None:
    """Record the audit entry FIRST, then commit the pending change (the audit-first rule of the export).

    The caller has already validated and staged its change in db.session but not committed it, so:
      - if the audit entry cannot be written, the staged change is rolled back and nothing happened;
      - if the commit then fails, the change is rolled back and a <action>_FAILED entry is recorded
        (as the hard delete does), so the log never claims something that did not happen.
    write_audit uses its own session, so the pending change does not interfere with it.
    """
    try:
        admin_service.write_audit(admin_id, action, student_id, student_email, details)
    except Exception:
        db.session.rollback()
        log.exception("audit entry %s could not be written; change rolled back admin=%s", action, admin_id)
        raise ServiceError(500, "This action could not be recorded in the audit log, so nothing was changed. "
                                "Please try again.")
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.exception("commit failed after audit entry %s admin=%s", action, admin_id)
        try:
            admin_service.write_audit(admin_id, f"{action}_FAILED", student_id, student_email, details)
        except Exception:
            log.exception("could not record %s_FAILED admin=%s", action, admin_id)
        raise


def create_paper(body, admin) -> dict:
    """Create a paper and its questions in ONE transaction: a bad question leaves nothing behind."""
    parsed = parse_paper(body)
    paper = TestPaper(title=parsed["title"], duration_minutes=parsed["duration_minutes"],
                      total_marks=parsed["total_marks"], pass_marks=parsed["pass_marks"],
                      created_by=admin.id, is_published=False)
    paper.questions = _build_questions(parsed["questions"])
    try:
        db.session.add(paper)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return get_paper(str(paper.id))


def update_paper(paper_id: str, body) -> dict:
    """Edit a paper (replaces its questions). Only while unpublished and with no submissions."""
    paper = get_paper_or_404(paper_id)
    if paper.is_published:
        raise ServiceError(409, "A published test can't be edited.")
    if _submission_counts([str(paper.id)]).get(str(paper.id), (0, 0))[0]:
        raise ServiceError(409, "This test already has assigned applicants, so it can't be edited.")
    parsed = parse_paper(body)
    paper.title, paper.duration_minutes = parsed["title"], parsed["duration_minutes"]
    paper.total_marks, paper.pass_marks = parsed["total_marks"], parsed["pass_marks"]
    paper.questions = _build_questions(parsed["questions"])  # old questions are deleted (delete-orphan)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return get_paper(str(paper.id))


def delete_paper(paper_id: str) -> None:
    """Delete a paper. Refused (409) once any applicant is assigned: test_submissions has no cascade."""
    paper = get_paper_or_404(paper_id)
    if _submission_counts([str(paper.id)]).get(str(paper.id), (0, 0))[0]:
        raise ServiceError(409, "This test already has assigned applicants, so it can't be deleted.")
    db.session.delete(paper)  # its questions go with it
    db.session.commit()


def publish_paper(paper_id: str, admin) -> dict:
    """Publish a paper once its question marks add up to total_marks. Publishing twice is harmless."""
    paper = get_paper_or_404(paper_id)
    if not paper.is_published:
        questions = _ordered_questions(str(paper.id))
        if not questions:
            raise ServiceError(400, "Add at least one question before publishing.")
        marks = sum(q.marks for q in questions)
        if marks != paper.total_marks:
            raise ServiceError(400, f"The questions add up to {marks} marks but the total is {paper.total_marks}. "
                                    "Make them equal, then publish.")
        paper.is_published = True
        _commit_with_audit(admin.id, "TEST_PUBLISHED", {"paper_id": str(paper.id), "title": paper.title})
    return get_paper(str(paper.id))


def assign_paper(paper_id: str, body, admin) -> dict:
    """Assign a published paper to every PAID applicant (optionally one programme/specialisation).

    Inserts one test_submissions row per applicant with INSERT ... ON CONFLICT DO NOTHING on the
    unique index from migration 005, so assigning twice never duplicates and never resets anyone.
    """
    paper = get_paper_or_404(paper_id)
    if not paper.is_published:
        raise ServiceError(409, "Publish the test before assigning it.")
    body = body if isinstance(body, dict) else {}
    programme, specialisation = body.get("programme"), body.get("specialisation")
    for value in (programme, specialisation):
        if value is not None and not _text(value, 255):
            raise ServiceError(400, "Programme and specialisation must be non-empty text.")

    query = select(Application.id).where(Application.status == "PAID")
    if programme:
        query = query.where(Application.programme == programme.strip())
    if specialisation:
        query = query.where(Application.specialisation == specialisation.strip())
    eligible = db.session.execute(query).scalars().all()

    admin_id, paper_id, title = admin.id, str(paper.id), paper.title  # plain values: safe across a rollback
    now, inserted = datetime.utcnow(), 0
    try:
        for i in range(0, len(eligible), _INSERT_CHUNK):
            rows = [{"id": str(uuid.uuid4()), "application_id": app_id, "test_paper_id": paper_id,
                     "answers": {}, "assigned_at": now} for app_id in eligible[i:i + _INSERT_CHUNK]]
            result = db.session.execute(pg_insert(TestSubmission).values(rows).on_conflict_do_nothing(
                index_elements=["application_id", "test_paper_id"]))
            inserted += result.rowcount
    except Exception:
        db.session.rollback()
        raise
    # The rows are inserted but not committed yet; the audit entry (which needs the count) comes first.
    _commit_with_audit(admin_id, "TEST_ASSIGNED", {
        "paper_id": paper_id, "title": title, "assigned": inserted, "eligible": len(eligible),
        "programme": programme, "specialisation": specialisation})
    return {"assigned": inserted, "eligible": len(eligible), "already_assigned": len(eligible) - inserted}


def reset_attempt(paper_id: str, application_id: str, admin) -> dict:
    """Give one applicant another attempt: clears answers, score and the start/submit times."""
    paper = get_paper_or_404(paper_id)
    sub = None
    if admin_service.is_uuid(application_id):
        sub = TestSubmission.query.filter_by(test_paper_id=str(paper.id), application_id=application_id).first()
    if sub is None:
        raise ServiceError(404, "That applicant has not been assigned this test.")
    student = db.session.execute(
        select(Student).join(Application, Application.student_id == Student.id)
        .where(Application.id == application_id)).scalar_one()
    was = _status(sub)
    admin_id, student_id, student_email = admin.id, student.id, student.email
    details = {"paper_id": str(paper.id), "title": paper.title, "was": was}
    sub.answers, sub.score, sub.started_at, sub.submitted_at = {}, None, None, None
    _commit_with_audit(admin_id, "TEST_ATTEMPT_RESET", details, student_id, student_email)
    return {"reset": True, "status": "ASSIGNED"}


# -------------------------------------------------------------------- results
def _status(sub: TestSubmission) -> str:
    return "SUBMITTED" if sub.submitted_at else "IN_PROGRESS" if sub.started_at else "ASSIGNED"


def _passed(score, pass_marks: int) -> bool | None:
    return None if score is None else float(score) >= pass_marks


def results(paper_id: str, page: int) -> dict:
    """Paginated (20 per page) results for one paper, newest submissions first, plus a summary."""
    paper = get_paper_or_404(paper_id)
    base = (select(TestSubmission, Student, Application)
            .join(Application, Application.id == TestSubmission.application_id)
            .join(Student, Student.id == Application.student_id)
            .where(TestSubmission.test_paper_id == str(paper.id)))
    total = db.session.execute(select(func.count()).select_from(base.order_by(None).subquery())).scalar_one()
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(page, 1), total_pages)
    rows = db.session.execute(
        base.order_by(TestSubmission.submitted_at.desc().nulls_last(), Student.full_name, TestSubmission.id)
        .limit(PER_PAGE).offset((page - 1) * PER_PAGE)).all()

    items = [{"application_id": str(app.id), "student_id": str(st.id), "name": st.full_name, "email": st.email,
              "programme": app.programme, "specialisation": app.specialisation, "status": _status(sub),
              "score": float(sub.score) if sub.score is not None else None,
              "passed": _passed(sub.score, paper.pass_marks),
              "assigned_at": sub.assigned_at.isoformat(),
              "started_at": sub.started_at.isoformat() if sub.started_at else None,
              "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None}
             for sub, st, app in rows]

    s = db.session.execute(select(
        func.count(), func.count(TestSubmission.started_at), func.count(TestSubmission.submitted_at),
        func.count().filter(TestSubmission.score >= paper.pass_marks)
    ).where(TestSubmission.test_paper_id == str(paper.id))).one()
    return {"paper": {"id": str(paper.id), "title": paper.title, "total_marks": paper.total_marks,
                      "pass_marks": paper.pass_marks},
            "summary": {"assigned": s[0], "started": s[1], "submitted": s[2], "passed": s[3]},
            "results": items, "page": page, "per_page": PER_PAGE, "total": total, "total_pages": total_pages}
