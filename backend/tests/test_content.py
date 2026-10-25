"""Admin-editable site content (v1.1 FR-12): routes, validation, the programme rules, and everything
that reads the content (payments, Step 3, the brochure, PDFs and emails), against real PostgreSQL."""
import copy

import pytest
from sqlalchemy import text

from app.extensions import db
from app.models import Application, AuditLog, SiteSetting
from app.services import content_service, pdf_service

PUBLIC = "/api/content"
ADMIN = "/api/admin/content"


def _put(client, section, value):
    return client.put(f"{ADMIN}/{section}", json={"value": value})


def _defaults(section):
    return copy.deepcopy(content_service.defaults()[section])


def _seats():
    return {(r.programme, r.specialisation): r.seats
            for r in db.session.execute(text("SELECT programme, specialisation, seats FROM programme_seats")).all()}


@pytest.fixture
def seat_rows(app):
    """A known seat matrix for the tests that check the sync. programme_seats is not reset between
    tests (other files empty it), so set it here and put back whatever was there afterwards."""
    before = _seats()
    db.session.execute(text("DELETE FROM programme_seats"))
    db.session.execute(text(
        "INSERT INTO programme_seats (programme, specialisation, seats) VALUES "
        "('B.Tech', 'CSE', 120), ('MCA', 'General', 40)"))
    db.session.commit()
    yield
    db.session.rollback()
    db.session.execute(text("DELETE FROM programme_seats"))
    for (programme, specialisation), seats in before.items():
        db.session.execute(text("INSERT INTO programme_seats (programme, specialisation, seats) VALUES (:p, :s, :n)"),
                           {"p": programme, "s": specialisation, "n": seats})
    db.session.commit()


# ------------------------------------------------------------------------- reading
def test_public_content_is_the_defaults_until_an_admin_edits_it(client):
    resp = client.get(PUBLIC)

    assert resp.status_code == 200
    data = resp.json["data"]
    assert data["institution"]["name"] == "AdmitFlow Institute"
    assert data["fee"] == {"amount_inr": 1000}
    assert [p["name"] for p in data["programmes"]] == ["B.Tech", "M.Tech", "MCA", "M.Sc."]
    assert data["demo_mode"] is True
    assert resp.headers["Cache-Control"] == "public, max-age=60"


def test_admin_view_says_which_sections_are_still_defaults(logged_in):
    resp = logged_in.get(ADMIN)

    assert resp.status_code == 200
    assert set(resp.json["data"]["meta"]) == set(content_service.SECTIONS)
    assert all(v is None for v in resp.json["data"]["meta"].values())


@pytest.mark.parametrize("method, path", [("GET", ADMIN), ("PUT", f"{ADMIN}/fee"), ("DELETE", f"{ADMIN}/fee")])
def test_editing_needs_an_admin(client, make_student, method, path):
    assert client.open(path, method=method, json={"value": {}}).status_code == 401
    with client.session_transaction() as sess:
        sess["student_id"] = make_student().id
    client.set_cookie("admitflow_student_session", "x")
    assert client.open(path, method=method, json={"value": {}}).status_code in (401, 403)


# ------------------------------------------------------------------------- saving
@pytest.mark.parametrize("section, value", [
    ("institution", {"name": "Sunrise College of Engineering", "about": ["A demo college."]}),
    ("contact", {"email": "office@sunrise.test", "phone": "+91 44 1234 5678", "address": "1 Main Road",
                 "hours": "9 to 5", "note": None}),
    ("dates", {"items": [{"label": "Applications open", "value": "1 June 2027"}], "note": ""}),
    ("guidelines", ["Read carefully.", "The fee is {fee}."]),
    ("eligibility", ["A pass in Class XII."]),
    ("documents", ["Class X mark sheet"]),
    ("fee", {"amount_inr": 1500}),
    ("suggestions", {"colleges": ["Sunrise College"], "universities": ["Anna University"]}),
])
def test_each_section_can_be_saved_and_reaches_the_public_content(logged_in, section, value):
    resp = _put(logged_in, section, value)

    assert resp.status_code == 200, resp.json
    saved = logged_in.get(PUBLIC).json["data"][section]
    if section == "contact":
        assert saved["email"] == "office@sunrise.test" and saved["note"] is None
    elif section == "dates":
        assert saved == {"items": value["items"], "note": None}   # empty optional text is stored as None
    else:
        assert saved == value
    assert resp.json["data"]["meta"][section]["updated_by"] is not None
    entry = AuditLog.query.filter_by(action_type="CONTENT_UPDATED").one()
    assert entry.details == {"section": section}


def test_text_is_trimmed(logged_in):
    _put(logged_in, "institution", {"name": "  Sunrise College  ", "about": ["  Hello  "]})

    assert logged_in.get(PUBLIC).json["data"]["institution"] == {"name": "Sunrise College", "about": ["Hello"]}


@pytest.mark.parametrize("section, value, message", [
    ("institution", {"name": "", "about": []}, "Institution name is required"),
    ("institution", {"name": "x" * 121, "about": []}, "at most 120"),
    ("contact", {"email": "not-an-email"}, "valid contact email"),
    ("dates", {"items": []}, "between 1 and 15"),
    ("dates", {"items": [{"label": "Open", "value": ""}]}, "Date 1: when is required"),
    ("guidelines", [], "at least 1"),
    ("guidelines", ["ok", ""], "Guideline 2 is required"),
    ("fee", {"amount_inr": 0}, "from 1 to"),
    ("fee", {"amount_inr": "1000"}, "whole number"),
    ("fee", {"amount_inr": True}, "whole number"),
    ("suggestions", {"colleges": ["<script>"], "universities": []}, "can contain"),
    ("suggestions", {"colleges": ["A College", "a college"], "universities": []}, "more than once"),
    ("programmes", [], "between 1 and 30"),
    ("programmes", [{"name": "B.Tech", "level": "PhD", "specialisations": ["CSE"]}], "choose UG"),
    ("programmes", [{"name": "B.Tech", "level": "UG", "specialisations": []}], "at least 1"),
    ("programmes", [{"name": "X", "level": "UG", "specialisations": ["A"]},
                    {"name": "x", "level": "PG", "specialisations": ["B"]}], "more than once"),
])
def test_invalid_values_are_refused_with_a_reason_and_nothing_is_saved(logged_in, section, value, message):
    resp = _put(logged_in, section, value)

    assert resp.status_code == 400
    assert message in resp.json["error"]
    assert db.session.get(SiteSetting, section) is None
    assert AuditLog.query.filter_by(action_type="CONTENT_UPDATED").count() == 0


def test_an_unknown_section_is_404(logged_in):
    assert _put(logged_in, "passwords", {"x": 1}).status_code == 404


def test_a_body_without_value_is_refused(logged_in):
    assert logged_in.put(f"{ADMIN}/fee", json={"amount_inr": 5}).status_code == 400


def test_reset_goes_back_to_the_default(logged_in):
    _put(logged_in, "fee", {"amount_inr": 2500})

    resp = logged_in.delete(f"{ADMIN}/fee")

    assert resp.status_code == 200
    assert logged_in.get(PUBLIC).json["data"]["fee"] == {"amount_inr": 1000}
    assert AuditLog.query.filter_by(action_type="CONTENT_RESET").count() == 1


def test_no_audit_entry_means_no_change(logged_in, monkeypatch):
    from app.services import admin_service

    def broken(*args, **kwargs):
        raise RuntimeError("audit down")

    monkeypatch.setattr(admin_service, "write_audit", broken)
    resp = _put(logged_in, "fee", {"amount_inr": 2500})

    assert resp.status_code == 500
    db.session.expire_all()
    assert db.session.get(SiteSetting, "fee") is None


# ------------------------------------------------------------------------- programmes
def test_a_new_programme_gets_a_seat_row_and_a_removed_unused_one_loses_it(logged_in, seat_rows):
    programmes = _defaults("programmes")
    programmes.append({"name": "B.Sc.", "level": "UG", "specialisations": ["Physics", "Chemistry"]})
    programmes = [p for p in programmes if p["name"] != "MCA"]   # nobody applied to MCA

    assert _put(logged_in, "programmes", programmes).status_code == 200

    seats = _seats()
    assert seats[("B.Sc.", "Physics")] == 0 and seats[("B.Sc.", "Chemistry")] == 0
    assert ("MCA", "General") not in seats
    assert seats[("B.Tech", "CSE")] == 120   # existing seat numbers are untouched


def test_a_programme_in_use_cannot_be_removed_or_renamed(logged_in, make_student, seat_rows):
    make_student(status="IN_PROGRESS")   # applies to B.Tech / CSE
    renamed = _defaults("programmes")
    renamed[0]["specialisations"][0] = "Computer Science and Engineering"   # CSE -> renamed

    resp = _put(logged_in, "programmes", renamed)

    assert resp.status_code == 409
    assert "B.Tech / CSE cannot be removed or renamed: 1 application use" in resp.json["error"]
    assert db.session.get(SiteSetting, "programmes") is None
    assert ("B.Tech", "CSE") in _seats()


def test_a_programme_in_use_cannot_switch_between_ug_and_pg(logged_in, make_student):
    make_student(status="IN_PROGRESS")
    switched = _defaults("programmes")
    switched[0]["level"] = "PG"

    resp = _put(logged_in, "programmes", switched)

    assert resp.status_code == 409 and "cannot switch between UG and PG" in resp.json["error"]


def test_step_3_accepts_only_offered_programmes(client, logged_in, make_student):
    student = make_student(status="IN_PROGRESS", files=False)
    application = Application.query.filter_by(student_id=student.id).one()
    with client.session_transaction() as sess:
        sess["student_id"] = student.id
    url = f"/api/app/draft/{application.id}/step/3"

    assert client.patch(url, json={"programme": "B.Arch", "specialisation": "Design"}).status_code == 400
    assert client.patch(url, json={"programme": "B.Tech", "specialisation": "Design"}).status_code == 400
    assert client.patch(url, json={"programme": "B.Tech", "specialisation": ""}).status_code == 200   # half-filled autosave
    assert client.patch(url, json={"programme": "B.Tech", "specialisation": "IT"}).status_code == 200

    programmes = _defaults("programmes") + [{"name": "B.Arch", "level": "UG", "specialisations": ["Design"]}]
    assert _put(logged_in, "programmes", programmes).status_code == 200
    assert client.patch(url, json={"programme": "B.Arch", "specialisation": "Design"}).status_code == 200


# ------------------------------------------------------------------------- consumers
def test_the_fee_set_by_an_admin_is_what_payment_charges(client, logged_in, make_student, monkeypatch):
    from app.models import Payment
    from app.services import payment_service

    charged = {}
    monkeypatch.setattr(payment_service, "create_order", lambda amount_paise, receipt: charged.update(
        amount=amount_paise) or {"id": "order_fee", "amount": amount_paise, "currency": "INR"})
    _put(logged_in, "fee", {"amount_inr": 1575})
    student = make_student(status="IN_PROGRESS", files=False)
    with client.session_transaction() as sess:
        sess["student_id"] = student.id

    assert client.post("/api/app/payment/create-order").status_code == 201
    assert charged["amount"] == 157500
    assert float(Payment.query.filter_by(razorpay_order_id="order_fee").one().amount) == 1575.0


def test_the_brochure_is_generated_from_the_current_content(logged_in, client):
    _put(logged_in, "institution", {"name": "Sunrise <College>", "about": []})
    _put(logged_in, "guidelines", ["The fee is {fee}."])
    _put(logged_in, "fee", {"amount_inr": 1575})

    resp = client.get("/api/content/brochure")

    assert resp.status_code == 200 and resp.data.startswith(b"%PDF")
    assert resp.headers["Cache-Control"] == "no-store"
    html = pdf_service._brochure_template(content_service.get_content(), 1575, "")
    assert "Sunrise &lt;College&gt;" in html          # admin text is escaped
    assert "The fee is ₹1,575." in html            # {fee} is filled in
    assert "Rs. 1,575" in html


def test_pdf_footer_carries_the_edited_name_and_cannot_break_out_of_the_css(app, logged_in):
    _put(logged_in, "institution", {"name": 'Evil" } body { display:none } </style><script>', "about": []})
    with app.app_context():
        footer = content_service.demo_footer()
    style = pdf_service._style({"demo_footer": footer})

    assert "</style>" not in style and '"} body' not in style
    assert "Evil" in style


def test_demo_mode_off_removes_every_disclaimer(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "DEMO_MODE", False)
    from app.services import email_service

    assert client.get(PUBLIC).json["data"]["demo_mode"] is False
    with app.app_context():
        assert content_service.demo_footer() == ""
        assert email_service.demo_footer_html() == ""
    assert "@bottom-center" not in pdf_service._style({"demo_footer": ""})
