from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classrooms", "0003_quizassignment_allow_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizassignment",
            name="delay_score_until_due",
            field=models.BooleanField(
                default=False,
                help_text="If enabled, students only see their score after the quiz closes (after the due date).",
            ),
        ),
    ]


