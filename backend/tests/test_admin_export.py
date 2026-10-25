"""Applicant export, CSV and PDF (SRD FR-11), against real PostgreSQL."""
import csv
import io
from datetime import datetime, timedelta

import pytest

from app.models import AuditLog
from app.services import export_service, pdf_service

CSV_URL = "/api/admin/export/applicants.csv"
PDF_URL = "/api/admin/export/applicants.pdf"


def _csv_rows(resp):
    text = resp.data.decode("utf-8-sig")  # the byte-order mark is there for Excel
    return list(csv.reader(io.StringIO(text)))


def _exports():
    return AuditLog.query.filter_by(action_type="EXPORT_APPLICANTS").all()


# ------------------------------------------------------------------------------ CSV
def test_csv_has_a_header_row_and_one_row_per_applicant(logged_in, make_student):
    make_student(name="Meena Iyer", status="PAID", payment="SUCCESS")
    make_student(name="Ravi Kumar")

    resp = logged_in.get(CSV_URL)

    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert resp.data.startswith(b"\xef\xbb\xbf")
    assert resp.headers["Content-Disposition"].startswith('attachment; filename="admitflow-applicants-')
    assert resp.headers["Cache-Control"] == "no-store"
    rows = _csv_rows(resp)
    assert rows[0] == export_service.HEADERS
    by_name = {r[0]: r for r in rows[1:]}
    assert set(by_name) == {"Meena Iyer", "Ravi Kumar"}
    meena = dict(zip(rows[0], by_name["Meena Iyer"]))
    assert (meena["Stage"], meena["Payment"], meena["Programme"], meena["Specialisation"]) == \
        ("Submitted & paid", "Paid", "B.Tech", "CSE")
    ravi = dict(zip(rows[0], by_name["Ravi Kumar"]))
    assert (ravi["Stage"], ravi["Payment"], ravi["Programme"]) == ("Not started", "No attempt", "")


def test_the_latest_submitted_aptitude_score_is_exported(logged_in, make_student):
    from app.extensions import db
    from app.models import Application, TestPaper, TestSubmission

    scored = make_student(name="Meena Iyer", status="PAID", payment="SUCCESS")
    make_student(name="Ravi Kumar", status="PAID", payment="SUCCESS")   # assigned nothing: empty cell
    application = Application.query.filter_by(student_id=scored.id).one()
    now = datetime.utcnow()
    for title, score, submitted in [("Old test", 4, now - timedelta(days=2)), ("New test", 7.5, now)]:
        paper = TestPaper(title=title, duration_minutes=10, total_marks=10, pass_marks=5, is_published=True)
        db.session.add(paper)
        db.session.flush()
        db.session.add(TestSubmission(application_id=application.id, test_paper_id=paper.id,
                                      score=score, started_at=submitted, submitted_at=submitted))
    db.session.commit()

    rows = _csv_rows(logged_in.get(CSV_URL))
    by_name = {r[0]: dict(zip(rows[0], r)) for r in rows[1:]}

    assert by_name["Meena Iyer"]["Aptitude score"] == "7.5"   # the most recent submission, not the first
    assert by_name["Ravi Kumar"]["Aptitude score"] == ""


def test_scores_are_formatted_without_trailing_zeros():
    from decimal import Decimal

    assert export_service._score(Decimal("7.00")) == "7"
    assert export_service._score(Decimal("7.50")) == "7.5"
    assert export_service._score(Decimal("0.00")) == "0"
    assert export_service._score(None) == ""


def test_export_uses_exactly_the_same_filters_and_order_as_the_applicant_table(logged_in, make_student):
    now = datetime.utcnow()
    for i, (status, payment) in enumerate([("PAID", "SUCCESS"), ("PAYMENT_PENDING", "FAILED"),
                                           ("PAID", "SUCCESS"), (None, None)]):
        make_student(name=f"Applicant {i}", status=status, payment=payment, created=now - timedelta(days=i))
    params = {"stage": "PAID", "sort": "name", "order": "desc"}

    table = logged_in.get("/api/admin/students", query_string=params).json["data"]["students"]
    exported = _csv_rows(logged_in.get(CSV_URL, query_string=params))[1:]

    assert [r[1] for r in exported] == [s["email"] for s in table]
    assert len(exported) == 2


def test_search_filter_applies(logged_in, make_student):
    make_student(name="Meena Iyer")
    make_student(name="Ravi Kumar")

    rows = _csv_rows(logged_in.get(CSV_URL, query_string={"q": "meena"}))

    assert [r[0] for r in rows[1:]] == ["Meena Iyer"]


@pytest.mark.parametrize("name", ["=HYPERLINK(\"http://evil.test\",\"click\")", "+1+1", "-2+3", "@SUM(A1:A2)"])
def test_a_name_that_looks_like_a_formula_is_exported_as_text(logged_in, make_student, name):
    make_student(name=name)

    rows = _csv_rows(logged_in.get(CSV_URL))

    assert rows[1][0] == "'" + name


def test_names_in_any_script_survive_the_csv(logged_in, make_student):
    make_student(name="விஜய குமார்")

    rows = _csv_rows(logged_in.get(CSV_URL))

    assert rows[1][0] == "விஜய குமார்"


def test_safe_cell_leaves_ordinary_values_alone():
    assert export_service.safe_cell("Meena Iyer") == "Meena Iyer"
    assert export_service.safe_cell("9123456780") == "9123456780"
    assert export_service.safe_cell("") == ""
    assert export_service.safe_cell(None) == ""


# ------------------------------------------------------------------------------ PDF
def test_pdf_export_is_a_pdf_attachment(logged_in, make_student):
    make_student(name="Meena Iyer", status="PAID", payment="SUCCESS")

    resp = logged_in.get(PDF_URL, query_string={"stage": "PAID"})

    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data.startswith(b"%PDF")
    assert resp.headers["Content-Disposition"].endswith('.pdf"')
    assert resp.headers["Cache-Control"] == "no-store"


def test_pdf_template_escapes_applicant_values():
    html = pdf_service._applicants_template({
        "headers": ["Name"], "rows": [["<script>alert(1)</script>"]], "filters": "all", "generated_at": "now"})

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_an_empty_export_still_produces_a_file(logged_in):
    assert logged_in.get(PDF_URL).status_code == 200
    assert _csv_rows(logged_in.get(CSV_URL)) == [export_service.HEADERS]


# --------------------------------------------------------------------- audit and limits
def test_every_export_is_audited_with_format_filters_and_row_count(logged_in, make_student, admin):
    make_student(name="Meena Iyer", status="PAID", payment="SUCCESS")
    make_student(name="Ravi Kumar")

    logged_in.get(CSV_URL, query_string={"stage": "PAID"})
    logged_in.get(PDF_URL)

    entries = sorted(_exports(), key=lambda e: e.created_at)
    assert [(e.admin_id, e.details["format"], e.details["rows"]) for e in entries] == \
        [(admin.id, "csv", 1), (admin.id, "pdf", 2)]
    assert entries[0].details["filters"]["stage"] == "PAID"
    assert "stage Submitted & paid" in entries[0].details["description"]


def test_no_audit_entry_means_no_export(logged_in, make_student, monkeypatch):
    from app.services import admin_service

    make_student(name="Meena Iyer")

    def broken(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(admin_service, "write_audit", broken)
    resp = logged_in.get(CSV_URL)

    assert resp.status_code == 500
    assert b"Meena" not in resp.data
    assert resp.json["success"] is False


def test_invalid_filters_are_refused_and_not_audited(logged_in):
    for params in ({"stage": "NOPE"}, {"payment_status": "MAYBE"}, {"sort": "password_hash"}, {"order": "sideways"}):
        resp = logged_in.get(CSV_URL, query_string=params)
        assert resp.status_code == 400, params
    assert _exports() == []


def test_too_many_matches_asks_for_narrower_filters(logged_in, make_student, monkeypatch):
    monkeypatch.setattr(export_service, "MAX_ROWS", 1)
    make_student(name="One")
    make_student(name="Two")

    resp = logged_in.get(CSV_URL)

    assert resp.status_code == 400
    assert "Narrow the filters" in resp.json["error"]
    assert _exports() == []
