from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Distinguishes permissions for students vs instructors."
    )
    headline = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional short descriptor that surfaces on dashboards."
    )
    bio = models.TextField(
        blank=True,
        help_text="Longer context that appears on the profile."
    )
    profile_photo = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        help_text="Optional profile photo used across the UI."
    )

    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    def is_instructor(self) -> bool:
        return self.role == self.Role.INSTRUCTOR
