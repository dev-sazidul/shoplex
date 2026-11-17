from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.platform.models import SellerApplication, SellerApplicationApproval, SellerProfile


PASSWORD = "Phase-Two-Test_Password-290!"


def create_user(email, role_key):
    user = User.objects.create_user(email=email, password=PASSWORD, first_name=email.split("@")[0], status=User.Status.ACTIVE)
    role = Role.objects.get(key=role_key)
    UserRole.objects.create(user=user, role=role)
    return user


class SellerApplicationWorkflowTests(TestCase):
    def setUp(self):
        self.customer = create_user("apply@example.test", Role.Key.CUSTOMER)
        self.admin = create_user("admin@example.test", Role.Key.ADMIN)
        self.owner = create_user("owner@example.test", Role.Key.OWNER)
        self.client = APIClient()

    def submit_application(self):
        self.client.force_authenticate(self.customer)
        return self.client.post("/api/v1/seller/application/", {
            "business_name": "Northline Goods",
            "business_type": "Retail",
            "business_address": "14 Market Street, Dhaka",
            "business_phone": "+8801700000000",
            "verification_reference": "TRADE-4821",
            "store_description": "Independent home and living store.",
        }, format="json")

    def review(self, reviewer, application_id, decision, reason=""):
        self.client.force_authenticate(reviewer)
        return self.client.post(f"/api/v1/management/seller-applications/{application_id}/review/", {"decision": decision, "reason": reason}, format="json")

    def test_seller_activation_requires_both_independent_approvals(self):
        submitted = self.submit_application()
        self.assertEqual(submitted.status_code, 201, submitted.data)
        application_id = submitted.data["id"]
        profile = SellerProfile.objects.get(user=self.customer)
        self.assertFalse(profile.is_active)

        admin_decision = self.review(self.admin, application_id, SellerApplicationApproval.Decision.APPROVED)
        self.assertEqual(admin_decision.status_code, 200, admin_decision.data)
        profile.refresh_from_db()
        self.assertFalse(profile.is_active)
        self.assertEqual(admin_decision.data["status"], SellerApplication.Status.PENDING)

        owner_decision = self.review(self.owner, application_id, SellerApplicationApproval.Decision.APPROVED)
        self.assertEqual(owner_decision.status_code, 200, owner_decision.data)
        profile.refresh_from_db()
        self.assertTrue(profile.is_active)
        self.assertTrue(self.customer.role_assignments.filter(role__key=Role.Key.SELLER).exists())
        self.assertEqual(owner_decision.data["status"], SellerApplication.Status.APPROVED)

    def test_rejection_by_either_reviewer_keeps_seller_inactive(self):
        submitted = self.submit_application()
        self.assertEqual(submitted.status_code, 201)
        response = self.review(self.admin, submitted.data["id"], SellerApplicationApproval.Decision.REJECTED, "Business documents could not be verified.")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], SellerApplication.Status.REJECTED)
        self.assertFalse(SellerProfile.objects.get(user=self.customer).is_active)
        self.assertFalse(self.customer.role_assignments.filter(role__key=Role.Key.SELLER).exists())

    def test_requested_information_starts_a_new_review_cycle(self):
        submitted = self.submit_application()
        self.review(self.admin, submitted.data["id"], SellerApplicationApproval.Decision.NEEDS_INFO, "Please provide a current license.")
        self.client.force_authenticate(self.customer)
        resubmitted = self.client.post("/api/v1/seller/application/", {
            "business_name": "Northline Goods",
            "business_type": "Retail",
            "business_address": "14 Market Street, Dhaka",
            "business_phone": "+8801700000000",
            "verification_reference": "TRADE-4821-UPDATED",
        }, format="json")
        self.assertEqual(resubmitted.status_code, 201, resubmitted.data)
        self.assertEqual(resubmitted.data["review_cycle"], 2)
        self.assertEqual(SellerApplication.objects.count(), 1)
