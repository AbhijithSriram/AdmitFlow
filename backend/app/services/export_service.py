"""Applicant data export for offline processing (SRD FR-11), as CSV or PDF.

The rows come from admin_service.applicant_query, so an export always matches what the admin's
applicant table shows for the same filters. Exports carry personal data: the route writes an
audit_log entry for every one (see blueprints/admin_export.py).
"""
import csv
import io
from datetime import datetime

from app.extensions import db
from app.services import admin_service, pdf_service

# A sanity cap, far above any one college's applicant count: an export is generated in one request.
MAX_ROWS = 10_000

HEADERS = ["Name", "Email", "Phone", "Date of birth", "Gender", "Registered on",
           "Stage", "Payment", "Programme", "Specialisation", "Aptitude score"]

_STAGE_LABELS = {"NOT_STARTED": "Not started", "IN_PROGRESS": "In progress",
                 "PAYMENT_PENDING": "Payment pending", "PAID": "Submitted & paid"}
_PAYMENT_LABELS = {"NONE": "No attempt", "PENDING": "Attempted, not paid", "PAID": "Paid"}

# A spreadsheet treats a cell starting with one of these as a formula. Applicants type their own
# names, so "=HYPERLINK(...)" or "@SUM(...)" would otherwise run when an admin opens the file.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


class TooManyRows(Exception):
    """The filters match more than MAX_ROWS applicants."""


def fetch_rows(filters: dict) -> list[list[str]]:
    """The filtered applicants as rows of display strings, in HEADERS order.

    Args:
        filters: as returned by admin_service.parse_applicant_filters.
    Raises:
        TooManyRows: if more than MAX_ROWS applicants match (the caller asks for narrower filters).
    """
    query = admin_service.applicant_query(**filters).limit(MAX_ROWS + 1)
    rows = db.session.execute(query).all()
    if len(rows) > MAX_ROWS:
        raise TooManyRows()
    return [[
        r.full_name or "",
        r.email or "",
        r.phone or "",
        r.date_of_birth.isoformat() if r.date_of_birth else "",
        r.gender or "",
        r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        _STAGE_LABELS.get(r.stage, r.stage),
        _PAYMENT_LABELS.get(r.payment_status, r.payment_status),
        r.programme or "",
        r.specialisation or "",
        _score(r.aptitude_score),
    ] for r in rows]


def _score(value) -> str:
    """The applicant's latest submitted aptitude score (admin_service.applicant_query), as '7' or '7.5';
    empty when no test has been submitted."""
    if value is None:
        return ""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def safe_cell(value: str) -> str:
    """Neutralise spreadsheet formula injection: a leading apostrophe makes the cell plain text."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_START) else text


def to_csv(rows: list[list[str]]) -> bytes:
    """CSV bytes with a header row. UTF-8 with a byte-order mark, so Excel shows non-English names
    (Tamil, Hindi, ...) correctly instead of garbled characters."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(HEADERS)
    for row in rows:
        writer.writerow([safe_cell(cell) for cell in row])
    return buf.getvalue().encode("utf-8-sig")


def to_pdf(rows: list[list[str]], filters: dict, institution_name: str = "AdmitFlow Institute") -> bytes:
    """A landscape PDF table of the same rows (values are escaped by pdf_service)."""
    return pdf_service.render_applicants_pdf({
        "institution_name": institution_name,
        "generated_at": datetime.utcnow().strftime("%d %b %Y, %H:%M UTC"),
        "filters": describe_filters(filters),
        "headers": HEADERS,
        "rows": rows,
    })


def describe_filters(filters: dict) -> str:
    """Human-readable summary, printed on the PDF and stored in the audit entry."""
    parts = []
    if filters.get("q"):
        parts.append(f'search "{filters["q"]}"')
    if filters.get("stage"):
        parts.append(f"stage {_STAGE_LABELS.get(filters['stage'], filters['stage'])}")
    if filters.get("payment_status"):
        parts.append(f"payment {_PAYMENT_LABELS.get(filters['payment_status'], filters['payment_status'])}")
    parts.append(f"sorted by {filters.get('sort', 'registered_at').replace('_', ' ')} ({filters.get('order', 'desc')})")
    return ", ".join(parts) if len(parts) > 1 else "all applicants, " + parts[0]


def filename(extension: str) -> str:
    return f"admitflow-applicants-{datetime.utcnow().strftime('%Y%m%d-%H%M')}.{extension}"
