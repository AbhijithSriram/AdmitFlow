"""ERP statistics module (SRD FR-11, Person 2): the seat matrix routes.

conftest.py only loads schema.sql and 002_admin_portal.sql, so the programme_seats table is created
here by running the real 006 migration file (which also tests that migration).
"""
import pathlib
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from app.extensions import db
from app.models import AuditLog
from app.services import stats_service

MIGRATION = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "006_seat_matrix.sql"
URL = "/api/admin/seats"


def _run_migration():
    db.session.connection().exec_driver_sql(MIGRATION.read_text())
    db.session.commit()


def _wipe_seats():
    db.session.rollback()
    db.session.execute(text("DELETE FROM programme_seats"))
    db.session.commit()


@pytest.fixture
def seat_table(app):
    _run_migration()
    _wipe_seats()
    yield
    _wipe_seats()


@pytest.fixture
def seats(seat_table):
    """Three known rows, inserted out of order."""
    db.session.execute(text(
        "INSERT INTO programme_seats (programme, specialisation, seats) VALUES "
        "('MCA', 'General', 40), ('B.Tech', 'IT', 50), ('B.Tech', 'CSE', 100)"))
    db.session.commit()


def _rows(client):
    resp = client.get(URL)
    assert resp.status_code == 200
    return resp.json["data"]["seats"]


def _as_set(rows):
    return {(r["programme"], r["specialisation"], r["seats"]) for r in rows}


ORIGINAL = {("B.Tech", "CSE", 100), ("B.Tech", "IT", 50), ("MCA", "General", 40)}


def test_get_seats_lists_the_matrix(logged_in, seats):
    rows = _rows(logged_in)
    assert len(rows) == 3
    assert _as_set(rows) == ORIGINAL
    assert rows[0]["programme"] == "B.Tech" and rows[0]["specialisation"] == "CSE"  # sorted


def test_put_updates_only_the_rows_sent_and_audits_the_change(logged_in, seats, admin):
    r = logged_in.put(URL, json={"seats": [{"programme": "B.Tech", "specialisation": "CSE", "seats": 110}]})
    assert r.status_code == 200
    assert r.json["data"]["changed"] == 1
    assert _as_set(r.json["data"]["seats"]) == {("B.Tech", "CSE", 110), ("B.Tech", "IT", 50), ("MCA", "General", 40)}
    assert _as_set(_rows(logged_in)) == _as_set(r.json["data"]["seats"])

    row = AuditLog.query.one()
    assert (row.action_type, row.admin_id) == ("UPDATE_SEATS", admin.id)
    assert row.details == {"changes": [
        {"programme": "B.Tech", "specialisation": "CSE", "from": 100, "to": 110}]}


def test_put_adds_a_new_row_and_trims_names(logged_in, seats):
    r = logged_in.put(URL, json={"seats": [{"programme": " M.Sc. ", "specialisation": " Physics ", "seats": 25}]})
    assert r.status_code == 200 and r.json["data"]["changed"] == 1
    assert _as_set(_rows(logged_in)) == ORIGINAL | {("M.Sc.", "Physics", 25)}
    assert AuditLog.query.one().details["changes"][0]["from"] is None


def test_put_with_unchanged_numbers_writes_no_audit_entry(logged_in, seats):
    r = logged_in.put(URL, json={"seats": [{"programme": "B.Tech", "specialisation": "CSE", "seats": 100}]})
    assert r.status_code == 200 and r.json["data"]["changed"] == 0
    assert AuditLog.query.count() == 0


def _row(programme="B.Tech", specialisation="CSE", seats=10):
    return {"programme": programme, "specialisation": specialisation, "seats": seats}


@pytest.mark.parametrize("body", [
    pytest.param(None, id="no-body"),
    pytest.param({}, id="empty-object"),
    pytest.param({"seats": "many"}, id="seats-not-a-list"),
    pytest.param({"seats": []}, id="empty-list"),
    pytest.param({"seats": [_row(seats=-1)]}, id="negative"),
    pytest.param({"seats": [_row(seats=1.5)]}, id="fractional"),
    pytest.param({"seats": [_row(seats=True)]}, id="boolean"),
    pytest.param({"seats": [_row(seats="10")]}, id="numeric-string"),
    pytest.param({"seats": [_row(seats=100001)]}, id="too-many"),
    pytest.param({"seats": [{"specialisation": "CSE", "seats": 10}]}, id="missing-programme"),
    pytest.param({"seats": [_row(specialisation="   ")]}, id="blank-specialisation"),
    pytest.param({"seats": [_row(), _row()]}, id="duplicate-rows"),
    pytest.param({"seats": ["B.Tech"]}, id="row-not-an-object"),
    pytest.param({"seats": [_row(programme="x" * 101)]}, id="name-too-long"),
    pytest.param({"seats": [_row(seats=999), _row(specialisation="IT", seats=-5)]}, id="valid-row-plus-invalid-row"),
])
def test_bad_payloads_are_rejected_and_change_nothing(logged_in, seats, body):
    r = logged_in.put(URL, json=body)
    assert r.status_code == 400
    assert r.json["success"] is False and isinstance(r.json["error"], str)
    assert _as_set(_rows(logged_in)) == ORIGINAL
    assert AuditLog.query.count() == 0


def test_database_error_returns_500_and_writes_no_audit_entry(logged_in, seats, monkeypatch):
    def boom(rows):
        raise RuntimeError("db down")

    monkeypatch.setattr(stats_service, "set_seats", boom)
    r = logged_in.put(URL, json={"seats": [_row()]})
    assert r.status_code == 500 and r.json["success"] is False
    assert AuditLog.query.count() == 0


def test_migration_is_safe_to_run_twice_and_keeps_admin_changes(seat_table):
    def totals():
        return tuple(db.session.execute(text("SELECT count(*), sum(seats) FROM programme_seats")).one())

    _run_migration()  # seeds the 15 demo rows into the emptied table
    assert totals() == (15, 672)

    db.session.execute(text(
        "UPDATE programme_seats SET seats = 999 WHERE programme = 'MCA' AND specialisation = 'General'"))
    db.session.commit()
    _run_migration()  # second run: no duplicates, and the admin's change is not overwritten
    assert totals() == (15, 672 - 60 + 999)


# ----------------------------------------------------------------------- summary
SUMMARY_URL = "/api/admin/stats/summary"


def test_summary_is_all_zeros_with_no_data(logged_in):
    r = logged_in.get(SUMMARY_URL)
    assert r.status_code == 200
    assert r.json["data"] == {"registrations": 0, "applications_started": 0, "paid": 0, "payment_pending": 0}


def test_summary_counts_each_stage(logged_in, make_student):
    make_student()                                         # registered, never opened the form
    make_student(status="NOT_STARTED")                     # has an application row, not started
    make_student(status="IN_PROGRESS")
    make_student(status="PAYMENT_PENDING", payment="FAILED")
    make_student(status="PAID", payment="SUCCESS")
    make_student(status="PAID", payment="SUCCESS")

    r = logged_in.get(SUMMARY_URL)
    assert r.status_code == 200
    assert r.json["data"] == {
        "registrations": 6,
        "applications_started": 4,   # IN_PROGRESS + PAYMENT_PENDING + 2 x PAID
        "paid": 2,
        "payment_pending": 1,
    }


# ---------------------------------------------------------------------- programmes
PROGRAMMES_URL = "/api/admin/stats/programmes"


def _set_programme(student, programme, specialisation):
    db.session.execute(
        text("UPDATE applications SET programme = :p, specialisation = :s WHERE student_id = :sid"),
        {"p": programme, "s": specialisation, "sid": student.id})
    db.session.commit()


def _add_paper(pass_marks=10):
    return db.session.execute(text(
        "INSERT INTO test_papers (title, duration_minutes, total_marks, pass_marks) "
        "VALUES ('Aptitude', 60, 20, :pm) RETURNING id"), {"pm": pass_marks}).scalar()


def _add_submission(student, paper_id, score):
    app_id = db.session.execute(
        text("SELECT id FROM applications WHERE student_id = :sid"), {"sid": student.id}).scalar()
    db.session.execute(text(
        "INSERT INTO test_submissions (application_id, test_paper_id, score, submitted_at) "
        "VALUES (:a, :p, :sc, CASE WHEN :sc IS NULL THEN NULL ELSE now() END)"),
        {"a": app_id, "p": paper_id, "sc": score})
    db.session.commit()


def _by_name(logged_in):
    r = logged_in.get(PROGRAMMES_URL)
    assert r.status_code == 200
    return {(x["programme"], x["specialisation"]): x for x in r.json["data"]["programmes"]}


def test_programmes_is_empty_with_no_seats_and_no_applications(logged_in, seat_table):
    r = logged_in.get(PROGRAMMES_URL)
    assert r.status_code == 200 and r.json["data"]["programmes"] == []


def test_a_programme_with_no_applications_still_shows_its_seats(logged_in, seats):
    table = _by_name(logged_in)
    assert len(table) == 3
    assert table[("MCA", "General")] == {
        "programme": "MCA", "specialisation": "General", "seats": 40, "applied": 0, "paid": 0, "shortlisted": 0}


def test_applied_and_paid_counts_per_programme(logged_in, seats, make_student):
    make_student(status="IN_PROGRESS")                          # B.Tech / CSE (the fixture default)
    make_student(status="PAID", payment="SUCCESS")
    make_student(status="PAID", payment="SUCCESS")
    make_student(status="NOT_STARTED")                          # not started: not counted as applied
    mca = make_student(status="PAYMENT_PENDING", payment="FAILED")
    _set_programme(mca, "MCA", "General")

    table = _by_name(logged_in)
    assert (table[("B.Tech", "CSE")]["seats"], table[("B.Tech", "CSE")]["applied"],
            table[("B.Tech", "CSE")]["paid"]) == (100, 3, 2)
    assert (table[("MCA", "General")]["applied"], table[("MCA", "General")]["paid"]) == (1, 0)
    assert table[("B.Tech", "IT")]["applied"] == 0


def test_shortlisted_needs_paid_and_a_passing_score(logged_in, seats, make_student):
    paper = _add_paper(pass_marks=10)
    passed = make_student(status="PAID", payment="SUCCESS")
    failed = make_student(status="PAID", payment="SUCCESS")
    unscored = make_student(status="PAID", payment="SUCCESS")
    unpaid = make_student(status="PAYMENT_PENDING", payment="FAILED")
    _add_submission(passed, paper, 12)
    _add_submission(failed, paper, 8)
    _add_submission(unscored, paper, None)     # assigned but not taken yet
    _add_submission(unpaid, paper, 15)         # a good score does not help an unpaid application

    row = _by_name(logged_in)[("B.Tech", "CSE")]
    assert (row["applied"], row["paid"], row["shortlisted"]) == (4, 3, 1)


def test_a_student_with_two_passing_tests_is_shortlisted_once(logged_in, seats, make_student):
    student = make_student(status="PAID", payment="SUCCESS")
    _add_submission(student, _add_paper(pass_marks=5), 9)
    _add_submission(student, _add_paper(pass_marks=8), 9)
    assert _by_name(logged_in)[("B.Tech", "CSE")]["shortlisted"] == 1


def test_a_programme_missing_from_the_seat_matrix_still_shows_with_zero_seats(logged_in, seats, make_student):
    student = make_student(status="IN_PROGRESS")
    _set_programme(student, "M.Sc.", "Physics")
    row = _by_name(logged_in)[("M.Sc.", "Physics")]
    assert (row["seats"], row["applied"]) == (0, 1)


# ------------------------------------------------------------------ registrations
REG_URL = "/api/admin/stats/registrations"


def _registrations(client, **params):
    r = client.get(REG_URL, query_string=params)
    assert r.status_code == 200
    return r.json["data"]["registrations"]


def test_default_range_is_the_last_30_days_ending_today(logged_in):
    rows = _registrations(logged_in)
    assert len(rows) == 30
    assert rows[-1]["date"] == datetime.now(timezone.utc).date().isoformat()
    assert all(row["count"] == 0 for row in rows)


def test_days_without_registrations_are_filled_with_zero(logged_in, make_student):
    make_student(created=datetime(2026, 10, 1, 9, 0))
    make_student(created=datetime(2026, 10, 1, 17, 30))
    make_student(created=datetime(2026, 10, 3, 12, 0))
    rows = _registrations(logged_in, **{"from": "2026-10-01", "to": "2026-10-04"})
    assert rows == [
        {"date": "2026-10-01", "count": 2},
        {"date": "2026-10-02", "count": 0},
        {"date": "2026-10-03", "count": 1},
        {"date": "2026-10-04", "count": 0},
    ]


def test_both_ends_are_included_and_nothing_outside_is_counted(logged_in, make_student):
    make_student(created=datetime(2026, 9, 30, 23, 59, 59))   # just before the range
    make_student(created=datetime(2026, 10, 1, 0, 0, 0))      # first second of the range
    make_student(created=datetime(2026, 10, 2, 23, 59, 59))   # last second of the range
    make_student(created=datetime(2026, 10, 3, 0, 0, 0))      # just after the range
    rows = _registrations(logged_in, **{"from": "2026-10-01", "to": "2026-10-02"})
    assert [row["count"] for row in rows] == [1, 1]


def test_a_single_day_range(logged_in, make_student):
    make_student(created=datetime(2026, 10, 5, 8, 0))
    assert _registrations(logged_in, **{"from": "2026-10-05", "to": "2026-10-05"}) == [
        {"date": "2026-10-05", "count": 1}]


def test_only_to_given_means_the_30_days_ending_there(logged_in):
    rows = _registrations(logged_in, to="2026-10-30")
    assert len(rows) == 30 and rows[0]["date"] == "2026-10-01" and rows[-1]["date"] == "2026-10-30"


@pytest.mark.parametrize("params", [
    pytest.param({"from": "01-10-2026"}, id="wrong-format"),
    pytest.param({"from": "2026-13-01"}, id="impossible-date"),
    pytest.param({"from": "20261001"}, id="compact-iso-form"),
    pytest.param({"to": "tomorrow"}, id="not-a-date"),
    pytest.param({"from": "2026-10-05", "to": "2026-10-01"}, id="from-after-to"),
    pytest.param({"from": "2024-01-01", "to": "2026-10-01"}, id="range-too-long"),
])
def test_bad_ranges_are_rejected(logged_in, params):
    r = logged_in.get(REG_URL, query_string=params)
    assert r.status_code == 400
    assert r.json["success"] is False and isinstance(r.json["error"], str)
