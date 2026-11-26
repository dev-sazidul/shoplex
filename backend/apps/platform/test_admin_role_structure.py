from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.catalog.models import Category, Product
from apps.platform.models import AuditLog, SellerProfile

PASSWORD = "Safe-Admin-Staff-77!Pass"


class FinalOwnerAndAdminRoleStructureTests(TestCase):
    def make_user(self, email, role_key):
        user = User.objects.create_user(email=email, password=PASSWORD, first_name=email.split("@")[0], status=User.Status.ACTIVE)
        UserRole.objects.create(user=user, role=Role.objects.get(key=role_key))
        return user

    def setUp(self):
        self.client = APIClient()
        self.owner = self.make_user("owner@structure.test", Role.Key.OWNER)
        self.category = Category.objects.create(name="Flagship", slug="flagship")

    def test_admin_is_owner_employee_with_zero_default_staff_permissions_and_no_seller_access(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            "/api/v1/owner/admins/",
            {"email": "staff1@structure.test", "first_name": "Rafiq", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["granted_count"], 0)
        admin_id = created.data["id"]
        admin_user = User.objects.get(pk=admin_id)

        # Admin cannot create another admin, grant itself permissions, register as a seller, or access unauthorized APIs
        self.client.force_authenticate(admin_user)
        self.assertEqual(
            self.client.post("/api/v1/owner/admins/", {"email": "rogue@structure.test"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                f"/api/v1/owner/admins/{admin_id}/permissions/",
                {"permission": "admin.products.create", "is_granted": True},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/seller/application/",
                {"business_name": "Admin Store", "business_address": "Dhaka", "business_phone": "+8801700000000"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/v1/admin-staff/orders/").status_code, 403)
        self.assertEqual(self.client.get("/api/v1/admin-staff/finance-report/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/admin-staff/products/",
                {"name": "Unauthorized Item", "description": "Desc", "category": "flagship", "price": "500.00"},
                format="json",
            ).status_code,
            403,
        )

    def test_admin_uploaded_product_is_platform_owned_by_shoplex_owner_and_revocation_is_immediate(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            "/api/v1/owner/admins/",
            {"email": "catalog.admin@structure.test", "first_name": "Sadia", "password": PASSWORD},
            format="json",
        )
        admin_id = created.data["id"]
        admin_user = User.objects.get(pk=admin_id)

        # Owner grants ONLY admin.products.create (not publish, not finance)
        grant = self.client.post(
            f"/api/v1/owner/admins/{admin_id}/permissions/",
            {"permission": "admin.products.create", "is_granted": True},
            format="json",
        )
        self.assertEqual(grant.status_code, 200)

        # Admin uploads a product -> owned by SHOPLEX Official (Owner), created_by = Admin ID, NOT SellerProfile of Admin
        self.client.force_authenticate(admin_user)
        uploaded = self.client.post(
            "/api/v1/admin-staff/products/",
            {
                "name": "SHOPLEX Signature Watch",
                "description": "Platform-owned flagship timepiece.",
                "category": "flagship",
                "price": "12500.00",
                "stock_quantity": 20,
                "product_source": "supplier",
                "supplier_name": "Geneva Watch Co.",
            },
            format="json",
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.data)
        self.assertEqual(uploaded.data["ownership_type"], Product.OwnershipType.PLATFORM)
        self.assertEqual(uploaded.data["product_owner"], "SHOPLEX Official")
        self.assertEqual(uploaded.data["created_by_id"], str(admin_user.pk))
        self.assertEqual(uploaded.data["product_source"], Product.ProductSource.SUPPLIER)
        self.assertEqual(uploaded.data["status"], Product.Status.PENDING_APPROVAL)
        self.assertFalse(SellerProfile.objects.filter(user=admin_user).exists())

        # Admin cannot publish without admin.products.publish
        product_id = uploaded.data["id"]
        self.assertEqual(
            self.client.post(f"/api/v1/admin-staff/products/{product_id}/publish/").status_code,
            403,
        )

        # Owner revokes admin.products.create -> immediate 403 on next upload attempt
        self.client.force_authenticate(self.owner)
        revoke = self.client.post(
            f"/api/v1/owner/admins/{admin_id}/permissions/",
            {"permission": "admin.products.create", "is_granted": False},
            format="json",
        )
        self.assertEqual(revoke.status_code, 200)

        self.client.force_authenticate(admin_user)
        blocked = self.client.post(
            "/api/v1/admin-staff/products/",
            {"name": "Second Item", "description": "Desc", "category": "flagship", "price": "500.00"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertTrue(AuditLog.objects.filter(action="owner.admin_permission_updated").exists())

    def test_owner_grants_selected_read_only_financial_report_without_ledger_write_access(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            "/api/v1/owner/admins/",
            {"email": "fin.admin@structure.test", "first_name": "Kamal", "password": PASSWORD},
            format="json",
        )
        admin_id = created.data["id"]
        admin_user = User.objects.get(pk=admin_id)

        self.client.post(
            f"/api/v1/owner/admins/{admin_id}/permissions/",
            {"permission": "admin.finance.reports", "is_granted": True},
            format="json",
        )

        self.client.force_authenticate(admin_user)
        report = self.client.get("/api/v1/admin-staff/finance-report/")
        self.assertEqual(report.status_code, 200)
        self.assertTrue(report.data["read_only"])

        # Admin STILL cannot access or modify the Owner financial ledger
        self.assertEqual(self.client.get("/api/v1/owner/finance/ledger/").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/owner/finance/ledger/",
                {"transaction_type": "operational_expense", "amount": "100.00"},
                format="json",
            ).status_code,
            403,
        )
