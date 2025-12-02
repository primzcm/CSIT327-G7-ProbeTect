from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string


def _generate_code(length: int = 6) -> str:
    """Generate a short, human-friendly join code."""
    return get_random_string(length=length).upper()


class Classroom(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classrooms",
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=12, unique=True, editable=False)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.code:
            # Try a few times to avoid collisions before falling back to a longer code.
            for length in (6, 7, 8, 10):
                candidate = _generate_code(length)
                if not Classroom.objects.filter(code=candidate).exists():
                    self.code = candidate
                    break
            if not self.code:
                self.code = _generate_code(12)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ClassroomMembership(models.Model):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="classroom_memberships",
    )
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("classroom", "user")
        ordering = ["-joined_at"]

    def __str__(self) -> str:
        return f"{self.user} in {self.classroom}"


class QuizAssignment(models.Model):
    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    quiz = models.ForeignKey(
        "quizzes.Quiz",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_assignments",
    )
    title = models.CharField(max_length=255, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum attempts per student (leave blank for 1 attempt).",
    )
    show_answers = models.BooleanField(
        default=True,
        help_text="Show correct answers after submission.",
    )
    allow_review = models.BooleanField(
        default=True,
        help_text="Let students review questions and their answers after submission.",
    )
    delay_score_until_due = models.BooleanField(
        default=False,
        help_text="If enabled, students only see their score after the quiz closes (after the due date).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or f"{self.quiz} for {self.classroom}"
