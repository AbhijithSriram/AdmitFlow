from functools import wraps

from flask import jsonify, session


def admin_required(view_func):
    """Rejects requests with no valid admin session (401) or a non-admin session (403)."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return jsonify({"success": False, "error": "Not authenticated"}), 401
        if not session.get("is_admin"):
            return jsonify({"success": False, "error": "Not authorised"}), 403
        return view_func(*args, **kwargs)

    return wrapper
