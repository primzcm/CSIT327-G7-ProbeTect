from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("quizzes", "0003_quiz_timer_minutes"),
    ]

    operations = [
        migrations.CreateModel(
            name="Classroom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("code", models.CharField(editable=False, max_length=12, unique=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="classrooms", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ClassroomMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("student", "Student"), ("instructor", "Instructor")], default="student", max_length=16)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "classroom",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="classrooms.classroom"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="classroom_memberships", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-joined_at"],
                "unique_together": {("classroom", "user")},
            },
        ),
        migrations.CreateModel(
            name="QuizAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=255)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("show_answers", models.BooleanField(default=True, help_text="Show correct answers after submission.")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "classroom",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="classrooms.classroom"),
                ),
                (
                    "created_by",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quiz_assignments", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "quiz",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="quizzes.quiz"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
