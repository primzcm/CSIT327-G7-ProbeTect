from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

User = get_user_model()


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="janedoe",
            email="jane@example.com",
            password="strong-pass-123",
        )

    def test_redirects_anonymous_users(self):
        response = self.client.get(reverse("profile"))
        expected_url = f"{reverse('login')}?next={reverse('profile')}"
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_updates_profile_details(self):
        self.client.login(username="janedoe", password="strong-pass-123")
        response = self.client.post(
            reverse("profile"),
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "updated@example.com",
            },
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.last_name, "Doe")
        self.assertEqual(self.user.email, "updated@example.com")
