"""Editable site content (v1.1 FR-12): the public read the website loads at start-up, the brochure
generated from it, and the admin routes that edit it. Logic in services/content_service.py.

  GET    /api/content                       public: all sections + demo_mode
  GET    /api/content/brochure              public: the information brochure as a PDF, from the content
  GET    /api/admin/content                 admin: content + when/by whom each section was last changed
  PUT    /api/admin/content/<section>       admin: replace one section (body: {"value": ...})
  DELETE /api/admin/content/<section>       admin: back to the default for that section
"""
from flask import Blueprint, Response, g, jsonify, request

from app.extensions import limiter
from app.middleware.admin_guard import admin_required
from app.services import content_service, pdf_service

content_bp = Blueprint("content", __name__)
admin_content_bp = Blueprint("admin_content", __name__)


def _ok(data):
    return jsonify({"success": True, "data": data}), 200


def _fail(message, status=400):
    return jsonify({"success": False, "error": message}), status


@content_bp.route("/content", methods=["GET"])
def public_content():
    """Everything the public pages and the application form show."""
    resp, status = _ok(content_service.public_content())
    # Short-lived: an admin's change should reach visitors within a minute, through Cloudflare too.
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp, status


@content_bp.route("/content/brochure", methods=["GET"])
@limiter.limit("20 per minute")
def brochure():
    """The information brochure, generated from the current content so it can never be out of date."""
    pdf = pdf_service.render_brochure_pdf(content_service.get_content(), content_service.fee_inr(),
                                          content_service.demo_footer())
    resp = Response(pdf, mimetype="application/pdf")
    resp.headers["Content-Disposition"] = 'inline; filename="brochure.pdf"'
    # Generated on request: never let a cache (Cloudflare caches .pdf files by default) keep an old one.
    resp.headers["Cache-Control"] = "no-store"
    return resp


@admin_content_bp.route("/content", methods=["GET"])
@admin_required
def admin_get_content():
    return _ok(content_service.admin_content())


@admin_content_bp.route("/content/<section>", methods=["PUT"])
@admin_required
def admin_save_section(section):
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or "value" not in body:
        return _fail('Send the new value as {"value": ...}.')
    try:
        return _ok(content_service.save_section(section, body["value"], g.admin))
    except content_service.ContentError as e:
        return _fail(e.message, e.status)


@admin_content_bp.route("/content/<section>", methods=["DELETE"])
@admin_required
def admin_reset_section(section):
    try:
        return _ok(content_service.reset_section(section, g.admin))
    except content_service.ContentError as e:
        return _fail(e.message, e.status)
