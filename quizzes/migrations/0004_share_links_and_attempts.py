from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("classrooms", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("quizzes", "0003_quiz_timer_minutes"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuizShareLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(editable=False, max_length=32, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quiz_share_links", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "quiz",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="share_links", to="quizzes.quiz"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="QuizAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveIntegerField(default=0)),
                ("total_questions", models.PositiveIntegerField(default=0)),
                ("percent", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("answers", models.JSONField(blank=True, default=dict)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assignment",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="classrooms.quizassignment"),
                ),
                (
                    "quiz",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="quizzes.quiz"),
                ),
                (
                    "share_link",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="attempts", to="quizzes.quizsharelink"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quiz_attempts", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="quizattempt",
            constraint=models.UniqueConstraint(condition=models.Q(("assignment__isnull", False)), fields=("assignment", "user"), name="unique_assignment_attempt_per_user"),
        ),
        migrations.AddConstraint(
            model_name="quizattempt",
            constraint=models.UniqueConstraint(condition=models.Q(("share_link__isnull", False)), fields=("share_link", "user"), name="unique_share_link_attempt_per_user"),
        ),
    ]
