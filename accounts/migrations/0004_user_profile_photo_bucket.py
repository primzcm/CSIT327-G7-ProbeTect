from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_user_supabase_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="profile_photo_bucket",
            field=models.CharField(
                max_length=120,
                blank=True,
                null=True,
                help_text="Supabase bucket storing the user's profile photo.",
            ),
        ),
    ]
