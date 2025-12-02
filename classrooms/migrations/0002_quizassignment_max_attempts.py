from __future__ import annotations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("classrooms", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="quizassignment",
            name="max_attempts",
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                help_text="Maximum attempts per student (leave blank for 1 attempt).",
            ),
        ),
    ]


