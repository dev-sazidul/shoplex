from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Permission, Role, RolePermission, UserRole
from apps.platform.models import Notification


class AuthorizationAPITests(TestCase):
    def setUp(self):
        customer_role = Role.objects.get(key=Role.Key.CUSTOMER)
        self.customer = User.objects.create_user(
            email="customer@example.test",
            password="Safe-Local-Test_82!Password",
            first_name="Jamie",
            status=User.Status.ACTIVE,
        )
        UserRole.objects.create(user=self.customer, role=customer_role)
        owner_role = Role.objects.get(key=Role.Key.OWNER)
        role_permission = Permission.objects.get(key="authorization.roles.read")
        RolePermission.objects.get_or_create(role=owner_role, permission=role_permission)
        self.owner = User.objects.create_user(
            email="owner@example.test",
            password="Safe-Local-Test_82!Password",
            first_name="Morgan",
            status=User.Status.ACTIVE,
        )
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.client = APIClient()

    def test_customer_cannot_read_privileged_role_data(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/v1/roles/").status_code, 403)

    def test_owner_with_permission_can_read_role_data(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get("/api/v1/roles/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 5)

    def test_notifications_are_scoped_to_authenticated_user(self):
        other = User.objects.create_user(
            email="other@example.test",
            password="Safe-Local-Test_82!Password",
            first_name="Alex",
            status=User.Status.ACTIVE,
        )
        Notification.objects.create(user=self.customer, category="account", title="Your notice")
        Notification.objects.create(user=other, category="account", title="Private notice")
        self.client.force_authenticate(self.customer)
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["title"] for item in response.data["results"]], ["Your notice"])
