"""Grading for the aptitude test (SRD FR-10). Pure Python: no database, no app."""
from types import SimpleNamespace

from app.services.test_service import grade


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
