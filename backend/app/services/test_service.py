"""Aptitude test logic for the student side (SRD FR-10): grading and the server-side deadline.

The functions take plain objects (a paper with .questions, a submission row) and never touch the
database themselves; the caller commits.
"""
from datetime import timedelta


def grade(paper, answers) -> int:
    """Score saved answers {question_id: "A".."D"} against the paper: each correct answer earns its
    question's marks; wrong, missing or unknown answers earn nothing (no negative marking)."""
    answers = answers or {}
    score = 0
    for question in paper.questions:
        if answers.get(str(question.id)) == question.correct_option:
            score += question.marks
    return score


def deadline(submission, paper):
    """When the attempt closes: started_at + the paper's duration, or None if not started yet."""
    if submission.started_at is None:
        return None
    return submission.started_at + timedelta(minutes=paper.duration_minutes)


def status(submission) -> str:
    if submission.submitted_at is not None:
        return "SUBMITTED"
    if submission.started_at is not None:
        return "IN_PROGRESS"
    return "ASSIGNED"


def finalise_if_expired(submission, paper, now) -> bool:
    """Lazy submit: if time ran out on an unsubmitted attempt (the tab was closed, say), grade the
    saved answers and close it at the deadline. Returns True if it did."""
    closes = deadline(submission, paper)
    if submission.submitted_at is not None or closes is None or now < closes:
        return False
    submission.score = grade(paper, submission.answers)
    submission.submitted_at = closes
    return True
