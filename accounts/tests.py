import base64
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .forms import UserProfileForm
from .models import User


class UserProfileFormTests(TestCase):
    """Covers optional fields and photo validation on the profile form."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._temp_media)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls._temp_media, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user(
            username="demo",
            email="demo@example.com",
            password="secure-pass-123",
        )

    def _tiny_png(self) -> bytes:
        """Returns a 1x1 transparent PNG payload."""
        return base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=")

    def test_optional_fields_can_save(self):
        form = UserProfileForm(
            data={
                "first_name": "Demo",
                "last_name": "User",
                "username": "demo",
                "email": "demo@example.com",
                "headline": "Anatomy major",
                "bio": "Focuses on cardio-respiratory practice sets.",
            },
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.headline, "Anatomy major")
        self.assertIn("cardio-respiratory", updated.bio)

    def test_profile_photo_upload_succeeds(self):
        photo = SimpleUploadedFile(
            "avatar.png",
            self._tiny_png(),
            content_type="image/png",
        )
        form = UserProfileForm(
            data={
                "first_name": "Demo",
                "last_name": "User",
                "username": "demo",
                "email": "demo@example.com",
            },
            files={"profile_photo": photo},
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertTrue(updated.profile_photo.name.endswith(".png"))

    def test_profile_photo_rejects_large_files(self):
        too_big = SimpleUploadedFile("huge.png", b"0" * (6 * 1024 * 1024), content_type="image/png")
        form = UserProfileForm(
            data={
                "first_name": "Demo",
                "last_name": "User",
                "username": "demo",
                "email": "demo@example.com",
            },
            files={"profile_photo": too_big},
            instance=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("profile_photo", form.errors)
