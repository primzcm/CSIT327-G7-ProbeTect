from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("lessons", "0002_lesson_classroom"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="lesson",
            name="scheduled_date",
        ),
    ]
