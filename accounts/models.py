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
    profile_photo_public_url = models.URLField(
        blank=True,
        null=True,
        help_text="Public Supabase URL for the user's profile photo."
    )
    profile_photo_storage_path = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Supabase storage path for the user's profile photo."
    )
    profile_photo_bucket = models.CharField(
        max_length=120,
        blank=True,
        null=True,
        help_text="Supabase bucket storing the user's profile photo."
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

    @property
    def profile_photo_url(self) -> str | None:
        """Return the Supabase URL if set, otherwise fall back to the local file URL."""
        if self.profile_photo_public_url:
            return self.profile_photo_public_url
        if self.profile_photo:
            try:
                return self.profile_photo.url
            except ValueError:
                return None
        return None
