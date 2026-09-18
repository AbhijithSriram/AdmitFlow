from functools import wraps

from flask import jsonify, session


def login_required(view_func):
    """Rejects requests with no valid student session (401)."""

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("student_id"):
            return jsonify({"success": False, "error": "Not authenticated"}), 401
        return view_func(*args, **kwargs)

    return wrapper
