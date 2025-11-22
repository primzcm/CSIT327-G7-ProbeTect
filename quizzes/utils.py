from __future__ import annotations

from typing import Iterable

from .models import QuizQuestion


def grade_quiz_submission(
    questions: Iterable[QuizQuestion],
    data: dict[str, str],
) -> tuple[list[dict], int, int, float]:
    """
    Grade user answers against the provided questions.

    Returns a tuple of (entries, score, total, percent).
    Each entry contains the question and a result mapping with the user's answer and correctness.
    """
    entries: list[dict] = []
    score = 0

    for question in questions:
        field_name = f"q_{question.id}"
        user_answer = (data.get(field_name) or "").strip()
        correct_answer = (question.correct_answer or "").strip()

        if question.choices:
            is_correct = user_answer == correct_answer
        else:
            is_correct = (
                user_answer.lower() == correct_answer.lower()
                if user_answer and correct_answer
                else False
            )

        if is_correct:
            score += 1

        entries.append(
            {
                "question": question,
                "result": {
                    "user_answer": user_answer,
                    "correct": is_correct,
                },
            }
        )

    total = len(entries) or 1
    percent = round((score / total) * 100, 1)
    return entries, score, total, percent
