from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.catalog.models import Category, Product
from apps.commerce.models import FinancialLedgerEntry, SellerEarning, SellerPayoutRequest
from apps.platform.models import AuditLog, SellerProfile

PASSWORD = "Safe-Control-Center-82!Pass"


class ControlCenterPhase3Tests(TestCase):
    def make_user(self, email, role_key):
        user = User.objects.create_user(email=email, password=PASSWORD, first_name="Test", status=User.Status.ACTIVE)
        UserRole.objects.create(user=user, role=Role.objects.get(key=role_key))
        return user

    def setUp(self):
        self.client = APIClient()
        self.owner = self.make_user("owner@control.test", Role.Key.OWNER)
        self.admin = self.make_user("admin@control.test", Role.Key.ADMIN)
        self.customer = self.make_user("customer@control.test", Role.Key.CUSTOMER)
        self.seller_user = self.make_user("seller@control.test", Role.Key.SELLER)
        self.seller_profile = SellerProfile.objects.create(
            user=self.seller_user,
            business_name="Studio Aurora",
            store_slug="studio-aurora",
            is_active=True,
        )
        self.category = Category.objects.create(name="Watches", slug="watches")
        self.product = Product.objects.create(
            seller=self.seller_profile,
            category=self.category,
            name="Aurora Chronograph",
            slug="aurora-chronograph",
            description="Precision timepiece.",
            sku="AUR-01",
            price=Decimal("15000.00"),
            stock_quantity=10,
            status=Product.Status.PUBLISHED,
        )

    def test_admin_permission_boundaries_block_all_owner_financial_and_governance_apis(self):
        self.client.force_authenticate(self.admin)
        admin_dash = self.client.get("/api/v1/management/admin-dashboard/")
        self.assertEqual(admin_dash.status_code, 200)
        self.assertIn("statistics", admin_dash.data)
        self.assertNotIn("financial_metrics", admin_dash.data)

        for restricted in (
            "/api/v1/owner/dashboard/",
            "/api/v1/owner/finance/ledger/",
            "/api/v1/owner/sellers/",
            "/api/v1/owner/payouts/",
            "/api/v1/owner/settings/",
            "/api/v1/owner/security/",
            "/api/v1/owner/audit-logs/",
        ):
            self.assertEqual(self.client.get(restricted).status_code, 403, restricted)

    def test_product_suspension_by_admin_and_restore_by_owner_only(self):
        self.client.force_authenticate(self.admin)
        suspended = self.client.post(
            f"/api/v1/management/products/{self.product.pk}/status/",
            {"action": "suspend", "reason": "Policy review"},
            format="json",
        )
        self.assertEqual(suspended.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.Status.SUSPENDED)

        admin_restore = self.client.post(
            f"/api/v1/management/products/{self.product.pk}/status/",
            {"action": "restore"},
            format="json",
        )
        self.assertEqual(admin_restore.status_code, 403)

        self.client.force_authenticate(self.owner)
        owner_restore = self.client.post(
            f"/api/v1/management/products/{self.product.pk}/status/",
            {"action": "restore"},
            format="json",
        )
        self.assertEqual(owner_restore.status_code, 200)
        self.product.refresh_from_db()
        self.assertNotEqual(self.product.status, Product.Status.SUSPENDED)

    def test_product_report_and_resolution_workflow(self):
        self.client.force_authenticate(self.customer)
        created = self.client.post(
            "/api/v1/management/product-reports/",
            {"product_id": str(self.product.pk), "reason": "Inaccurate specification", "details": "Case size mismatch"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        report_id = created.data["id"]

        self.client.force_authenticate(self.admin)
        queue = self.client.get("/api/v1/management/product-reports/")
        self.assertEqual(queue.status_code, 200)
        self.assertEqual(len(queue.data), 1)

        resolved = self.client.post(
            f"/api/v1/management/product-reports/{report_id}/resolve/",
            {"status": "resolved", "resolution_note": "Verified and suspended", "suspend_product": True},
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.Status.SUSPENDED)

    def test_owner_seller_suspension_and_reactivation(self):
        self.client.force_authenticate(self.owner)
        suspend = self.client.post(
            f"/api/v1/owner/sellers/{self.seller_profile.pk}/status/",
            {"action": "suspend", "reason": "Compliance audit"},
            format="json",
        )
        self.assertEqual(suspend.status_code, 200)
        self.seller_profile.refresh_from_db()
        self.seller_user.refresh_from_db()
        self.assertFalse(self.seller_profile.is_active)
        self.assertEqual(self.seller_user.status, User.Status.SUSPENDED)

        reactivate = self.client.post(
            f"/api/v1/owner/sellers/{self.seller_profile.pk}/status/",
            {"action": "reactivate"},
            format="json",
        )
        self.assertEqual(reactivate.status_code, 200)
        self.seller_profile.refresh_from_db()
        self.seller_user.refresh_from_db()
        self.assertTrue(self.seller_profile.is_active)
        self.assertEqual(self.seller_user.status, User.Status.ACTIVE)

    def test_immutable_financial_ledger_and_payout_settlement(self):
        SellerEarning.objects.create(
            seller=self.seller_profile,
            entry_type=SellerEarning.EntryType.SALE,
            amount=Decimal("5000.00"),
            reference="SLX-TEST-01",
        )
        payout = SellerPayoutRequest.objects.create(seller=self.seller_profile, amount=Decimal("2000.00"))

        self.client.force_authenticate(self.owner)
        expense = self.client.post(
            "/api/v1/owner/finance/ledger/",
            {"transaction_type": "operational_expense", "amount": "350.00", "description": "Cloud infrastructure"},
            format="json",
        )
        self.assertEqual(expense.status_code, 201)

        settled = self.client.post(
            f"/api/v1/owner/payouts/{payout.pk}/decision/",
            {"decision": "paid", "reason": "Bank transfer completed"},
            format="json",
        )
        self.assertEqual(settled.status_code, 200)
        payout.refresh_from_db()
        self.assertEqual(payout.status, SellerPayoutRequest.Status.PAID)

        entry = FinancialLedgerEntry.objects.filter(payout_request=payout).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.transaction_type, FinancialLedgerEntry.TransactionType.SELLER_PAYOUT)

        with self.assertRaises(ValueError):
            entry.amount = Decimal("1.00")
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()

        ledger = self.client.get("/api/v1/owner/finance/ledger/")
        self.assertEqual(ledger.status_code, 200)
        self.assertEqual(ledger.data["summary"]["operational_expenses"], "350.00")
        self.assertEqual(ledger.data["summary"]["completed_payouts_amount"], "2000.00")

    def test_owner_settings_security_mfa_and_audit_logs(self):
        self.client.force_authenticate(self.owner)
        updated_settings = self.client.put(
            "/api/v1/owner/settings/",
            {"settings": {"maintenance_mode": {"enabled": False, "message": "Normal operation"}}},
            format="json",
        )
        self.assertEqual(updated_settings.status_code, 200)

        mfa_bad_pass = self.client.post(
            "/api/v1/owner/security/",
            {"action": "enroll_mfa", "password": "wrong"},
            format="json",
        )
        self.assertEqual(mfa_bad_pass.status_code, 403)

        mfa_ok = self.client.post(
            "/api/v1/owner/security/",
            {"action": "enroll_mfa", "name": "Owner Hardware Key", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(mfa_ok.status_code, 200)
        self.assertTrue(mfa_ok.data["is_verified"])

        audits = self.client.get("/api/v1/owner/audit-logs/")
        self.assertEqual(audits.status_code, 200)
        self.assertTrue(any(row["action"] == "owner.mfa_enrolled" for row in audits.data))
        self.assertGreater(AuditLog.objects.count(), 0)
