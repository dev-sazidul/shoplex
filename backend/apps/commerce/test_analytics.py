from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole

PASSWORD = "Safe-Local-Test_82!Password"


class ManagementOverviewTests(TestCase):
    def make_user(self, email, role_key):
        user = User.objects.create_user(email=email, password=PASSWORD, first_name="Test", status=User.Status.ACTIVE)
        UserRole.objects.create(user=user, role=Role.objects.get(key=role_key))
        return user

    def setUp(self):
        self.client = APIClient()

    def get_overview(self, user):
        self.client.force_authenticate(user)
        return self.client.get("/api/v1/management/overview/")

    def test_owner_receives_every_section(self):
        response = self.get_overview(self.make_user("owner@example.test", Role.Key.OWNER))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["operations"])
        self.assertIsNotNone(response.data["commerce"])
        self.assertEqual(len(response.data["commerce"]["daily"]), 14)
        self.assertEqual(response.data["users"]["by_role"]["owner"], 1)

    def test_admin_sees_operations_but_not_finance(self):
        response = self.get_overview(self.make_user("admin@example.test", Role.Key.ADMIN))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["operations"])
        self.assertIsNone(response.data["commerce"])
        self.assertIsNone(response.data["users"])

    def test_manager_receives_authorized_analytics(self):
        response = self.get_overview(self.make_user("manager@example.test", Role.Key.MANAGER))
        self.assertEqual(response.status_code, 200)
        self.assertIn("platform.analytics.read", response.data["viewer"]["permissions"])
        self.assertIsNotNone(response.data["commerce"])

    def test_customer_and_seller_are_denied(self):
        self.assertEqual(self.get_overview(self.make_user("customer@example.test", Role.Key.CUSTOMER)).status_code, 403)
        self.assertEqual(self.get_overview(self.make_user("seller@example.test", Role.Key.SELLER)).status_code, 403)

    def test_suspended_owner_is_denied(self):
        owner = self.make_user("suspended@example.test", Role.Key.OWNER)
        owner.status = User.Status.SUSPENDED
        owner.save(update_fields=["status"])
        self.client.force_authenticate(owner)
        self.assertIn(self.client.get("/api/v1/management/overview/").status_code, (401, 403))
