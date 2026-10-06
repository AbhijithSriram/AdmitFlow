from functools import wraps

from flask import current_app, g, jsonify, request

from app.services import admin_service


def admin_required(view_func):
    """Protects admin routes using the separate admin session cookie.

    401 -> no valid admin session.
    403 -> a student session cookie is present but there is no admin session
           (an authenticated non-admin; SRD NFR-1).
    On success the Admin row is available as `flask.g.admin`.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        cfg = current_app.config
        admin = admin_service.load_admin_from_token(request.cookies.get(cfg["ADMIN_SESSION_COOKIE_NAME"]))
        if admin is None:
            if request.cookies.get(cfg["SESSION_COOKIE_NAME"]):
                return jsonify({"success": False, "error": "You do not have permission to access this resource."}), 403
            return jsonify({"success": False, "error": "Please sign in to continue."}), 401
        g.admin = admin
        return view_func(*args, **kwargs)

    return wrapper
