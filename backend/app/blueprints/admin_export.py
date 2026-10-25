"""Applicant data export, CSV and PDF (SRD FR-11). Owner: Person 3.

Registered at /api/admin/export. Takes the same filter parameters as GET /api/admin/students.
Exports contain personal data, so every export writes an audit_log row before any data is sent,
and CSV cells that start with = + - or @ are neutralised (formula injection).
"""
import logging

from flask import Blueprint, Response, g, jsonify, request

from app.extensions import limiter
from app.middleware.admin_guard import admin_required
from app.services import admin_service, export_service

log = logging.getLogger(__name__)
admin_export_bp = Blueprint("admin_export", __name__)

_MIMETYPES = {"csv": "text/csv; charset=utf-8", "pdf": "application/pdf"}


def _fail(message, status=400):
    return jsonify({"success": False, "error": message}), status


def _export(fmt: str):
    filters, problem = admin_service.parse_applicant_filters(request.args)
    if problem:
        return _fail(problem)

    try:
        rows = export_service.fetch_rows(filters)
    except export_service.TooManyRows:
        return _fail(f"More than {export_service.MAX_ROWS:,} applicants match. Narrow the filters and try again.")

    # Recorded before the file is produced: if the audit entry cannot be written, nothing is exported.
    try:
        admin_service.write_audit(g.admin.id, "EXPORT_APPLICANTS", details={
            "format": fmt, "rows": len(rows), "filters": filters,
            "description": export_service.describe_filters(filters),
        })
    except Exception:
        log.exception("export refused: audit entry could not be written admin=%s", g.admin.id)
        return _fail("The export could not be recorded, so it was not produced. Please try again.", 500)

    try:
        if fmt == "csv":
            body = export_service.to_csv(rows)
        else:
            body = export_service.to_pdf(rows, filters)
    except Exception:
        log.exception("export failed format=%s admin=%s", fmt, g.admin.id)
        return _fail("The export could not be generated. Please try again.", 500)

    log.info("export format=%s rows=%s admin=%s", fmt, len(rows), g.admin.id)
    resp = Response(body, mimetype=_MIMETYPES[fmt])
    resp.headers["Content-Disposition"] = f'attachment; filename="{export_service.filename(fmt)}"'
    resp.headers["Cache-Control"] = "no-store"  # personal data: no copies in browser or proxy caches
    # Lets the page read the file name when the API is on another origin (the dev setup);
    # harmless in production, where Nginx serves both from one origin.
    resp.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    return resp


@admin_export_bp.route("/applicants.csv", methods=["GET"])
@admin_required
@limiter.limit("10 per minute")
def export_csv():
    """Filtered applicants as a CSV download."""
    return _export("csv")


@admin_export_bp.route("/applicants.pdf", methods=["GET"])
@admin_required
@limiter.limit("10 per minute")
def export_pdf():
    """Filtered applicants as a PDF table (WeasyPrint)."""
    return _export("pdf")
