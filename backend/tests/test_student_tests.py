"""Student side of the aptitude test (SRD FR-10): listing assigned tests and starting one.
The timer is the server's: start sets started_at once, and the deadline is computed from it."""
import json
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def sign_in(client):
    def _sign_in(student):
        with client.session_transaction() as sess:
            sess["student_id"] = student.id
        return client
    return _sign_in


@pytest.fixture
def make_paper(app, admin):
    from app.extensions import db
    from app.models import TestPaper, TestQuestion

    def _make(title="Aptitude 1", published=True, duration=30, answers=(("A", 1), ("B", 2))):
        paper = TestPaper(title=title, duration_minutes=duration, total_marks=sum(m for _, m in answers),
                          pass_marks=1, created_by=admin.id, is_published=published)
        for i, (correct, marks) in enumerate(answers, 1):
            paper.questions.append(TestQuestion(
                question_text=f"Question {i}?", option_a="one", option_b="two", option_c="three",
                option_d="four", correct_option=correct, marks=marks))
        db.session.add(paper)
        db.session.commit()
        return paper
    return _make


@pytest.fixture
def assign(app):
    from app.extensions import db
    from app.models import Application, TestSubmission

    def _assign(student, paper, **fields):
        application = Application.query.filter_by(student_id=student.id).one()
        sub = TestSubmission(application_id=application.id, test_paper_id=paper.id, **fields)
        db.session.add(sub)
        db.session.commit()
        return sub
    return _assign


@pytest.fixture
def paid(make_student):
    return make_student(status="PAID")


def _start(client, paper_id):
    return client.post(f"/api/student/tests/{paper_id}/start")


def _reload(sub):
    from app.extensions import db
    db.session.expire_all()
    return db.session.get(type(sub), sub.id)


# --- GET /api/student/tests -------------------------------------------------------------------

def test_list_is_only_for_paid_applicants(make_student, sign_in):
    client = sign_in(make_student(status="PAYMENT_PENDING"))
    r = client.get("/api/student/tests")
    assert r.status_code == 403 and r.json["success"] is False


def test_list_is_empty_without_assignments(paid, sign_in):
    r = sign_in(paid).get("/api/student/tests")
    assert r.status_code == 200 and r.json == {"success": True, "data": {"tests": []}}


def test_list_shows_an_assigned_test(paid, sign_in, make_paper, assign):
    paper = make_paper()
    assign(paid, paper)
    tests = sign_in(paid).get("/api/student/tests").json["data"]["tests"]
    assert tests == [{"paper_id": str(paper.id), "title": "Aptitude 1", "duration_minutes": 30,
                      "question_count": 2, "status": "ASSIGNED", "deadline": None}]


def test_list_does_not_show_other_students_tests(paid, make_student, sign_in, make_paper, assign):
    assign(make_student(status="PAID"), make_paper())
    assert sign_in(paid).get("/api/student/tests").json["data"]["tests"] == []


def test_list_hides_unpublished_papers(paid, sign_in, make_paper, assign):
    assign(paid, make_paper(published=False))
    assert sign_in(paid).get("/api/student/tests").json["data"]["tests"] == []


def test_list_shows_in_progress_with_its_deadline(paid, sign_in, make_paper, assign):
    paper = make_paper()
    client = sign_in(paid)
    assign(paid, paper)
    deadline = _start(client, paper.id).json["data"]["deadline"]
    [test] = client.get("/api/student/tests").json["data"]["tests"]
    assert test["status"] == "IN_PROGRESS" and test["deadline"] == deadline


def test_list_never_reveals_the_score(paid, sign_in, make_paper, assign):
    now = datetime.utcnow()
    assign(paid, make_paper(), started_at=now, submitted_at=now, score=3)
    [test] = sign_in(paid).get("/api/student/tests").json["data"]["tests"]
    assert test["status"] == "SUBMITTED" and "score" not in test


def test_list_grades_an_attempt_whose_time_ran_out(paid, sign_in, make_paper, assign):
    paper = make_paper(duration=30)
    started = datetime.utcnow() - timedelta(minutes=45)
    sub = assign(paid, paper, started_at=started, answers={str(paper.questions[1].id): "B"})
    [test] = sign_in(paid).get("/api/student/tests").json["data"]["tests"]
    assert test["status"] == "SUBMITTED"
    sub = _reload(sub)
    assert sub.score == 2 and sub.submitted_at == started + timedelta(minutes=30)


# --- POST /api/student/tests/:paper_id/start --------------------------------------------------

def test_start_returns_questions_and_a_server_deadline(paid, sign_in, make_paper, assign):
    paper = make_paper(duration=30)
    assign(paid, paper)
    before = datetime.utcnow()
    r = _start(sign_in(paid), paper.id)
    assert r.status_code == 200
    data = r.json["data"]
    assert data["paper"] == {"id": str(paper.id), "title": "Aptitude 1", "duration_minutes": 30}
    assert [q["id"] for q in data["questions"]] == sorted(str(q.id) for q in paper.questions)
    assert data["questions"][0]["options"] == {"A": "one", "B": "two", "C": "three", "D": "four"}
    assert data["answers"] == {}
    deadline = datetime.fromisoformat(data["deadline"].rstrip("Z"))
    assert before + timedelta(minutes=30) <= deadline <= datetime.utcnow() + timedelta(minutes=30)
    assert data["deadline"].endswith("Z")
    assert 29 * 60 <= data["seconds_left"] <= 30 * 60


def test_start_never_reveals_correct_answers(paid, sign_in, make_paper, assign):
    paper = make_paper()
    assign(paid, paper)
    body = json.dumps(_start(sign_in(paid), paper.id).json)
    assert "correct" not in body and "marks" not in body


def test_start_is_idempotent(paid, sign_in, make_paper, assign):
    paper = make_paper()
    sub = assign(paid, paper)
    client = sign_in(paid)
    first = _start(client, paper.id).json["data"]
    started_at = _reload(sub).started_at
    second = _start(client, paper.id).json["data"]
    assert second["deadline"] == first["deadline"]
    assert _reload(sub).started_at == started_at


def test_start_returns_saved_answers_so_a_refresh_resumes(paid, sign_in, make_paper, assign):
    paper = make_paper()
    qid = str(paper.questions[0].id)
    assign(paid, paper, started_at=datetime.utcnow(), answers={qid: "C"})
    assert _start(sign_in(paid), paper.id).json["data"]["answers"] == {qid: "C"}


def test_start_unassigned_test_is_404(paid, make_student, sign_in, make_paper, assign):
    paper = make_paper()
    assign(make_student(status="PAID"), paper)
    assert _start(sign_in(paid), paper.id).status_code == 404


def test_start_with_a_malformed_id_is_404(paid, sign_in):
    assert _start(sign_in(paid), "not-a-uuid").status_code == 404


def test_start_unpublished_paper_is_404(paid, sign_in, make_paper, assign):
    paper = make_paper(published=False)
    assign(paid, paper)
    assert _start(sign_in(paid), paper.id).status_code == 404


def test_start_is_only_for_paid_applicants(make_student, sign_in, make_paper, assign):
    student = make_student(status="PAYMENT_PENDING")
    paper = make_paper()
    assign(student, paper)
    assert _start(sign_in(student), paper.id).status_code == 403


def test_start_after_submitting_is_409(paid, sign_in, make_paper, assign):
    paper = make_paper()
    now = datetime.utcnow()
    assign(paid, paper, started_at=now, submitted_at=now, score=0)
    r = _start(sign_in(paid), paper.id)
    assert r.status_code == 409 and "questions" not in json.dumps(r.json)


def test_start_after_the_deadline_grades_and_refuses(paid, sign_in, make_paper, assign):
    paper = make_paper(duration=30)
    sub = assign(paid, paper, started_at=datetime.utcnow() - timedelta(hours=1),
                 answers={str(paper.questions[0].id): "A"})
    assert _start(sign_in(paid), paper.id).status_code == 409
    assert _reload(sub).score == 1


# --- PUT /api/student/tests/:paper_id/answers -------------------------------------------------

def _save(client, paper_id, answers):
    return client.put(f"/api/student/tests/{paper_id}/answers", json={"answers": answers})


@pytest.fixture
def started(paid, make_paper, assign):
    """A paid applicant's paper, started a minute ago (30 minutes long): (paper, submission, q1, q2)."""
    paper = make_paper(duration=30)
    sub = assign(paid, paper, started_at=datetime.utcnow() - timedelta(minutes=1))
    q1, q2 = sorted(str(q.id) for q in paper.questions)
    return paper, sub, q1, q2


def test_save_stores_a_pick(paid, sign_in, started):
    paper, sub, q1, _ = started
    r = _save(sign_in(paid), paper.id, {q1: "C"})
    assert r.status_code == 200
    assert r.json["data"]["answers"] == {q1: "C"}
    assert 28 * 60 <= r.json["data"]["seconds_left"] <= 29 * 60
    assert _reload(sub).answers == {q1: "C"}


def test_each_save_merges_with_earlier_picks(paid, sign_in, started):
    paper, sub, q1, q2 = started
    client = sign_in(paid)
    _save(client, paper.id, {q1: "A"})
    _save(client, paper.id, {q2: "D"})
    assert _reload(sub).answers == {q1: "A", q2: "D"}


def test_a_later_pick_replaces_the_earlier_one(paid, sign_in, started):
    paper, sub, q1, _ = started
    client = sign_in(paid)
    _save(client, paper.id, {q1: "A"})
    _save(client, paper.id, {q1: "B"})
    assert _reload(sub).answers == {q1: "B"}


def test_question_ids_not_on_the_paper_are_ignored(paid, sign_in, started, make_paper):
    paper, sub, q1, _ = started
    other_question = str(make_paper(title="Other").questions[0].id)
    r = _save(sign_in(paid), paper.id, {q1: "A", other_question: "B", "made-up": "C"})
    assert r.status_code == 200 and r.json["data"]["answers"] == {q1: "A"}
    assert _reload(sub).answers == {q1: "A"}


@pytest.mark.parametrize("bad", ["E", "a", "", None, 1, ["A"]])
def test_an_option_other_than_a_to_d_is_400_and_nothing_is_saved(paid, sign_in, started, bad):
    paper, sub, q1, q2 = started
    r = _save(sign_in(paid), paper.id, {q1: "A", q2: bad})
    assert r.status_code == 400 and r.json["success"] is False
    assert _reload(sub).answers == {}


@pytest.mark.parametrize("body", [None, {}, {"answers": ["A"]}, {"answers": "A"}])
def test_a_body_without_an_answers_object_is_400(paid, sign_in, started, body):
    paper, *_ = started
    r = sign_in(paid).put(f"/api/student/tests/{paper.id}/answers", json=body)
    assert r.status_code == 400


def test_save_after_the_deadline_is_refused_and_the_attempt_is_graded(paid, sign_in, make_paper, assign):
    paper = make_paper(duration=30)
    q1 = str(paper.questions[0].id)
    sub = assign(paid, paper, started_at=datetime.utcnow() - timedelta(minutes=31), answers={q1: "A"})
    r = _save(sign_in(paid), paper.id, {q1: "B"})
    assert r.status_code == 409
    sub = _reload(sub)
    assert sub.answers == {q1: "A"} and sub.score == 1 and sub.submitted_at is not None


def test_save_after_submitting_is_refused(paid, sign_in, make_paper, assign):
    paper = make_paper()
    q1 = str(paper.questions[0].id)
    now = datetime.utcnow()
    sub = assign(paid, paper, started_at=now, submitted_at=now, score=0, answers={q1: "D"})
    assert _save(sign_in(paid), paper.id, {q1: "A"}).status_code == 409
    assert _reload(sub).answers == {q1: "D"}


def test_save_before_starting_is_refused(paid, sign_in, make_paper, assign):
    paper = make_paper()
    sub = assign(paid, paper)
    assert _save(sign_in(paid), paper.id, {str(paper.questions[0].id): "A"}).status_code == 409
    assert _reload(sub).answers == {}


def test_save_to_an_unassigned_test_is_404(paid, make_student, sign_in, make_paper, assign):
    paper = make_paper()
    assign(make_student(status="PAID"), paper, started_at=datetime.utcnow())
    assert _save(sign_in(paid), paper.id, {str(paper.questions[0].id): "A"}).status_code == 404


def test_save_with_a_malformed_id_is_404(paid, sign_in):
    assert _save(sign_in(paid), "not-a-uuid", {}).status_code == 404


def test_save_to_an_unpublished_paper_is_404(paid, sign_in, make_paper, assign):
    paper = make_paper(published=False)
    assign(paid, paper, started_at=datetime.utcnow())
    assert _save(sign_in(paid), paper.id, {str(paper.questions[0].id): "A"}).status_code == 404


def test_save_is_only_for_paid_applicants(make_student, sign_in, make_paper, assign):
    student = make_student(status="PAYMENT_PENDING")
    paper = make_paper()
    assign(student, paper, started_at=datetime.utcnow())
    assert _save(sign_in(student), paper.id, {str(paper.questions[0].id): "A"}).status_code == 403
