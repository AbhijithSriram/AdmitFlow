"""The application form's fields in the order the form asks them, with readable labels.

PostgreSQL's JSONB keeps an object's keys sorted, so a saved step comes back alphabetically;
the PDF uses this catalogue instead. form_fields.json is a copy of
frontend/src/utils/formFields.json (the preview and admin panel use that one): keep the two
identical, tests/test_form_fields.py checks it.
"""
import json
from pathlib import Path

_CATALOGUE = {
    int(step): fields
    for step, fields in json.loads((Path(__file__).with_name("form_fields.json")).read_text()).items()
}


def _value(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return value


def _fallback_label(key: str) -> str:
    text = key.replace("_", " ")
    return text[:1].upper() + text[1:]


def ordered_rows(step: int, data: dict) -> list[tuple[str, object]]:
    """(label, value) rows for one saved step: catalogue fields first, in form order, then any
    field the catalogue does not know yet (so nothing is hidden). `*_url` storage keys are skipped."""
    data = {key: value for key, value in (data or {}).items() if not key.endswith("_url")}
    known = _CATALOGUE.get(step, [])
    rows = [(label, _value(data[key])) for key, label in known if key in data]
    listed = {key for key, _ in known}
    rows += [(_fallback_label(key), _value(value)) for key, value in data.items() if key not in listed]
    return rows
