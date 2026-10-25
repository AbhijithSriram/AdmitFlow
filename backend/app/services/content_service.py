"""Site content an admin can edit from the portal, so one deployment can be set up for any college
without touching code (SRD 1.4: "configured for any college"; v1.1 FR-12).

The content is split into SECTIONS. Each section is stored as one row in site_settings (migration
007); a section without a row falls back to backend/app/content_defaults.json. Every save is
validated, written to the audit log first, and then committed. Routes live in blueprints/content.py.

Whether the site shows the academic-project disclaimer is NOT content: it is a per-deployment server
setting (DEMO_MODE), so an admin cannot switch it off on the public demo.
"""
import copy
import json
import logging
import pathlib
import re
from datetime import datetime

from flask import current_app
from sqlalchemy import text

from app.extensions import db
from app.models import SiteSetting
from app.services import admin_service, field_rules

log = logging.getLogger(__name__)

DEFAULTS_FILE = pathlib.Path(__file__).resolve().parents[1] / "content_defaults.json"
SECTIONS = ("institution", "contact", "dates", "guidelines", "eligibility", "documents", "fee",
            "suggestions", "programmes")
LEVELS = ("UG", "PG")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_defaults_cache: dict | None = None


class ContentError(Exception):
    """A value an admin sent is not acceptable. The message says what to fix; status is the HTTP code."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# ----------------------------------------------------------------------------- read side
def defaults() -> dict:
    global _defaults_cache
    if _defaults_cache is None:
        _defaults_cache = json.loads(DEFAULTS_FILE.read_text(encoding="utf-8"))
    return copy.deepcopy(_defaults_cache)


def get_content() -> dict:
    """Every section: the saved value where an admin has edited it, the default otherwise."""
    content = defaults()
    for row in SiteSetting.query.filter(SiteSetting.key.in_(SECTIONS)).all():
        content[row.key] = row.value
    return content


def public_content() -> dict:
    """What the website loads at start-up: all the content, plus whether to show the demo notice."""
    return {**get_content(), "demo_mode": demo_mode()}


def admin_content() -> dict:
    """The content plus, per section, when it was last changed and by whom (None = still the default)."""
    rows = {r.key: r for r in SiteSetting.query.filter(SiteSetting.key.in_(SECTIONS)).all()}
    meta = {}
    for key in SECTIONS:
        row = rows.get(key)
        meta[key] = None if row is None else {"updated_at": row.updated_at.isoformat(), "updated_by": row.updated_by}
    return {"content": public_content(), "meta": meta}


def fee_inr() -> int:
    return int(get_content()["fee"]["amount_inr"])


def fee_paise() -> int:
    return fee_inr() * 100


def institution_name() -> str:
    return get_content()["institution"]["name"]


def programme_choices() -> dict[str, dict]:
    """{programme name: {"level": "UG"|"PG", "specialisations": set()}} for validating Step 3."""
    return {p["name"]: {"level": p["level"], "specialisations": set(p["specialisations"])}
            for p in get_content()["programmes"]}


def demo_mode() -> bool:
    return bool(current_app.config.get("DEMO_MODE", True))


def demo_footer() -> str:
    """The disclaimer printed on PDFs while DEMO_MODE is on; empty for a real deployment."""
    if not demo_mode():
        return ""
    return (f"AdmitFlow is an academic project: {institution_name()} is fictional. "
            "This document is not issued by any real college and is not an offer of admission.")


def fill(value: str) -> str:
    """Replace the {fee} placeholder an admin may use in guidelines and other text."""
    return value.replace("{fee}", f"₹{fee_inr():,}")


# ----------------------------------------------------------------------------- validation
def _text(value, label: str, max_len: int, required: bool = True):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ContentError(f"{label} is required.")
        return None
    if not isinstance(value, str):
        raise ContentError(f"{label} must be text.")
    value = value.strip()
    if len(value) > max_len:
        raise ContentError(f"{label} can be at most {max_len} characters.")
    return value


def _list(value, label: str, item_label: str, max_items: int, max_len: int, min_items: int = 0) -> list[str]:
    if not isinstance(value, list):
        raise ContentError(f"{label} must be a list.")
    items = [_text(v, f"{item_label} {n}", max_len) for n, v in enumerate(value, start=1)]
    if len(items) < min_items:
        raise ContentError(f"{label} needs at least {min_items} item{'s' if min_items != 1 else ''}.")
    if len(items) > max_items:
        raise ContentError(f"{label} can have at most {max_items} items.")
    return items


def _object(value, label: str) -> dict:
    if not isinstance(value, dict):
        raise ContentError(f"{label} must be an object.")
    return value


def _unique(items: list[str], label: str) -> None:
    seen = set()
    for item in items:
        key = item.casefold()
        if key in seen:
            raise ContentError(f"{label} \"{item}\" appears more than once.")
        seen.add(key)


def validate(section: str, value):
    """The cleaned value for a section, or ContentError explaining the first problem."""
    if section == "institution":
        v = _object(value, "Institution")
        return {"name": _text(v.get("name"), "Institution name", 120),
                "about": _list(v.get("about", []), "About", "Paragraph", 10, 1500)}
    if section == "contact":
        v = _object(value, "Contact")
        email = _text(v.get("email"), "Email", 255, required=False)
        if email and not _EMAIL.match(email):
            raise ContentError("Enter a valid contact email address.")
        return {"email": email, "phone": _text(v.get("phone"), "Phone", 40, required=False),
                "address": _text(v.get("address"), "Address", 300, required=False),
                "hours": _text(v.get("hours"), "Office hours", 120, required=False),
                "note": _text(v.get("note"), "Note", 1000, required=False)}
    if section == "dates":
        v = _object(value, "Dates")
        items = v.get("items")
        if not isinstance(items, list) or not 1 <= len(items) <= 15:
            raise ContentError("Add between 1 and 15 dates.")
        cleaned = []
        for n, item in enumerate(items, start=1):
            item = _object(item, f"Date {n}")
            cleaned.append({"label": _text(item.get("label"), f"Date {n}: what happens", 80),
                            "value": _text(item.get("value"), f"Date {n}: when", 120)})
        return {"items": cleaned, "note": _text(v.get("note"), "Note under the dates", 300, required=False)}
    if section == "guidelines":
        return _list(value, "Guidelines", "Guideline", 40, 1000, min_items=1)
    if section == "eligibility":
        return _list(value, "Eligibility", "Rule", 40, 1000, min_items=1)
    if section == "documents":
        return _list(value, "Documents", "Document", 40, 300)
    if section == "fee":
        amount = _object(value, "Fee").get("amount_inr")
        if isinstance(amount, bool) or not isinstance(amount, int) or not 1 <= amount <= 100000:
            raise ContentError("The application fee must be a whole number of rupees from 1 to 1,00,000.")
        return {"amount_inr": amount}
    if section == "suggestions":
        v = _object(value, "Suggestions")
        out = {}
        for key, label in (("colleges", "College"), ("universities", "University")):
            items = _list(v.get(key, []), f"{label} suggestions", label, 300, 150)
            for item in items:
                # Step 4 drops characters its College/University boxes do not accept as they are typed,
                # so a suggestion with such a character would be altered when picked.
                if not field_rules.is_valid_text("org", item):
                    raise ContentError(f"{label} \"{item}\" can contain letters, numbers, spaces and . , & ' ( ) / - only.")
            _unique(items, label)
            out[key] = items
        return out
    if section == "programmes":
        return _validate_programmes(value)
    raise ContentError("Unknown section.", 404)


def _validate_programmes(value) -> list[dict]:
    if not isinstance(value, list) or not 1 <= len(value) <= 30:
        raise ContentError("Add between 1 and 30 programmes.")
    cleaned = []
    for n, p in enumerate(value, start=1):
        p = _object(p, f"Programme {n}")
        name = _text(p.get("name"), f"Programme {n}: name", 60)
        if p.get("level") not in LEVELS:
            raise ContentError(f"{name}: choose UG (Class XII and X are asked) or PG (the UG degree is asked too).")
        specs = _list(p.get("specialisations"), f"{name}: specialisations", "Specialisation", 30, 80, min_items=1)
        _unique(specs, f"{name}: specialisation")
        cleaned.append({"name": name, "level": p["level"], "specialisations": specs})
    _unique([p["name"] for p in cleaned], "Programme")
    return cleaned


def _check_programmes_against_applications(new: list[dict]) -> None:
    """Applications store the programme and specialisation by name, so a pair that applications use
    cannot be removed or renamed, and such a programme cannot switch between UG and PG (its academic
    answers were collected for the other kind)."""
    in_use = db.session.execute(text(
        "SELECT programme, specialisation, count(*) AS n FROM applications "
        "WHERE programme IS NOT NULL AND specialisation IS NOT NULL GROUP BY programme, specialisation"
    )).all()
    offered = {(p["name"], s) for p in new for s in p["specialisations"]}
    levels = {p["name"]: p["level"] for p in new}
    old_levels = {p["name"]: p["level"] for p in get_content()["programmes"]}
    for row in in_use:
        if (row.programme, row.specialisation) not in offered:
            raise ContentError(f"{row.programme} / {row.specialisation} cannot be removed or renamed: "
                               f"{row.n} application{'s' if row.n != 1 else ''} use it.", 409)
        if row.programme in old_levels and levels.get(row.programme) != old_levels[row.programme]:
            raise ContentError(f"{row.programme} cannot switch between UG and PG: applications already have "
                               "academic details for the current level.", 409)


def _sync_seats(new: list[dict]) -> None:
    """Keep the seat matrix (migration 006) in step: a new programme/specialisation gets a row with 0
    seats; a removed one (never in use, see the check above) loses its row."""
    pairs = [{"p": p["name"], "s": s} for p in new for s in p["specialisations"]]
    db.session.execute(text(
        "INSERT INTO programme_seats (programme, specialisation, seats) VALUES (:p, :s, 0) "
        "ON CONFLICT (programme, specialisation) DO NOTHING"), pairs)
    keep = {(x["p"], x["s"]) for x in pairs}
    for row in db.session.execute(text("SELECT programme, specialisation FROM programme_seats")).all():
        if (row.programme, row.specialisation) not in keep:
            db.session.execute(text("DELETE FROM programme_seats WHERE programme = :p AND specialisation = :s"),
                               {"p": row.programme, "s": row.specialisation})


# ----------------------------------------------------------------------------- write side
def save_section(section: str, value, admin) -> dict:
    """Validate and store one section. The audit entry is written FIRST: if it cannot be written,
    nothing changes. Returns the full admin view of the content afterwards."""
    if section not in SECTIONS:
        raise ContentError("Unknown section.", 404)
    cleaned = validate(section, value)
    if section == "programmes":
        _check_programmes_against_applications(cleaned)

    admin_id = admin.id
    row = db.session.get(SiteSetting, section)
    if row is None:
        row = SiteSetting(key=section)
        db.session.add(row)
    row.value, row.updated_at, row.updated_by = cleaned, datetime.utcnow(), admin_id
    if section == "programmes":
        _sync_seats(cleaned)

    try:
        admin_service.write_audit(admin_id, "CONTENT_UPDATED", details={"section": section})
    except Exception:
        db.session.rollback()
        log.exception("content not saved: audit entry could not be written section=%s", section)
        raise ContentError("The change could not be recorded in the audit log, so it was not saved. "
                           "Please try again.", 500)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.exception("content save failed section=%s", section)
        raise ContentError("The change could not be saved. Please try again.", 500)
    log.info("content updated section=%s admin=%s", section, admin_id)
    return admin_content()


def reset_section(section: str, admin) -> dict:
    """Go back to the default for a section (deletes its row). Programmes are checked like a save."""
    if section not in SECTIONS:
        raise ContentError("Unknown section.", 404)
    if section == "programmes":
        default = defaults()["programmes"]
        _check_programmes_against_applications(default)
        _sync_seats(default)
    row = db.session.get(SiteSetting, section)
    if row is not None:
        db.session.delete(row)
    try:
        admin_service.write_audit(admin.id, "CONTENT_RESET", details={"section": section})
    except Exception:
        db.session.rollback()
        raise ContentError("The change could not be recorded in the audit log, so it was not saved.", 500)
    db.session.commit()
    return admin_content()
