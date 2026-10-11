import json
import logging
import urllib.parse
import urllib.request

from flask import current_app

log = logging.getLogger(__name__)

VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"


def verify_token(token: str | None, remote_ip: str | None = None) -> bool:
    """Verify a reCAPTCHA v2 token with Google. Fails closed on any error.

    With no RECAPTCHA_SECRET_KEY configured the check is skipped only in debug/testing,
    so a misconfigured production deploy rejects signups instead of silently allowing bots.
    """
    secret = current_app.config.get("RECAPTCHA_SECRET_KEY")
    if not secret:
        return bool(current_app.config.get("DEBUG") or current_app.config.get("TESTING"))
    if not token or not isinstance(token, str):
        return False

    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    request_ = urllib.request.Request(VERIFY_URL, data=urllib.parse.urlencode(payload).encode("utf-8"))
    try:
        with urllib.request.urlopen(request_, timeout=5) as response:
            return bool(json.load(response).get("success"))
    except Exception:  # network error, bad JSON, timeout — never let it become a pass
        log.exception("recaptcha verification failed")
        return False
