"""Form fields shown in the order the form asks them, with readable labels (application PDF).

PostgreSQL's JSONB stores an object's keys sorted, so a saved step comes back A-Z. The order and
labels come from form_fields.json instead, the same catalogue the preview and admin panel use."""
from pathlib import Path

from app.services import form_fields, pdf_service

ROOT = Path(__file__).resolve().parents[2]


def test_the_backend_and_frontend_catalogues_are_identical():
    frontend = ROOT / "frontend" / "src" / "utils" / "formFields.json"
    backend = ROOT / "backend" / "app" / "services" / "form_fields.json"
    assert backend.read_text() == frontend.read_text(), "copy frontend/src/utils/formFields.json over the backend one"


def test_rows_follow_the_form_order_not_the_alphabet():
    saved = {"religion": "Hindu", "mother_name": "L", "father_name": "R", "full_name": "K", "ews": False}
    assert form_fields.ordered_rows(1, saved) == [
        ("Full name", "K"), ("Father's name", "R"), ("Mother's name", "L"), ("Religion", "Hindu"), ("EWS", "No")]


def test_true_and_false_read_as_yes_and_no():
    rows = form_fields.ordered_rows(2, {"same_as_permanent": True})
    assert rows == [("Communication address same as permanent", "Yes")]


def test_the_same_key_gets_its_own_steps_label():
    assert form_fields.ordered_rows(4, {"score": "8.1"}) == [("UG score", "8.1")]
    assert form_fields.ordered_rows(5, {"score": "95"}) == [("Score", "95")]


def test_an_unknown_field_is_still_shown_last_and_internal_keys_never():
    rows = form_fields.ordered_rows(6, {"photo_url": "applications/1/p.png", "new_thing": "x", "id_proof_type": "PAN"})
    assert rows == [("ID proof type", "PAN"), ("New thing", "x")]


def test_the_application_pdf_lists_class_xii_before_class_x():
    html = pdf_service._rows_html({"Academic Details": form_fields.ordered_rows(
        4, {"x_board": "CBSE", "xii_board": "State", "x_year": "2022", "xii_year": "2024"})})
    assert html.index("Class XII board") < html.index("Class XII year of passing") < html.index("Class X board")
    assert "Xii" not in html and "x board" not in html.lower().replace("class x board", "")
