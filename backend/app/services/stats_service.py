"""Queries for the ERP statistics view (SRD FR-11). Routes in blueprints/admin_stats.py stay thin.

Contents: the seat matrix (read, validate, update), the summary cards, the per-programme table and
the daily registrations (counted by India-time day).
"""
import logging
import re
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import text

from app.extensions import db

log = logging.getLogger(__name__)

MAX_ROWS = 200
MAX_SEATS = 100000
MAX_NAME_LENGTH = 100  # programme_seats.programme / specialisation are VARCHAR(100)


class SeatValidationError(ValueError):
    """The seat payload is not valid. The message is safe to show to the admin."""


# ------------------------------------------------------------------------- seats
def get_seats() -> list[dict]:
    rows = db.session.execute(text(
        "SELECT programme, specialisation, seats FROM programme_seats "
        "ORDER BY programme, specialisation"
    )).all()
    return [{"programme": r.programme, "specialisation": r.specialisation, "seats": r.seats} for r in rows]


def validate_seats(body) -> list[dict]:
    """Return the cleaned rows from a PUT body, or raise SeatValidationError."""
    if not isinstance(body, dict) or not isinstance(body.get("seats"), list):
        raise SeatValidationError('Send a JSON body like {"seats": [{"programme", "specialisation", "seats"}]}.')
    items = body["seats"]
    if not items:
        raise SeatValidationError("Send at least one row.")
    if len(items) > MAX_ROWS:
        raise SeatValidationError(f"Send at most {MAX_ROWS} rows at a time.")

    cleaned, seen = [], set()
    for number, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise SeatValidationError(f"Row {number}: expected an object.")
        programme, specialisation, seats = item.get("programme"), item.get("specialisation"), item.get("seats")
        for label, value in (("programme", programme), ("specialisation", specialisation)):
            if not isinstance(value, str) or not value.strip():
                raise SeatValidationError(f"Row {number}: {label} is required.")
            if len(value.strip()) > MAX_NAME_LENGTH:
                raise SeatValidationError(f"Row {number}: {label} is too long (at most {MAX_NAME_LENGTH} characters).")
        if isinstance(seats, bool) or not isinstance(seats, int) or not 0 <= seats <= MAX_SEATS:
            raise SeatValidationError(f"Row {number}: seats must be a whole number from 0 to {MAX_SEATS}.")
        key = (programme.strip(), specialisation.strip())
        if key in seen:
            raise SeatValidationError(f"Row {number}: {key[0]} / {key[1]} appears more than once.")
        seen.add(key)
        cleaned.append({"programme": key[0], "specialisation": key[1], "seats": seats})
    return cleaned


def set_seats(rows: list[dict]) -> list[dict]:
    """Insert or update the given rows in one transaction; rows not sent are left alone.

    Returns the list of real changes (for the audit entry). The caller handles rollback on error.
    """
    before = {(r["programme"], r["specialisation"]): r["seats"] for r in get_seats()}
    changes = []
    for r in rows:
        old = before.get((r["programme"], r["specialisation"]))
        if old != r["seats"]:
            changes.append({"programme": r["programme"], "specialisation": r["specialisation"],
                            "from": old, "to": r["seats"]})
    db.session.execute(text(
        "INSERT INTO programme_seats (programme, specialisation, seats) "
        "VALUES (:programme, :specialisation, :seats) "
        "ON CONFLICT (programme, specialisation) DO UPDATE SET seats = EXCLUDED.seats"
    ), rows)
    db.session.commit()
    return changes


# ----------------------------------------------------------------------- summary
def get_summary() -> dict:
    """The four numbers on the statistics cards, from one query.

    registrations counts every student row. The other three count applications by status
    (each student has at most one application).
    """
    row = db.session.execute(text(
        "SELECT "
        "(SELECT count(*) FROM students) AS registrations, "
        "count(*) FILTER (WHERE status <> 'NOT_STARTED') AS applications_started, "
        "count(*) FILTER (WHERE status = 'PAID') AS paid, "
        "count(*) FILTER (WHERE status = 'PAYMENT_PENDING') AS payment_pending "
        "FROM applications"
    )).one()
    return {
        "registrations": int(row.registrations),
        "applications_started": int(row.applications_started),
        "paid": int(row.paid),
        "payment_pending": int(row.payment_pending),
    }


# -------------------------------------------------------------------- programmes
def get_programmes() -> list[dict]:
    """Per programme and specialisation: seats, applied, paid, shortlisted.

    Starts from the seat matrix (so empty programmes still show) and full-joins the application
    counts (so an application whose programme is not in the matrix still shows, with 0 seats).
    shortlisted = a PAID application with a scored test submission at or above the paper's pass marks.
    """
    rows = db.session.execute(text(
        "WITH per_app AS ("
        "  SELECT a.programme, a.specialisation, a.status,"
        "         EXISTS (SELECT 1 FROM test_submissions ts"
        "                 JOIN test_papers tp ON tp.id = ts.test_paper_id"
        "                 WHERE ts.application_id = a.id"
        "                   AND ts.score IS NOT NULL AND ts.score >= tp.pass_marks) AS qualified"
        "  FROM applications a"
        "  WHERE a.programme IS NOT NULL AND a.specialisation IS NOT NULL"
        "    AND a.status <> 'NOT_STARTED'"
        "), agg AS ("
        "  SELECT programme, specialisation,"
        "         count(*) AS applied,"
        "         count(*) FILTER (WHERE status = 'PAID') AS paid,"
        "         count(*) FILTER (WHERE status = 'PAID' AND qualified) AS shortlisted"
        "  FROM per_app GROUP BY programme, specialisation"
        ") "
        "SELECT COALESCE(s.programme, g.programme) AS programme,"
        "       COALESCE(s.specialisation, g.specialisation) AS specialisation,"
        "       COALESCE(s.seats, 0) AS seats,"
        "       COALESCE(g.applied, 0) AS applied,"
        "       COALESCE(g.paid, 0) AS paid,"
        "       COALESCE(g.shortlisted, 0) AS shortlisted "
        "FROM programme_seats s FULL OUTER JOIN agg g"
        "  ON g.programme = s.programme AND g.specialisation = s.specialisation "
        "ORDER BY 1, 2"
    )).all()
    return [{"programme": r.programme, "specialisation": r.specialisation, "seats": int(r.seats),
             "applied": int(r.applied), "paid": int(r.paid), "shortlisted": int(r.shortlisted)} for r in rows]


# ----------------------------------------------------------------- registrations
IST = timezone(timedelta(hours=5, minutes=30))  # India has no daylight saving; keep in sync with the SQL below
MAX_RANGE_DAYS = 366
DEFAULT_RANGE_DAYS = 30
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class RangeError(ValueError):
    """The ?from= / ?to= values are not usable. The message is safe to show to the admin."""


def _parse_day(value: str, label: str) -> date:
    if not _ISO_DATE.match(value):
        raise RangeError(f"'{label}' must be a date like 2026-10-01.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RangeError(f"'{label}' is not a real calendar date.") from None


def parse_range(from_raw, to_raw) -> tuple[date, date]:
    """Turn the query parameters into (start, end), both inclusive. Defaults: the last 30 days (India time)."""
    today = datetime.now(IST).date()  # days are India-time days (the schema stores naive UTC timestamps)
    end = _parse_day(to_raw, "to") if to_raw else today
    start = _parse_day(from_raw, "from") if from_raw else end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if start > end:
        raise RangeError("'from' must not be after 'to'.")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise RangeError(f"Choose a range of at most {MAX_RANGE_DAYS} days.")
    return start, end


def get_registrations(start: date, end: date) -> list[dict]:
    """One row per day from start to end inclusive; days with no sign-ups have count 0.

    The range is cast to timestamp on purpose: generate_series on plain dates would pick the
    timestamptz variant, and created_at is a naive (timestamp without time zone) UTC column.
    A day is an India-time day: it starts at 00:00 IST, which is 18:30 UTC the evening before.
    """
    rows = db.session.execute(text(
        "SELECT CAST(d AS date) AS day, count(s.id) AS count "
        "FROM generate_series(CAST(:start AS timestamp), CAST(:end AS timestamp), interval '1 day') AS d "
        "LEFT JOIN students s ON s.created_at >= d - interval '5 hours 30 minutes' "
        "AND s.created_at < d + interval '1 day' - interval '5 hours 30 minutes' "
        "GROUP BY d ORDER BY d"
    ), {"start": start, "end": end}).all()
    return [{"date": r.day.isoformat(), "count": int(r.count)} for r in rows]
