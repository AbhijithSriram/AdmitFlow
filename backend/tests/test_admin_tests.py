"""Admin side of the aptitude test (FR-10): /api/admin/tests, scores in the applicant views, hard delete."""
from datetime import datetime, timedelta
from unittest import mock

import pytest

from app.extensions import db
from app.models import Application, AuditLog, Student
from app.models.test_paper import TestPaper
from app.models.test_question import TestQuestion
from app.models.test_submission import TestSubmission
from app.services import test_service

URL = "/api/admin/tests"


def question(n=1, correct="B", marks=1):
    return {"question_text": f"Question {n}?", "option_a": "a", "option_b": "b", "option_c": "c",
            "option_d": "d", "correct_option": correct, "marks": marks}


def paper_body(**over):
    body = {"title": "Aptitude 1", "duration_minutes": 30, "total_marks": 3, "pass_marks": 2,
            "questions": [question(1), question(2, "C"), question(3, "D")]}
    body.update(over)
    return body


def make_paper(c, publish=False, **over):
    r = c.post(URL, json=paper_body(**over))
    assert r.status_code == 201, r.json
    pid = r.json["data"]["id"]
    if publish:
        assert c.post(f"{URL}/{pid}/publish").status_code == 200
    return pid


@pytest.fixture
def paid(make_student):
    """Create a PAID applicant; returns (student, application)."""
    def _paid(name="Paid Student", programme="B.Tech", specialisation="CSE"):
        s = make_student(name, status="PAID", payment="SUCCESS")
        a = Application.query.filter_by(student_id=s.id).first()
        a.programme, a.specialisation = programme, specialisation
        db.session.commit()
        return s, a
    return _paid


# ----------------------------------------------------------------- create / read
def test_create_and_read_back_in_authoring_order(logged_in, admin):
    pid = make_paper(logged_in)
    d = logged_in.get(f"{URL}/{pid}").json["data"]
    assert (d["title"], d["is_published"], d["total_marks"], d["pass_marks"]) == ("Aptitude 1", False, 3, 2)
    assert [q["question_text"] for q in d["questions"]] == ["Question 1?", "Question 2?", "Question 3?"]
    assert [q["correct_option"] for q in d["questions"]] == ["B", "C", "D"]  # admins see the answers
    assert db.session.get(TestPaper, pid).created_by == admin.id


@pytest.mark.parametrize("change, message", [
    ({"title": "  "}, "title"),
    ({"duration_minutes": 0}, "Duration"),
    ({"duration_minutes": True}, "Duration"),          # True is an int in Python; must be rejected
    ({"duration_minutes": "30"}, "Duration"),
    ({"total_marks": 0}, "Total marks"),
    ({"pass_marks": 4}, "Pass marks"),                  # pass marks above total marks
    ({"pass_marks": -1}, "Pass marks"),
    ({"questions": []}, "at least one question"),
    ({"questions": "nope"}, "at least one question"),
    ({"questions": [{**question(), "correct_option": "E"}]}, "Question 1: choose exactly one correct"),
    ({"questions": [{**question(), "correct_option": "b"}]}, "Question 1: choose exactly one correct"),
    ({"questions": [{**question(), "correct_option": None}]}, "Question 1: choose exactly one correct"),
    ({"questions": [{**question(), "option_c": ""}]}, "Question 1: all four options"),
    ({"questions": [{k: v for k, v in question().items() if k != "option_d"}]}, "Question 1: all four options"),
    ({"questions": [{**question(), "question_text": " "}]}, "Question 1: enter the question text"),
    ({"questions": [{**question(), "marks": 0}]}, "Question 1: marks"),
    ({"questions": ["text"]}, "Question 1: invalid"),
])
def test_create_rejects_bad_input(logged_in, change, message):
    r = logged_in.post(URL, json=paper_body(**change))
    assert r.status_code == 400 and message in r.json["error"], r.json
    assert TestPaper.query.count() == 0


def test_create_with_a_bad_later_question_leaves_nothing_behind(logged_in):
    r = logged_in.post(URL, json=paper_body(questions=[question(1), {**question(2), "correct_option": "Z"}]))
    assert r.status_code == 400 and "Question 2" in r.json["error"]
    assert TestPaper.query.count() == 0 and TestQuestion.query.count() == 0


def test_create_needs_json(logged_in):
    assert logged_in.post(URL, data="not json", content_type="text/plain").status_code == 400


def test_list_shows_counts(logged_in, paid):
    pid = make_paper(logged_in, publish=True)
    paid("One"); paid("Two")
    logged_in.post(f"{URL}/{pid}/assign")
    t = logged_in.get(URL).json["data"]["tests"][0]
    assert (t["id"], t["question_count"], t["assigned"], t["submitted"], t["is_published"]) == (pid, 3, 2, 0, True)


def test_unknown_and_malformed_ids_are_404(logged_in):
    for pid in ("00000000-0000-4000-8000-000000000000", "not-a-uuid"):
        for method, suffix in (("get", ""), ("put", ""), ("delete", ""), ("post", "/publish"),
                               ("post", "/assign"), ("get", "/results")):
            r = getattr(logged_in, method)(f"{URL}/{pid}{suffix}", json=paper_body())
            assert r.status_code == 404, (method, suffix)


# ------------------------------------------------------------ edit / delete / publish
def test_edit_replaces_the_questions_while_unpublished(logged_in):
    pid = make_paper(logged_in)
    r = logged_in.put(f"{URL}/{pid}", json=paper_body(title="Renamed", total_marks=1, pass_marks=1,
                                                      questions=[question(9, "A")]))
    assert r.status_code == 200
    d = logged_in.get(f"{URL}/{pid}").json["data"]
    assert d["title"] == "Renamed" and [q["question_text"] for q in d["questions"]] == ["Question 9?"]
    assert TestQuestion.query.count() == 1  # the old three are gone, not orphaned


def test_failed_edit_keeps_the_old_paper(logged_in):
    pid = make_paper(logged_in)
    assert logged_in.put(f"{URL}/{pid}", json=paper_body(questions=[{**question(), "correct_option": "Q"}])).status_code == 400
    assert len(logged_in.get(f"{URL}/{pid}").json["data"]["questions"]) == 3


def test_cannot_edit_a_published_paper(logged_in):
    pid = make_paper(logged_in, publish=True)
    r = logged_in.put(f"{URL}/{pid}", json=paper_body(title="X"))
    assert r.status_code == 409 and "published" in r.json["error"]
    assert logged_in.get(f"{URL}/{pid}").json["data"]["title"] == "Aptitude 1"


def test_delete_unused_paper_removes_its_questions(logged_in):
    pid = make_paper(logged_in)
    r = logged_in.delete(f"{URL}/{pid}")
    assert r.status_code == 200 and r.json["data"] == {"deleted": True}
    assert TestPaper.query.count() == 0 and TestQuestion.query.count() == 0


def test_delete_with_submissions_is_a_clear_409_not_a_database_error(logged_in, paid):
    pid = make_paper(logged_in, publish=True)
    paid()
    logged_in.post(f"{URL}/{pid}/assign")
    r = logged_in.delete(f"{URL}/{pid}")
    assert r.status_code == 409 and "assigned" in r.json["error"]
    assert TestPaper.query.count() == 1 and TestSubmission.query.count() == 1


def test_publish_requires_marks_to_add_up(logged_in):
    pid = make_paper(logged_in, total_marks=5)  # questions add up to 3
    r = logged_in.post(f"{URL}/{pid}/publish")
    assert r.status_code == 400 and "3 marks" in r.json["error"] and "5" in r.json["error"]
    assert db.session.get(TestPaper, pid).is_published is False


def test_publish_uses_each_questions_own_marks(logged_in):
    pid = make_paper(logged_in, total_marks=6, pass_marks=3,
                     questions=[question(1, marks=1), question(2, marks=2), question(3, marks=3)])
    assert logged_in.post(f"{URL}/{pid}/publish").status_code == 200


def test_publish_is_idempotent_and_audited_once(logged_in):
    pid = make_paper(logged_in, publish=True)
    assert logged_in.post(f"{URL}/{pid}/publish").json["data"]["is_published"] is True
    assert AuditLog.query.filter_by(action_type="TEST_PUBLISHED").count() == 1


# ----------------------------------------------------------------------- assign
def test_assign_needs_a_published_paper(logged_in, paid):
    pid = make_paper(logged_in)
    paid()
    assert logged_in.post(f"{URL}/{pid}/assign").status_code == 409
    assert TestSubmission.query.count() == 0


def test_assign_only_reaches_paid_applicants(logged_in, paid, make_student):
    pid = make_paper(logged_in, publish=True)
    paid("Paid")
    make_student("Started", status="IN_PROGRESS")
    make_student("Pending", status="PAYMENT_PENDING", payment="FAILED")
    make_student("Nothing", status=None)
    r = logged_in.post(f"{URL}/{pid}/assign")
    assert r.status_code == 200 and r.json["data"]["assigned"] == 1
    assert TestSubmission.query.count() == 1


def test_assign_can_filter_by_programme_and_specialisation(logged_in, paid):
    pid = make_paper(logged_in, publish=True)
    paid("A", "B.Tech", "CSE"); paid("B", "B.Tech", "ECE"); paid("C", "M.Tech", "CSE")
    assert logged_in.post(f"{URL}/{pid}/assign", json={"programme": "B.Tech", "specialisation": "CSE"}).json["data"]["assigned"] == 1
    assert logged_in.post(f"{URL}/{pid}/assign", json={"programme": "B.Tech"}).json["data"]["assigned"] == 1  # only B is new
    assert TestSubmission.query.count() == 2


def test_assigning_twice_never_duplicates_or_resets(logged_in, paid):
    pid = make_paper(logged_in, publish=True)
    paid("One"); paid("Two")
    assert logged_in.post(f"{URL}/{pid}/assign").json["data"]["assigned"] == 2
    sub = TestSubmission.query.first()
    sub.started_at, sub.answers = datetime.utcnow(), {"q": "A"}   # a student has begun
    db.session.commit()
    second = logged_in.post(f"{URL}/{pid}/assign").json["data"]
    assert second["assigned"] == 0 and second["already_assigned"] == 2
    assert TestSubmission.query.count() == 2
    db.session.refresh(sub)
    assert sub.started_at is not None and sub.answers == {"q": "A"}  # progress untouched


def test_a_later_paid_applicant_is_picked_up_by_assigning_again(logged_in, paid):
    pid = make_paper(logged_in, publish=True)
    paid("First")
    logged_in.post(f"{URL}/{pid}/assign")
    paid("Second")
    assert logged_in.post(f"{URL}/{pid}/assign").json["data"]["assigned"] == 1


def test_assign_with_nobody_eligible_is_fine(logged_in):
    pid = make_paper(logged_in, publish=True)
    assert logged_in.post(f"{URL}/{pid}/assign").json["data"]["assigned"] == 0


def test_assign_rejects_blank_filters(logged_in):
    pid = make_paper(logged_in, publish=True)
    assert logged_in.post(f"{URL}/{pid}/assign", json={"programme": 5}).status_code == 400


def test_assign_writes_an_audit_entry(logged_in, paid, admin):
    pid = make_paper(logged_in, publish=True)
    paid()
    logged_in.post(f"{URL}/{pid}/assign")
    row = AuditLog.query.filter_by(action_type="TEST_ASSIGNED").one()
    assert row.admin_id == admin.id and row.details["assigned"] == 1 and row.details["paper_id"] == pid


# ---------------------------------------------------------------- results / reset
def _submit(sub, score, minutes_ago=0):
    sub.started_at = datetime.utcnow() - timedelta(minutes=minutes_ago + 20)
    sub.submitted_at = datetime.utcnow() - timedelta(minutes=minutes_ago)
    sub.score = score
    db.session.commit()


def test_results_show_status_score_and_pass_fail(logged_in, paid):
    pid = make_paper(logged_in, publish=True)           # pass marks = 2
    (_, a1), (_, a2), (_, a3), (_, a4) = paid("Passed"), paid("Failed"), paid("Midway"), paid("Waiting")
    logged_in.post(f"{URL}/{pid}/assign")
    subs = {s.application_id: s for s in TestSubmission.query.all()}
    _submit(subs[a1.id], 3); _submit(subs[a2.id], 1)
    subs[a3.id].started_at = datetime.utcnow(); db.session.commit()

    d = logged_in.get(f"{URL}/{pid}/results").json["data"]
    assert d["summary"] == {"assigned": 4, "started": 3, "submitted": 2, "passed": 1}
    by_name = {r["name"]: r for r in d["results"]}
    assert (by_name["Passed"]["status"], by_name["Passed"]["score"], by_name["Passed"]["passed"]) == ("SUBMITTED", 3.0, True)
    assert (by_name["Failed"]["status"], by_name["Failed"]["passed"]) == ("SUBMITTED", False)
    assert (by_name["Midway"]["status"], by_name["Midway"]["score"], by_name["Midway"]["passed"]) == ("IN_PROGRESS", None, None)
    assert by_name["Waiting"]["status"] == "ASSIGNED" and by_name["Waiting"]["submitted_at"] is None
    assert {"email", "programme", "specialisation", "assigned_at"} <= set(by_name["Passed"])


def test_results_are_paginated_twenty_per_page(logged_in, paid):
    pid = make_paper(logged_in, publish=True)
    for i in range(25):
        paid(f"Student {i:02d}")
    logged_in.post(f"{URL}/{pid}/assign")
    p1 = logged_in.get(f"{URL}/{pid}/results").json["data"]
    p2 = logged_in.get(f"{URL}/{pid}/results?page=2").json["data"]
    assert (p1["total"], p1["total_pages"], len(p1["results"]), len(p2["results"])) == (25, 2, 20, 5)
    assert logged_in.get(f"{URL}/{pid}/results?page=99").json["data"]["page"] == 2   # clamped
    assert logged_in.get(f"{URL}/{pid}/results?page=abc").status_code == 400


def test_results_for_an_unassigned_paper_are_empty(logged_in):
    pid = make_paper(logged_in, publish=True)
    d = logged_in.get(f"{URL}/{pid}/results").json["data"]
    assert d["results"] == [] and d["total_pages"] == 1 and d["summary"]["assigned"] == 0


def test_reset_clears_the_attempt_and_is_audited(logged_in, paid, admin):
    pid = make_paper(logged_in, publish=True)
    s, a = paid("Retaker")
    logged_in.post(f"{URL}/{pid}/assign")
    sub = TestSubmission.query.one()
    sub.answers = {"x": "A"}; _submit(sub, 2)

    r = logged_in.post(f"{URL}/{pid}/reset/{a.id}")
    assert r.status_code == 200 and r.json["data"]["status"] == "ASSIGNED"
    db.session.refresh(sub)
    assert (sub.answers, sub.score, sub.started_at, sub.submitted_at) == ({}, None, None, None)
    assert TestSubmission.query.count() == 1                       # same row, not a new one
    row = AuditLog.query.filter_by(action_type="TEST_ATTEMPT_RESET").one()
    assert (row.admin_id, row.target_student_id, row.target_email) == (admin.id, s.id, s.email)
    assert row.details["was"] == "SUBMITTED"


def test_reset_of_an_unassigned_applicant_or_bad_id_is_404(logged_in, paid):
    pid = make_paper(logged_in, publish=True)
    _, a = paid()
    assert logged_in.post(f"{URL}/{pid}/reset/{a.id}").status_code == 404           # never assigned
    assert logged_in.post(f"{URL}/{pid}/reset/not-a-uuid").status_code == 404
    assert AuditLog.query.filter_by(action_type="TEST_ATTEMPT_RESET").count() == 0


# ------------------------------------------- scores in the applicant views + delete
def test_applicant_list_shows_the_latest_submitted_score(logged_in, paid):
    s, a = paid("Scored")
    paid("Unscored")
    older, newer = make_paper(logged_in, publish=True, title="Old"), make_paper(logged_in, publish=True, title="New")
    for pid in (older, newer):
        logged_in.post(f"{URL}/{pid}/assign")
    for sub in TestSubmission.query.all():
        if sub.application_id == a.id:
            _submit(sub, 1 if sub.test_paper_id == older else 3, minutes_ago=60 if sub.test_paper_id == older else 5)
    rows = {r["name"]: r for r in logged_in.get("/api/admin/students").json["data"]["students"]}
    assert rows["Scored"]["aptitude_score"] == 3.0        # the more recent submission wins
    assert rows["Unscored"]["aptitude_score"] is None     # assigned but not submitted


def test_applicant_list_score_is_none_without_any_test(logged_in, make_student):
    make_student("Plain", status="IN_PROGRESS")
    assert logged_in.get("/api/admin/students").json["data"]["students"][0]["aptitude_score"] is None


def test_applicant_detail_lists_every_test(logged_in, paid):
    s, a = paid()
    pid = make_paper(logged_in, publish=True)
    logged_in.post(f"{URL}/{pid}/assign")
    _submit(TestSubmission.query.one(), 2)
    t = logged_in.get(f"/api/admin/students/{s.id}").json["data"]["aptitude"]
    assert len(t) == 1 and (t[0]["title"], t[0]["status"], t[0]["score"], t[0]["total_marks"], t[0]["passed"]) == ("Aptitude 1", "SUBMITTED", 2.0, 3, True)


def test_applicant_detail_has_an_empty_list_without_an_application(logged_in, make_student):
    s = make_student(status=None)
    assert logged_in.get(f"/api/admin/students/{s.id}").json["data"]["aptitude"] == []


def test_the_export_query_still_works_with_the_score_column(logged_in, paid):
    paid()
    assert logged_in.get("/api/admin/export/applicants.csv").status_code == 200


def test_hard_delete_reports_and_removes_test_submissions(logged_in, paid, fake_minio):
    s, a = paid()
    student_id = s.id            # read it now: the object is gone after the delete
    pid = make_paper(logged_in, publish=True)
    logged_in.post(f"{URL}/{pid}/assign")
    r = logged_in.delete(f"/api/admin/students/{student_id}", json={"confirmation": "DELETE"})
    assert r.status_code == 200 and r.json["data"]["cascaded"]["test_submissions"] == 1
    assert TestSubmission.query.count() == 0 and db.session.get(Student, str(student_id)) is None
    assert TestPaper.query.count() == 1                      # the paper itself is not touched


# ------------------------------------------------------------------------ guards
def test_every_route_needs_an_admin_session(client):
    for method, path in (("get", ""), ("post", ""), ("get", "/p1"), ("put", "/p1"), ("delete", "/p1"),
                         ("post", "/p1/publish"), ("post", "/p1/assign"), ("get", "/p1/results"),
                         ("post", "/p1/reset/a1")):
        assert getattr(client, method)(URL + path).status_code == 401, (method, path)


# ------------------------------------------- marks limit (score column is NUMERIC(6,2))
@pytest.mark.parametrize("total", [10000, 20000, 2**31, 10**12])
def test_create_rejects_total_marks_above_the_score_limit(logged_in, total):
    r = logged_in.post(URL, json=paper_body(total_marks=total, pass_marks=1))
    assert r.status_code == 400 and r.json["success"] is False
    assert "from 1 to 9999" in r.json["error"], r.json
    assert TestPaper.query.count() == 0


def test_a_valid_paper_can_still_be_created(logged_in):
    r = logged_in.post(URL, json=paper_body())
    assert r.status_code == 201 and r.json["data"]["total_marks"] == 3


def test_the_largest_allowed_paper_cannot_overflow_the_score_column(logged_in, paid):
    """99 questions of 100 marks + one of 99 = 9999 = the cap. A perfect score must be storable."""
    qs = [question(i, correct="A", marks=100) for i in range(1, 100)] + [question(100, correct="A", marks=99)]
    pid = make_paper(logged_in, publish=True, total_marks=9999, pass_marks=5000, questions=qs)
    paid()
    logged_in.post(f"{URL}/{pid}/assign")
    paper = db.session.get(TestPaper, pid)
    perfect = test_service.grade(paper, {str(q.id): "A" for q in paper.questions})
    assert perfect == 9999
    sub = TestSubmission.query.one()
    sub.score = perfect                       # what the student side stores on submit
    db.session.commit()                       # raises if NUMERIC(6,2) cannot hold it
    db.session.refresh(sub)
    assert float(sub.score) == 9999.0


# ---------------------------------- audit first: a failed audit write changes nothing
def _audit_down():
    return mock.patch("app.services.admin_service.write_audit", side_effect=RuntimeError("audit down"))


def test_publish_is_not_applied_when_the_audit_entry_cannot_be_written(logged_in):
    pid = make_paper(logged_in)
    with _audit_down():
        r = logged_in.post(f"{URL}/{pid}/publish")
    assert r.status_code == 500 and r.json["success"] is False and "nothing was changed" in r.json["error"]
    db.session.expire_all()
    assert db.session.get(TestPaper, pid).is_published is False
    assert AuditLog.query.filter_by(action_type="TEST_PUBLISHED").count() == 0
    # once the audit log works again the same request succeeds, and is audited exactly once
    assert logged_in.post(f"{URL}/{pid}/publish").status_code == 200
    assert AuditLog.query.filter_by(action_type="TEST_PUBLISHED").count() == 1


def test_assign_is_not_applied_when_the_audit_entry_cannot_be_written(logged_in, paid):
    paid("A"); paid("B")
    pid = make_paper(logged_in, publish=True)
    with _audit_down():
        r = logged_in.post(f"{URL}/{pid}/assign", json={})
    assert r.status_code == 500 and r.json["success"] is False and "nothing was changed" in r.json["error"]
    db.session.expire_all()
    assert TestSubmission.query.count() == 0
    assert AuditLog.query.filter_by(action_type="TEST_ASSIGNED").count() == 0
    r = logged_in.post(f"{URL}/{pid}/assign", json={})
    assert r.status_code == 200 and r.json["data"]["assigned"] == 2
    assert AuditLog.query.filter_by(action_type="TEST_ASSIGNED").count() == 1


def test_reset_is_not_applied_when_the_audit_entry_cannot_be_written(logged_in, paid):
    pid = make_paper(logged_in, publish=True)
    _, a = paid("Retaker")
    logged_in.post(f"{URL}/{pid}/assign")
    sub = TestSubmission.query.one()
    sub.answers = {"x": "A"}
    _submit(sub, 2)
    with _audit_down():
        r = logged_in.post(f"{URL}/{pid}/reset/{a.id}")
    assert r.status_code == 500 and r.json["success"] is False and "nothing was changed" in r.json["error"]
    db.session.expire_all()
    sub = TestSubmission.query.one()
    assert sub.answers == {"x": "A"} and float(sub.score) == 2.0 and sub.submitted_at is not None
    assert AuditLog.query.filter_by(action_type="TEST_ATTEMPT_RESET").count() == 0


def test_a_failed_commit_is_recorded_as_failed_and_changes_nothing(logged_in):
    """Audit-first means the entry exists before the commit; if the commit then fails, a *_FAILED
    entry says so (the same approach as the hard delete), and the paper stays unpublished."""
    pid = make_paper(logged_in)
    with mock.patch.object(db.session, "commit", side_effect=RuntimeError("db down")):
        with pytest.raises(RuntimeError):
            logged_in.post(f"{URL}/{pid}/publish")
    db.session.rollback()
    assert db.session.get(TestPaper, pid).is_published is False
    assert AuditLog.query.filter_by(action_type="TEST_PUBLISHED_FAILED").count() == 1


def test_a_normal_publish_leaves_no_failed_entry(logged_in):
    make_paper(logged_in, publish=True)
    assert AuditLog.query.filter_by(action_type="TEST_PUBLISHED").count() == 1
    assert AuditLog.query.filter(AuditLog.action_type.like("%_FAILED")).count() == 0
