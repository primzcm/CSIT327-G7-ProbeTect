import shutil
import tempfile
from unittest import mock
from io import BytesIO

from PIL import Image
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
        buffer = BytesIO()
        Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(buffer, format="PNG")
        return buffer.getvalue()

    def _tiny_jpeg(self) -> bytes:
        buffer = BytesIO()
        Image.new("RGB", (1, 1), (255, 255, 255)).save(buffer, format="JPEG")
        return buffer.getvalue()

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

    @mock.patch("materials.supabase.upload_file")
    @mock.patch("materials.supabase.delete_file")
    def test_profile_photo_upload_succeeds(self, delete_file_mock, upload_file_mock):
        upload_file_mock.return_value = ("avatars/1/abc.png", "https://supabase.test/public/avatars/1/abc.png")
        photo = SimpleUploadedFile("avatar.png", self._tiny_png(), content_type="image/png")

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

        upload_file_mock.assert_called_once()
        delete_file_mock.assert_not_called()
        self.assertEqual(updated.profile_photo_storage_path, "avatars/1/abc.png")
        self.assertEqual(updated.profile_photo_public_url, "https://supabase.test/public/avatars/1/abc.png")
        self.assertFalse(updated.profile_photo)

    @mock.patch("materials.supabase.upload_file")
    @mock.patch("materials.supabase.delete_file")
    def test_profile_photo_replaces_existing_supabase_asset(self, delete_file_mock, upload_file_mock):
        self.user.profile_photo_storage_path = "avatars/1/old.png"
        self.user.profile_photo_public_url = "https://supabase.test/public/avatars/1/old.png"
        self.user.save()

        upload_file_mock.return_value = ("avatars/1/new.png", "https://supabase.test/public/avatars/1/new.png")
        photo = SimpleUploadedFile("avatar.png", self._tiny_png(), content_type="image/png")

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

        upload_file_mock.assert_called_once()
        delete_file_mock.assert_called_once_with("avatars/1/old.png", bucket_override=None)
        self.assertEqual(updated.profile_photo_storage_path, "avatars/1/new.png")
        self.assertEqual(updated.profile_photo_public_url, "https://supabase.test/public/avatars/1/new.png")

    @mock.patch("materials.supabase.upload_file")
    @mock.patch("materials.supabase.delete_file")
    def test_profile_photo_jpeg_is_converted_to_png(self, delete_file_mock, upload_file_mock):
        upload_file_mock.return_value = ("avatars/1/abc.png", "https://supabase.test/public/avatars/1/abc.png")
        photo = SimpleUploadedFile("avatar.jpg", self._tiny_jpeg(), content_type="image/jpeg")

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

        upload_file_mock.assert_called_once()
        sent_file = upload_file_mock.call_args[0][0]
        self.assertEqual(sent_file.content_type, "image/png")
        self.assertTrue(sent_file.name.endswith(".png"))
        self.assertEqual(updated.profile_photo_public_url, "https://supabase.test/public/avatars/1/abc.png")

    @mock.patch("materials.supabase.upload_file")
    @mock.patch("materials.supabase.delete_file")
    def test_profile_photo_can_be_removed(self, delete_file_mock, upload_file_mock):
        self.user.profile_photo_storage_path = "avatars/1/old.png"
        self.user.profile_photo_public_url = "https://supabase.test/public/avatars/1/old.png"
        self.user.profile_photo_bucket = "avatars"
        self.user.save()

        form = UserProfileForm(
            data={
                "first_name": "Demo",
                "last_name": "User",
                "username": "demo",
                "email": "demo@example.com",
                "remove_profile_photo": True,
            },
            instance=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()

        upload_file_mock.assert_not_called()
        delete_file_mock.assert_called_once_with("avatars/1/old.png", bucket_override="avatars")
        self.assertIsNone(updated.profile_photo_storage_path)
        self.assertIsNone(updated.profile_photo_public_url)
        self.assertIsNone(updated.profile_photo_bucket)
        self.assertFalse(bool(updated.profile_photo))

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
