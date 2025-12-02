from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classrooms", "0002_quizassignment_max_attempts"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizassignment",
            name="allow_review",
            field=models.BooleanField(
                default=True,
                help_text="Let students review questions and their answers after submission.",
            ),
        ),
    ]


