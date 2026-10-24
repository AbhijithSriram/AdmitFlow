"""Aptitude test logic for the student side (SRD FR-10): grading, and later the deadline rules."""


def grade(paper, answers) -> int:
    """Score saved answers {question_id: "A".."D"} against the paper: each correct answer earns its
    question's marks; wrong, missing or unknown answers earn nothing (no negative marking)."""
    answers = answers or {}
    score = 0
    for question in paper.questions:
        if answers.get(str(question.id)) == question.correct_option:
            # `marks` arrives with migration 005; until then every question is worth 1.
            score += getattr(question, "marks", 1)
    return score
