import logging

from flask import Blueprint, current_app, g, jsonify, request

from app.extensions import limiter
from app.middleware.admin_guard import admin_required
from app.services import admin_service

log = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


def _ok(data=None, status=200):
    return jsonify({"success": True, "data": data if data is not None else {}}), status


def _fail(message, status=400):
    return jsonify({"success": False, "error": message}), status


@admin_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def admin_login():
    """Authenticate an admin account (no registration flow; seeded accounts only)."""
    body = request.get_json(silent=True) or {}
    email, password = body.get("email"), body.get("password")
    if not isinstance(email, str) or not isinstance(password, str) or not email or not password:
        return _fail("Enter your email and password.", 400)

    admin = admin_service.authenticate(email, password)
    if admin is None:
        log.warning("admin login failed")
        return _fail("Incorrect email or password.", 401)

    token = admin_service.create_session(admin)
    log.info("admin login ok admin_id=%s", admin.id)
    resp, status = _ok({"admin": {"id": admin.id, "name": admin.name, "email": admin.email}})
    cfg = current_app.config
    resp.set_cookie(cfg["ADMIN_SESSION_COOKIE_NAME"], token, httponly=True, samesite="Strict",
                    secure=bool(cfg.get("SESSION_COOKIE_SECURE")), path="/api/admin")
    return resp, status


@admin_bp.route("/logout", methods=["POST"])
@admin_required
def admin_logout():
    """Invalidate the current admin session immediately (server-side)."""
    cfg = current_app.config
    admin_service.destroy_session(request.cookies.get(cfg["ADMIN_SESSION_COOKIE_NAME"]))
    resp, status = _ok({"message": "Signed out."})
    resp.delete_cookie(cfg["ADMIN_SESSION_COOKIE_NAME"], path="/api/admin")
    return resp, status


@admin_bp.route("/me", methods=["GET"])
@admin_required
def admin_me():
    """Lets the React app restore the admin session after a page refresh."""
    a = g.admin
    return _ok({"admin": {"id": a.id, "name": a.name, "email": a.email}})


@admin_bp.route("/students", methods=["GET"])
@admin_required
def list_students():
    """Paginated (20/page), sortable, searchable list of all applicants.

    Query params: page, sort (name|email|registered_at|stage), order (asc|desc),
    q (search name/email/phone), stage, payment_status.
    """
    filters, problem = admin_service.parse_applicant_filters(request.args)
    if problem:
        return _fail(problem, 400)
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        return _fail("Invalid page number.", 400)

    return _ok(admin_service.list_students(page, **filters))


@admin_bp.route("/students/<student_id>", methods=["GET"])
@admin_required
def get_student(student_id):
    """Full application detail for one student (documents as 15-minute presigned URLs)."""
    detail = admin_service.get_student_detail(student_id) if admin_service.is_uuid(student_id) else None
    if detail is None:
        return _fail("Applicant not found.", 404)
    return _ok(detail)


@admin_bp.route("/students/<student_id>", methods=["DELETE"])
@admin_required
def delete_student(student_id):
    """Hard delete: MinIO cleanup, audit entry, then cascading DB delete (SRD FR-7.3)."""
    body = request.get_json(silent=True) or {}
    if body.get("confirmation") != "DELETE":
        return _fail('Type "DELETE" to confirm.', 400)
    if not admin_service.is_uuid(student_id):
        return _fail("Applicant not found.", 404)

    try:
        result = admin_service.hard_delete_student(student_id, g.admin)
    except admin_service.DeleteAborted:
        return _fail("Some files could not be removed, so nothing was deleted. Try again in a moment.", 502)
    except Exception:
        log.exception("hard delete failed student=%s", student_id)
        return _fail("The delete failed. The attempt has been recorded in the audit log.", 500)
    if result is None:
        return _fail("Applicant not found.", 404)
    return _ok(result)
