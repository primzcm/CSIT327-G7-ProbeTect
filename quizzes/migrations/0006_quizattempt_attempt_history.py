from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quizzes", "0005_quizattempt_attempts_used"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizattempt",
            name="attempt_history",
            field=models.JSONField(default=list, blank=True),
        ),
    ]


