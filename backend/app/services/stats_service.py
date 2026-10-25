"""Queries for the ERP statistics view (SRD FR-11). Routes in blueprints/admin_stats.py stay thin.

Contents: the seat matrix (read, validate, update). The summary, programme and registration
queries are added below as they are built.
"""
import logging

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
