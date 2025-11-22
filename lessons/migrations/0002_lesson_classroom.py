from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("classrooms", "0001_initial"),
        ("lessons", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="lesson",
            name="classroom",
            field=models.ForeignKey(
                blank=True,
                help_text="Optional class to share this lesson with",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="lessons",
                to="classrooms.classroom",
            ),
        ),
    ]
