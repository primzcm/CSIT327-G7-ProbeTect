from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_bio_user_headline_user_profile_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="profile_photo_public_url",
            field=models.URLField(
                blank=True,
                null=True,
                help_text="Public Supabase URL for the user's profile photo.",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="profile_photo_storage_path",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=255,
                help_text="Supabase storage path for the user's profile photo.",
            ),
        ),
    ]
