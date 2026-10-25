"""Grading and the server-side timer for the aptitude test (SRD FR-10). Pure Python: no database, no app."""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.test_service import deadline, finalise_if_expired, grade, status


def _q(qid, correct, marks=1):
    return SimpleNamespace(id=qid, correct_option=correct, marks=marks)


def _paper(*questions):
    return SimpleNamespace(questions=list(questions))


PAPER = _paper(_q("q1", "A"), _q("q2", "B", marks=2), _q("q3", "C", marks=3))


def test_all_correct_scores_the_sum_of_marks():
    assert grade(PAPER, {"q1": "A", "q2": "B", "q3": "C"}) == 6


def test_each_correct_answer_earns_its_own_marks():
    assert grade(PAPER, {"q1": "D", "q2": "B", "q3": "A"}) == 2


def test_wrong_answers_score_zero_and_are_not_negative():
    assert grade(PAPER, {"q1": "B", "q2": "C", "q3": "D"}) == 0


def test_unanswered_questions_score_zero():
    assert grade(PAPER, {"q3": "C"}) == 3


def test_no_answers_at_all_scores_zero():
    assert grade(PAPER, {}) == 0
    assert grade(PAPER, None) == 0


def test_answers_to_questions_not_on_the_paper_are_ignored():
    assert grade(PAPER, {"q1": "A", "other-paper-question": "A"}) == 1


def test_answer_must_match_exactly():
    # The save endpoint only stores "A".."D"; anything else is not a correct answer.
    assert grade(PAPER, {"q1": "a", "q2": " B", "q3": ["C"]}) == 0


def test_question_ids_are_compared_as_strings():
    paper = _paper(_q(7, "A"))
    assert grade(paper, {"7": "A"}) == 1


# --- the server's timer -----------------------------------------------------------------------

T0 = datetime(2026, 11, 1, 10, 0, 0)
TIMED = SimpleNamespace(duration_minutes=30, questions=PAPER.questions)


def _sub(started_at=None, submitted_at=None, answers=None, score=None):
    return SimpleNamespace(started_at=started_at, submitted_at=submitted_at, answers=answers or {}, score=score)


def test_deadline_is_start_plus_duration():
    assert deadline(_sub(started_at=T0), TIMED) == T0 + timedelta(minutes=30)


def test_no_deadline_before_the_test_is_started():
    assert deadline(_sub(), TIMED) is None


def test_status_follows_the_timestamps():
    assert status(_sub()) == "ASSIGNED"
    assert status(_sub(started_at=T0)) == "IN_PROGRESS"
    assert status(_sub(started_at=T0, submitted_at=T0)) == "SUBMITTED"


def test_expired_unsubmitted_test_is_graded_and_closed_at_the_deadline():
    sub = _sub(started_at=T0, answers={"q1": "A", "q2": "B"})
    assert finalise_if_expired(sub, TIMED, now=T0 + timedelta(minutes=31)) is True
    assert sub.score == 3
    assert sub.submitted_at == T0 + timedelta(minutes=30)


def test_test_still_inside_its_time_is_left_alone():
    sub = _sub(started_at=T0, answers={"q1": "A"})
    assert finalise_if_expired(sub, TIMED, now=T0 + timedelta(minutes=29)) is False
    assert sub.score is None and sub.submitted_at is None


def test_unstarted_or_already_submitted_tests_are_left_alone():
    later = T0 + timedelta(days=1)
    assert finalise_if_expired(_sub(), TIMED, now=later) is False
    done = _sub(started_at=T0, submitted_at=T0 + timedelta(minutes=5), score=1)
    assert finalise_if_expired(done, TIMED, now=later) is False
    assert done.score == 1 and done.submitted_at == T0 + timedelta(minutes=5)
