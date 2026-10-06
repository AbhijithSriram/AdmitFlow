"""Logging setup with a redaction filter so secrets never reach the logs (SRD NFR-6)."""
import logging
import re

_SENSITIVE = re.compile(
    r"(?i)(password|passwd|otp|secret|api[_-]?key|token|authorization|cookie|signature)"
    r"(['\"]?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,&}]+)"
)


class RedactFilter(logging.Filter):
    """Masks values that follow sensitive keys: password=abc -> password=[REDACTED]."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _SENSITIVE.sub(r"\1\2[REDACTED]", record.getMessage())
        record.args = ()
        return True


def setup_logging(level: int = logging.INFO) -> None:
    """Install one stderr handler (with the redaction filter) on the root logger.

    Called before the Flask app is built so Flask sees a handler already exists and
    does not add its own unfiltered one.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
