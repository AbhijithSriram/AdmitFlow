"""Business logic for the admin portal (SRD FR-7). Routes in blueprints/admin.py stay thin.

Contents: credential check, server-side admin sessions, audit writer, applicant
list/detail queries, and the hard-delete flow.
"""
import hashlib
import logging
import math
import secrets
import uuid
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import and_, case, delete, exists, func, or_, select
from sqlalchemy.orm import Session

from app.extensions import bcrypt, db
from app.models import Admin, AdminSession, Application, AuditLog, FormDraft, OtpToken, Payment, Student
from app.models.test_submission import TestSubmission
from app.models.test_paper import TestPaper
from app.services import minio_service

log = logging.getLogger(__name__)

PER_PAGE = 20  # SRD NFR-3
STAGES = ("NOT_STARTED", "IN_PROGRESS", "PAYMENT_PENDING", "PAID")
PAYMENT_STATUSES = ("NONE", "PENDING", "PAID")
_TOUCH_AFTER = timedelta(seconds=60)  # don't rewrite last_seen_at on every single request

_dummy_hash: str | None = None


def _now() -> datetime:
    return datetime.utcnow()  # the schema uses naive UTC TIMESTAMPs everywhere


# --------------------------------------------------------------------------- auth
def authenticate(email: str, password: str) -> Admin | None:
    """Return the Admin if the credentials are valid, else None.

    For an unknown email we still run one bcrypt check against a dummy hash, so a
    missing account and a wrong password take about the same time.
    """
    global _dummy_hash
    admin = Admin.query.filter_by(email=email.strip().lower()).first()
    if admin is None:
        if _dummy_hash is None:
            _dummy_hash = bcrypt.generate_password_hash("not-a-real-password").decode()
        bcrypt.check_password_hash(_dummy_hash, password)
        return None
    return admin if bcrypt.check_password_hash(admin.password_hash, password) else None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _idle_timeout() -> timedelta:
    lifetime = current_app.config["PERMANENT_SESSION_LIFETIME"]
    return lifetime if isinstance(lifetime, timedelta) else timedelta(seconds=int(lifetime))


def create_session(admin: Admin) -> str:
    """Create a server-side session row and return the raw cookie token."""
    token = secrets.token_urlsafe(32)
    db.session.add(AdminSession(token_hash=_hash_token(token), admin_id=admin.id))
    db.session.commit()
    return token


def load_admin_from_token(token: str | None) -> Admin | None:
    """Return the Admin for a valid, non-idle session, sliding the idle window; else None."""
    if not token:
        return None
    sess = db.session.get(AdminSession, _hash_token(token))
    if sess is None:
        return None
    now = _now()
    if sess.last_seen_at + _idle_timeout() < now:
        db.session.delete(sess)
        db.session.commit()
        return None
    admin = db.session.get(Admin, sess.admin_id)
    if admin is None:
        return None
    if now - sess.last_seen_at > _TOUCH_AFTER:
        sess.last_seen_at = now
        db.session.commit()
    return admin


def destroy_session(token: str | None) -> None:
    """Invalidate a session immediately (logout)."""
    if not token:
        return
    sess = db.session.get(AdminSession, _hash_token(token))
    if sess:
        db.session.delete(sess)
        db.session.commit()


# ------------------------------------------------------------------------- audit
def write_audit(admin_id: str, action_type: str, target_student_id: str | None = None,
                target_email: str | None = None, details: dict | None = None) -> str:
    """Append an audit_log row in its OWN transaction and commit immediately.

    A separate session means the entry is durable even if the caller's transaction
    (e.g. the hard-delete) fails and rolls back (SRD NFR-2).

    Args:
        admin_id: id of the acting admin.
        action_type: short code such as "HARD_DELETE_STUDENT".
        target_student_id / target_email: what was acted on. The email is stored
            redundantly so the row stays meaningful once the student is gone.
        details: JSON-serialisable dict. Never put secrets or OTPs in here.
    Returns:
        The id of the new audit row.
    """
    with Session(db.engine) as s:
        row = AuditLog(admin_id=admin_id, action_type=action_type,
                       target_student_id=target_student_id, target_email=target_email, details=details)
        s.add(row)
        s.commit()
        log.info("audit action=%s admin=%s target=%s", action_type, admin_id, target_student_id)
        return row.id


# -------------------------------------------------------------------- list/search
def _payment_status_expr():
    paid = exists().where(and_(Payment.application_id == Application.id, Payment.status == "SUCCESS"))
    attempted = exists().where(Payment.application_id == Application.id)
    return case((paid, "PAID"), (attempted, "PENDING"), else_="NONE")


def _like_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


SORTS = ("name", "email", "registered_at", "stage")


def parse_applicant_filters(args) -> tuple[dict | None, str | None]:
    """Validate the applicant filters from a request's query string (shared by the applicant list
    and the export, so both accept exactly the same parameters).

    Args:
        args: the request's query arguments (sort, order, q, stage, payment_status).
    Returns:
        (filters, None) where filters has the keys sort, order, q, stage, payment_status;
        or (None, a human-readable error message) if a value is not allowed.
    """
    sort, order = args.get("sort", "registered_at"), args.get("order", "desc")
    stage, payment_status = args.get("stage", ""), args.get("payment_status", "")
    if sort not in SORTS or order not in ("asc", "desc"):
        return None, "Invalid sort option."
    if stage and stage not in STAGES:
        return None, "Invalid stage filter."
    if payment_status and payment_status not in PAYMENT_STATUSES:
        return None, "Invalid payment status filter."
    return {"sort": sort, "order": order, "q": args.get("q", "").strip()[:100],
            "stage": stage, "payment_status": payment_status}, None


def applicant_query(sort: str, order: str, q: str, stage: str, payment_status: str):
    """The filtered, sorted applicant query behind both the admin list and the export.

    Students who have not started an application have no applications row, so their
    stage is reported as NOT_STARTED. Payment status is derived from the payments
    table: PAID if any attempt succeeded, PENDING if attempts exist but none succeeded,
    NONE otherwise.

    Returns:
        A SQLAlchemy select (not yet executed) with one row per student.
    """
    stage_expr = func.coalesce(Application.status, "NOT_STARTED")
    pay_expr = _payment_status_expr()
    # Aptitude score shown per applicant: the score of their most recently SUBMITTED test, else NULL.
    # (An applicant normally has one test; this rule keeps the column to a single number.)
    score_expr = (select(TestSubmission.score)
                  .where(TestSubmission.application_id == Application.id, TestSubmission.submitted_at.is_not(None))
                  .order_by(TestSubmission.submitted_at.desc()).limit(1).scalar_subquery())

    query = (
        select(Student.id, Student.full_name, Student.email, Student.phone, Student.created_at,
               Student.date_of_birth, Student.gender, Application.programme, Application.specialisation,
               stage_expr.label("stage"), pay_expr.label("payment_status"),
               score_expr.label("aptitude_score"))
        .select_from(Student)
        .outerjoin(Application, Application.student_id == Student.id)
    )
    if q:
        pattern = f"%{_like_escape(q)}%"
        query = query.where(or_(Student.full_name.ilike(pattern, escape="\\"),
                                Student.email.ilike(pattern, escape="\\"),
                                Student.phone.ilike(pattern, escape="\\")))
    if stage:
        query = query.where(stage_expr == stage)
    if payment_status:
        query = query.where(pay_expr == payment_status)

    sort_columns = {"name": Student.full_name, "email": Student.email,
                    "registered_at": Student.created_at, "stage": stage_expr}
    col = sort_columns[sort]
    return query.order_by(col.asc() if order == "asc" else col.desc(), Student.id)


def list_students(page: int, sort: str, order: str, q: str, stage: str, payment_status: str) -> dict:
    """Paginated applicant list (20 per page) with search, filters and sorting (see applicant_query)."""
    query = applicant_query(sort, order, q, stage, payment_status)

    total = db.session.execute(select(func.count()).select_from(query.order_by(None).subquery())).scalar_one()
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = min(max(page, 1), total_pages)
    rows = db.session.execute(query.limit(PER_PAGE).offset((page - 1) * PER_PAGE)).all()

    return {
        "students": [{"id": r.id, "name": r.full_name, "email": r.email, "phone": r.phone,
                      "registered_at": r.created_at.isoformat(), "stage": r.stage,
                      "payment_status": r.payment_status,
                      "aptitude_score": float(r.aptitude_score) if r.aptitude_score is not None else None}
                     for r in rows],
        "page": page, "per_page": PER_PAGE, "total": total, "total_pages": total_pages,
    }


# ------------------------------------------------------------------------- detail
_DOC_FIELDS = (("photo", "photo_url"), ("signature", "signature_url"),
               ("id_proof", "id_proof_url"), ("application_pdf", "pdf_url"))


def _document(object_name: str | None) -> dict:
    """Describe one stored file. The URL is a 15-minute presigned link, never a raw MinIO URL."""
    if not object_name:
        return {"present": False, "url": None}
    try:
        return {"present": True, "url": minio_service.get_presigned_url(object_name)}
    except Exception:  # MinIO briefly down must not break the whole detail page
        log.exception("could not presign document for %s", object_name)
        return {"present": True, "url": None, "error": "File storage is unavailable right now."}


def aptitude_for_application(application_id: str) -> list[dict]:
    """Every aptitude test assigned to an application, with status and score (admin view only)."""
    rows = db.session.execute(
        select(TestSubmission, TestPaper).join(TestPaper, TestPaper.id == TestSubmission.test_paper_id)
        .where(TestSubmission.application_id == application_id).order_by(TestSubmission.assigned_at)).all()
    out = []
    for sub, paper in rows:
        status = "SUBMITTED" if sub.submitted_at else "IN_PROGRESS" if sub.started_at else "ASSIGNED"
        score = float(sub.score) if sub.score is not None else None
        out.append({"paper_id": str(paper.id), "title": paper.title, "status": status, "score": score,
                    "total_marks": paper.total_marks, "pass_marks": paper.pass_marks,
                    "passed": None if score is None else score >= paper.pass_marks,
                    "assigned_at": sub.assigned_at.isoformat(),
                    "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None})
    return out


def get_student_detail(student_id: str) -> dict | None:
    """Full applicant record for the admin detail view, or None if not found."""
    student = db.session.get(Student, student_id)
    if student is None:
        return None
    app_row = Application.query.filter_by(student_id=student.id).first()

    application = None
    steps: dict = {}
    payments: list = []
    if app_row is not None:
        application = {
            "id": app_row.id, "status": app_row.status, "programme": app_row.programme,
            "specialisation": app_row.specialisation,
            "guidelines_accepted_at": app_row.guidelines_accepted_at.isoformat() if app_row.guidelines_accepted_at else None,
            "created_at": app_row.created_at.isoformat(), "updated_at": app_row.updated_at.isoformat(),
            "documents": {name: _document(getattr(app_row, col)) for name, col in _DOC_FIELDS},
        }
        for d in FormDraft.query.filter_by(application_id=app_row.id).order_by(FormDraft.step_number):
            steps[str(d.step_number)] = d.data
        for p in Payment.query.filter_by(application_id=app_row.id).order_by(Payment.created_at):
            # razorpay_signature is deliberately not exposed
            payments.append({"id": p.id, "status": p.status, "amount": str(p.amount),
                             "razorpay_order_id": p.razorpay_order_id,
                             "razorpay_payment_id": p.razorpay_payment_id,
                             "created_at": p.created_at.isoformat()})
    return {
        "aptitude": aptitude_for_application(app_row.id) if app_row is not None else [],
        "student": {"id": student.id, "full_name": student.full_name,
                    "date_of_birth": student.date_of_birth.isoformat(), "gender": student.gender,
                    "email": student.email, "phone": student.phone, "email_verified": student.email_verified,
                    "created_at": student.created_at.isoformat()},
        "application": application, "steps": steps, "payments": payments,
    }


# ------------------------------------------------------------------- hard delete
class DeleteAborted(Exception):
    """Raised when file cleanup fails; nothing was deleted from the database."""


def _count(model, *conds) -> int:
    return db.session.execute(select(func.count()).select_from(model).where(*conds)).scalar_one()


def _delete_student_row(student_id: str) -> None:
    """One DELETE on students; PostgreSQL's ON DELETE CASCADE removes every child row."""
    db.session.execute(delete(Student).where(Student.id == student_id))
    db.session.commit()


def hard_delete_student(student_id: str, admin: Admin) -> dict | None:
    """Permanently delete a student and everything attached to them (SRD FR-7.3).

    Order (SRD §6.2 / NFR-2):
      1. delete the applicant's MinIO files (abort, with nothing deleted, if any fail);
      2. write the audit entry in its own committed transaction;
      3. run one DELETE on students, letting the database cascade.

    Returns a structured summary, or None if the student does not exist.
    Raises DeleteAborted if file cleanup failed, or re-raises the DB error if step 3 failed
    (the audit entry from step 2 is kept either way, plus a *_FAILED entry).
    """
    student = db.session.get(Student, student_id)
    if student is None:
        return None
    email = student.email
    app_row = Application.query.filter_by(student_id=student_id).first()

    object_names = [getattr(app_row, col) for _, col in _DOC_FIELDS if app_row and getattr(app_row, col)]
    removed, failed = [], []
    for name in object_names:
        try:
            minio_service.delete_object(name)
            removed.append(name)
        except Exception:
            log.exception("MinIO delete failed for %s", name)
            failed.append(name)
    if failed:
        write_audit(admin.id, "HARD_DELETE_ABORTED", student_id, email,
                    {"reason": "file cleanup failed", "files_removed": removed, "files_failed": failed})
        raise DeleteAborted(f"{len(failed)} file(s) could not be removed")

    cascaded = {
        "otp_tokens": _count(OtpToken, OtpToken.student_id == student_id),
        "applications": 1 if app_row else 0,
        "form_drafts": _count(FormDraft, FormDraft.application_id == app_row.id) if app_row else 0,
        "payments": _count(Payment, Payment.application_id == app_row.id) if app_row else 0,
        "test_submissions": _count(TestSubmission, TestSubmission.application_id == app_row.id) if app_row else 0,
    }

    write_audit(admin.id, "HARD_DELETE_STUDENT", student_id, email,
                {"files_removed": removed, "rows_cascaded": cascaded})
    try:
        _delete_student_row(student_id)
    except Exception:
        db.session.rollback()
        write_audit(admin.id, "HARD_DELETE_STUDENT_FAILED", student_id, email, {"files_removed": removed})
        raise

    log.info("hard delete complete student=%s by admin=%s", student_id, admin.id)
    return {"student_id": student_id, "email": email, "files_removed": removed, "cascaded": cascaded}


def is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False
