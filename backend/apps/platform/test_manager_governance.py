from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.catalog.models import Category, Product, ProductApproval
from apps.platform.models import (
    AuditLog,
    AuthSession,
    ManagerProfile,
    OwnershipHistory,
    SellerProfile,
    ShareTransaction,
)

PASSWORD = "Safe-Phase4-Manager-91!Pass"


class ManagerAndShareGovernanceTests(TestCase):
    def make_user(self, email, role_key):
        user = User.objects.create_user(email=email, password=PASSWORD, first_name=email.split("@")[0], status=User.Status.ACTIVE)
        UserRole.objects.create(user=user, role=Role.objects.get(key=role_key))
        return user

    def setUp(self):
        self.client = APIClient()
        self.owner = self.make_user("owner@phase4.test", Role.Key.OWNER)
        self.admin_assigned = self.make_user("admin1@phase4.test", Role.Key.ADMIN)
        self.admin_unassigned = self.make_user("admin2@phase4.test", Role.Key.ADMIN)
        self.other_manager = self.make_user("mgr2@phase4.test", Role.Key.MANAGER)
        self.other_manager_profile = ManagerProfile.objects.create(
            user=self.other_manager,
            title="Regional Director",
            business_unit="Chattogram",
            responsibilities=["Regional Logistics"],
            created_by=self.owner,
        )

    def test_owner_creates_manager_and_prevents_manager_privilege_escalation(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            "/api/v1/owner/managers/",
            {
                "email": "nadia.mgr@phase4.test",
                "first_name": "Nadia",
                "last_name": "Karim",
                "title": "VP of Operations",
                "business_unit": "Dhaka Metro",
                "responsibilities": ["Catalog Oversight", "SLA Compliance"],
                "password": PASSWORD,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        manager_id = created.data["id"]
        manager_user = User.objects.get(email="nadia.mgr@phase4.test")

        # Manager cannot create another manager, modify permissions, or assign admins
        self.client.force_authenticate(manager_user)
        self.assertEqual(
            self.client.post("/api/v1/owner/managers/", {"email": "rogue@phase4.test"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/owner/managers/{manager_id}/permissions/",
                {"permission": "manager.reports.finance", "is_granted": True},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/owner/admin-assignments/",
                {"admin_id": str(self.admin_assigned.pk), "manager_id": manager_id},
                format="json",
            ).status_code,
            403,
        )

    def test_financial_data_isolation_and_dynamic_permission_grant_revoke(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            "/api/v1/owner/managers/",
            {"email": "fin.mgr@phase4.test", "title": "Partner", "password": PASSWORD},
            format="json",
        )
        manager_id = created.data["id"]
        manager_user = User.objects.get(email="fin.mgr@phase4.test")

        # By default manager.reports.finance is False -> revenue_analytics is None
        self.client.force_authenticate(manager_user)
        dash_before = self.client.get("/api/v1/manager/dashboard/")
        self.assertEqual(dash_before.status_code, 200)
        self.assertFalse(dash_before.data["permissions"]["manager.reports.finance"])
        self.assertIsNone(dash_before.data["revenue_analytics"])

        # Owner grants manager.reports.finance
        self.client.force_authenticate(self.owner)
        grant = self.client.post(
            f"/api/v1/owner/managers/{manager_id}/permissions/",
            {"permission": "manager.reports.finance", "is_granted": True},
            format="json",
        )
        self.assertEqual(grant.status_code, 200)

        self.client.force_authenticate(manager_user)
        dash_after = self.client.get("/api/v1/manager/dashboard/")
        self.assertTrue(dash_after.data["permissions"]["manager.reports.finance"])
        self.assertIsNotNone(dash_after.data["revenue_analytics"])

        # Owner revokes manager.reports.finance -> immediate effect
        self.client.force_authenticate(self.owner)
        self.client.post(
            f"/api/v1/owner/managers/{manager_id}/permissions/",
            {"permission": "manager.reports.finance", "is_granted": False},
            format="json",
        )
        self.client.force_authenticate(manager_user)
        dash_revoked = self.client.get("/api/v1/manager/dashboard/")
        self.assertFalse(dash_revoked.data["permissions"]["manager.reports.finance"])
        self.assertIsNone(dash_revoked.data["revenue_analytics"])

    def test_admin_assignment_isolation_and_immediate_manager_removal_revocation(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            "/api/v1/owner/managers/",
            {"email": "team.mgr@phase4.test", "title": "Team Lead", "password": PASSWORD},
            format="json",
        )
        manager_id = created.data["id"]
        manager_user = User.objects.get(email="team.mgr@phase4.test")

        # Assign admin_assigned to team.mgr, and admin_unassigned to other_manager
        assign1 = self.client.post(
            "/api/v1/owner/admin-assignments/",
            {
                "action": "assign",
                "admin_id": str(self.admin_assigned.pk),
                "manager_id": manager_id,
                "responsibilities": "Electronics Moderation",
            },
            format="json",
        )
        self.assertEqual(assign1.status_code, 200)

        self.client.post(
            "/api/v1/owner/admin-assignments/",
            {
                "action": "assign",
                "admin_id": str(self.admin_unassigned.pk),
                "manager_id": self.other_manager_profile.pk,
                "responsibilities": "Fashion Moderation",
            },
            format="json",
        )

        # Create product approval activity for both admins
        seller_u = self.make_user("s@phase4.test", Role.Key.SELLER)
        seller_p = SellerProfile.objects.create(user=seller_u, business_name="S1", store_slug="s1", is_active=True)
        cat = Category.objects.create(name="Tech", slug="tech")
        prod1 = Product.objects.create(seller=seller_p, category=cat, name="P1", slug="p1", description="d", price="100")
        prod2 = Product.objects.create(seller=seller_p, category=cat, name="P2", slug="p2", description="d", price="100")
        ProductApproval.objects.create(product=prod1, reviewer=self.admin_assigned, reviewer_role="admin", decision="approved", version=1)
        ProductApproval.objects.create(product=prod2, reviewer=self.admin_unassigned, reviewer_role="admin", decision="approved", version=1)

        # Manager only sees admin_assigned and their activity, NOT admin_unassigned
        self.client.force_authenticate(manager_user)
        dash = self.client.get("/api/v1/manager/dashboard/")
        self.assertEqual(dash.status_code, 200)
        emails = [a["email"] for a in dash.data["assigned_admins"]]
        self.assertEqual(emails, ["admin1@phase4.test"])
        activity_admins = [a["admin_email"] for a in dash.data["team_activity"]]
        self.assertEqual(activity_admins, ["admin1@phase4.test"])

        # Create active session for manager, then Owner removes manager -> session invalidated & dashboard 403
        session = AuthSession.objects.create(
            user=manager_user,
            refresh_jti="jti-test-phase4",
            expires_at=timezone.now() + timezone.timedelta(days=1),
        )
        self.client.force_authenticate(self.owner)
        removed = self.client.post(
            f"/api/v1/owner/managers/{manager_id}/status/",
            {"action": "remove", "reason": "End of partner rotation"},
            format="json",
        )
        self.assertEqual(removed.status_code, 200)
        session.refresh_from_db()
        self.assertIsNotNone(session.revoked_at)

        self.client.force_authenticate(manager_user)
        self.assertEqual(self.client.get("/api/v1/manager/dashboard/").status_code, 403)

    def test_business_share_plan_percentage_validation_transfers_and_manager_isolation(self):
        self.client.force_authenticate(self.owner)
        plan_res = self.client.post(
            "/api/v1/owner/shares/plans/",
            {
                "name": "SHOPLEX Partner Equity Plan 2026",
                "code": "partner-equity-2026",
                "total_authorized_shares": 100000,
                "max_allocated_percentage": "25.00",
                "company_valuation": "80000000.00",
            },
            format="json",
        )
        self.assertEqual(plan_res.status_code, 201, plan_res.data)
        plan_id = plan_res.data["id"]

        mgr1_res = self.client.post(
            "/api/v1/owner/managers/",
            {"email": "partner1@phase4.test", "title": "Senior Partner", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(mgr1_res.status_code, 201)
        mgr1_user = User.objects.get(email="partner1@phase4.test")

        # Allocate 15.00% to partner1
        alloc1 = self.client.post(
            "/api/v1/owner/shares/allocations/",
            {
                "plan_id": plan_id,
                "holder_email": "partner1@phase4.test",
                "ownership_percentage": "15.00",
                "legal_reference": "DEED-2026-001",
            },
            format="json",
        )
        self.assertEqual(alloc1.status_code, 201, alloc1.data)
        allocation_id = alloc1.data["allocations"][0]["id"]

        # Attempting to allocate another 12.00% (15 + 12 = 27% > 25% max) must fail validation
        exceed = self.client.post(
            "/api/v1/owner/shares/allocations/",
            {
                "plan_id": plan_id,
                "holder_email": "mgr2@phase4.test",
                "ownership_percentage": "12.00",
            },
            format="json",
        )
        self.assertEqual(exceed.status_code, 400)

        # Transfer 5.00% from partner1 to mgr2
        transfer = self.client.post(
            "/api/v1/owner/shares/transfers/",
            {
                "allocation_id": allocation_id,
                "to_holder_email": "mgr2@phase4.test",
                "percentage": "5.00",
                "legal_reference": "TRANSFER-2026-009",
            },
            format="json",
        )
        self.assertEqual(transfer.status_code, 200, transfer.data)

        # Add ownership document for partner1 only
        doc = self.client.post(
            "/api/v1/owner/shares/documents/",
            {
                "plan_id": plan_id,
                "holder_email": "partner1@phase4.test",
                "title": "Partner Equity Certificate #001",
                "document_type": "certificate",
                "reference_number": "CERT-2026-001",
            },
            format="json",
        )
        self.assertEqual(doc.status_code, 201)

        # Verify append-only immutability on ShareTransaction and OwnershipHistory
        tx = ShareTransaction.objects.first()
        hist = OwnershipHistory.objects.first()
        with self.assertRaises(ValueError):
            tx.percentage_delta = Decimal("1.00")
            tx.save()
        with self.assertRaises(ValueError):
            hist.delete()

        # Verify partner1 sees ONLY their own 10.00% remaining share and document, while mgr2 sees ONLY their 5.00%
        self.client.force_authenticate(mgr1_user)
        mgr1_dash = self.client.get("/api/v1/manager/dashboard/")
        self.assertEqual(mgr1_dash.data["share_ownership"]["total_ownership_percentage"], "10.00")
        self.assertEqual(len(mgr1_dash.data["share_ownership"]["documents"]), 1)

        self.client.force_authenticate(self.other_manager)
        mgr2_dash = self.client.get("/api/v1/manager/dashboard/")
        self.assertEqual(mgr2_dash.data["share_ownership"]["total_ownership_percentage"], "5.00")
        self.assertEqual(len(mgr2_dash.data["share_ownership"]["documents"]), 0)

        self.assertTrue(AuditLog.objects.filter(action="shares.transferred").exists())
