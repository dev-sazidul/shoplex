from django.core.cache import cache
from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.platform.models import AuthSession


class AuthenticationAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="member@example.test",
            password="Safe-Local-Test_82!Password",
            first_name="Casey",
            status=User.Status.ACTIVE,
        )

    def test_registration_requires_email_verification_before_login(self):
        response = self.client.post("/api/v1/auth/register/", {
            "email": "new-member@example.test",
            "first_name": "Taylor",
            "password": "New-Account-Pass_940!",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(email="new-member@example.test").status, User.Status.PENDING)
        self.assertEqual(len(mail.outbox), 1)

        token = mail.outbox[0].body.split(": ")[-1].strip()
        verify = self.client.post("/api/v1/auth/verify-email/", {"token": token})
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(User.objects.get(email="new-member@example.test").status, User.Status.ACTIVE)

    def test_login_creates_tracked_session_and_logout_revokes_access(self):
        login = self.client.post("/api/v1/auth/login/", {
            "email": self.user.email,
            "password": "Safe-Local-Test_82!Password",
        })
        self.assertEqual(login.status_code, 200, login.data)
        self.assertEqual(AuthSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 200)

        logout = self.client.post("/api/v1/auth/logout/", {})
        self.assertEqual(logout.status_code, 204)
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)

    def test_refresh_rotates_and_rejects_old_token(self):
        login = self.client.post("/api/v1/auth/login/", {
            "email": self.user.email,
            "password": "Safe-Local-Test_82!Password",
        })
        old_refresh = login.data["refresh"]
        refreshed = self.client.post("/api/v1/auth/refresh/", {"refresh": old_refresh})
        self.assertEqual(refreshed.status_code, 200, refreshed.data)
        self.assertNotEqual(refreshed.data["refresh"], old_refresh)
        replay = self.client.post("/api/v1/auth/refresh/", {"refresh": old_refresh})
        self.assertEqual(replay.status_code, 401)

    def test_suspended_account_cannot_use_an_existing_access_token(self):
        login = self.client.post("/api/v1/auth/login/", {
            "email": self.user.email,
            "password": "Safe-Local-Test_82!Password",
        })
        self.user.status = User.Status.SUSPENDED
        self.user.save(update_fields=["status"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)

    def test_suspended_account_cannot_refresh(self):
        login = self.client.post("/api/v1/auth/login/", {
            "email": self.user.email,
            "password": "Safe-Local-Test_82!Password",
        })
        self.user.status = User.Status.SUSPENDED
        self.user.save(update_fields=["status"])
        response = self.client.post("/api/v1/auth/refresh/", {"refresh": login.data["refresh"]})
        self.assertEqual(response.status_code, 401)

    def test_logout_cannot_revoke_another_users_refresh_token(self):
        other = User.objects.create_user(
            email="other@example.test",
            password="Safe-Local-Test_82!Password",
            first_name="Other",
            status=User.Status.ACTIVE,
        )
        own_login = self.client.post("/api/v1/auth/login/", {
            "email": self.user.email,
            "password": "Safe-Local-Test_82!Password",
        })
        other_login = self.client.post("/api/v1/auth/login/", {
            "email": other.email,
            "password": "Safe-Local-Test_82!Password",
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {own_login.data['access']}")
        self.assertEqual(self.client.post("/api/v1/auth/logout/", {"refresh": other_login.data["refresh"]}).status_code, 204)
        response = self.client.post("/api/v1/auth/refresh/", {"refresh": other_login.data["refresh"]})
        self.assertEqual(response.status_code, 200, response.data)
