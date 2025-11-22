from __future__ import annotations

from django.conf import settings
from django.db import models


class Lesson(models.Model):
    """Lesson entry model for educators to plan and organize lessons."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lessons")
    classroom = models.ForeignKey(
        'classrooms.Classroom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
        help_text="Optional class to share this lesson with",
    )
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    content = models.TextField(help_text="Lesson content, notes, or plan")
    material = models.ForeignKey('materials.Material', on_delete=models.SET_NULL, null=True, blank=True, related_name="lessons", help_text="Optional associated material")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"

    def __str__(self) -> str:
        return self.title
