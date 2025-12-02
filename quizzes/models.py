from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string


class Quiz(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        ERROR = "error", "Error"
    
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quizzes")
    material = models.ForeignKey('materials.Material', on_delete=models.CASCADE, related_name="quizzes")
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    model_name = models.CharField(max_length=64, blank=True)
    question_count = models.PositiveIntegerField(default=0)
    timer_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Optional timer in minutes for the quiz")
    settings = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.title or f"Quiz for {self.material.title or 'material'}"


class QuizQuestion(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "multiple_choice", "Multiple Choice"
        TRUE_FALSE = "true_false", "True/False"
        FILL_IN_BLANK = "fill_in_blank", "Fill in the Blank"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.MULTIPLE_CHOICE)
    prompt = models.TextField()
    choices = models.JSONField(default=list, blank=True)
    correct_answer = models.CharField(max_length=255, blank=True)
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self) -> str:
        return self.prompt[:80]


class QuizShareLink(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="share_links",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_share_links",
    )
    token = models.CharField(max_length=32, unique=True, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):  # type: ignore[override]
        if not self.token:
            self.token = get_random_string(24)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Share link for {self.quiz}"


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    assignment = models.ForeignKey(
        "classrooms.QuizAssignment",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attempts",
    )
    share_link = models.ForeignKey(
        QuizShareLink,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attempts",
    )
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    answers = models.JSONField(default=dict, blank=True)
    attempts_used = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "user"],
                condition=models.Q(assignment__isnull=False),
                name="unique_assignment_attempt_per_user",
            ),
            models.UniqueConstraint(
                fields=["share_link", "user"],
                condition=models.Q(share_link__isnull=False),
                name="unique_share_link_attempt_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} on {self.quiz}"
