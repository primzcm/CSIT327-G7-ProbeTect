from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quizzes", "0004_share_links_and_attempts"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizattempt",
            name="attempts_used",
            field=models.PositiveIntegerField(default=0),
        ),
    ]


