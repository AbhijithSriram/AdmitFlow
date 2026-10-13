"""Which characters the free-text answers of the application form accept.

The form (frontend/src/utils/textRules.js) stops a student typing a digit into "Father's Name",
but that is only a convenience: the API is the source of truth, so the same rules are enforced here.
Keep the two in step.

Letters are any letter in any script, plus the combining marks the Indian scripts need, so names
are not limited to A-Z.
"""

import unicodedata

# kind -> (extra characters allowed besides letters and spaces, whether digits are allowed)
_RULES = {
    # Names of people, religion, mother tongue, guardian relationship.
    "person": (".'’-", False),
    # Districts, states, countries ("Andaman & Nicobar Islands").
    "place": (".,&'’()-", False),
    # Towns: post-office names such as "Sector 5" contain digits.
    "town": (".,&'’()/-", True),
    # Degree name and specialisation.
    "subject": (".,&'’()/-", False),
    # College and university names ("Anna University, Chennai - 25").
    "org": (".,&'’()/-", True),
}

# Form step -> {field: kind}. Fields not listed (addresses, scores, years, ...) are not text-only.
STEP_FIELD_KINDS = {
    1: {
        "father_name": "person",
        "mother_name": "person",
        "guardian_name": "person",
        "guardian_relationship": "person",
        "religion": "person",
        "mother_tongue": "person",
        "country": "place",
    },
    2: {
        **{f"{prefix}_town": "town" for prefix in ("perm", "comm")},
        **{f"{prefix}_{field}": "place" for prefix in ("perm", "comm") for field in ("district", "state", "country")},
    },
    # Step 3 is the programme choice (dropdowns); step 4 holds the academic details.
    4: {
        "ug_degree_other": "subject",
        "ug_specialisation": "subject",
        "college": "org",
        "university": "org",
        "xii_school": "org",
        "x_school": "org",
    },
}

_PHRASES = {
    "person": "letters only",
    "place": "letters only",
    "town": "letters and numbers only",
    "subject": "letters only",
    "org": "letters and numbers only",
}


def is_valid_text(kind: str, value: str) -> bool:
    """True if `value` is made only of what the kind allows and contains at least one letter.
    An empty value is valid here: whether a field is required is the form's business."""
    value = value.strip()
    if not value:
        return True
    punctuation, digits_ok = _RULES[kind]
    has_letter = False
    for ch in value:
        if ch.isalpha():
            has_letter = True
        elif ch == " " or ch in punctuation or unicodedata.category(ch).startswith("M"):
            continue
        elif digits_ok and unicodedata.category(ch) == "Nd":
            continue
        else:
            return False
    return has_letter and (value[0].isalpha() or digits_ok)


def describe(kind: str) -> str:
    return _PHRASES[kind]


def check_text(kind: str, value) -> bool:
    """Same as is_valid_text but False for anything that is not a string."""
    return isinstance(value, str) and is_valid_text(kind, value)


def step_text_error(step_number: int, payload: dict):
    """First problem in a step's text-only fields, as (field, message), or None if all are fine."""
    for field, kind in STEP_FIELD_KINDS.get(step_number, {}).items():
        if field not in payload:
            continue
        if not check_text(kind, payload[field]):
            return field, f"{_label(field)} can contain {describe(kind)}."
    return None


def _label(field: str) -> str:
    return field.replace("perm_", "permanent ").replace("comm_", "communication ").replace("_", " ").capitalize()
