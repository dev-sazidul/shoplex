from decimal import Decimal
import uuid

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.catalog.models import Category, Product
from apps.commerce.models import Address, CommissionRule, FinancialLedgerEntry, Order, Payment, SellerOrder
from apps.platform.models import SellerProfile

PASSWORD = "Safe-Phase5-Payment-99!Pass"


class Phase5PaymentsFinancialAndSecurityTests(TestCase):
    def make_user(self, email, role_key):
        user = User.objects.create_user(
            email=email,
            password=PASSWORD,
            first_name=email.split("@")[0],
            phone_number="+8801711223344",
            status=User.Status.ACTIVE,
        )
        UserRole.objects.create(user=user, role=Role.objects.get(key=role_key))
        return user

    def setUp(self):
        self.client = APIClient()
        self.owner = self.make_user("owner@phase5.test", Role.Key.OWNER)
        self.admin = self.make_user("admin@phase5.test", Role.Key.ADMIN)
        self.customer = self.make_user("customer@phase5.test", Role.Key.CUSTOMER)
        self.seller_user = self.make_user("seller@phase5.test", Role.Key.SELLER)
        self.seller = SellerProfile.objects.create(
            user=self.seller_user,
            business_name="Apex Flagship",
            store_slug="apex-flagship",
            is_active=True,
        )
        self.category = Category.objects.create(name="Audio", slug="audio")
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            name="Apex Reference Headphones",
            slug="apex-reference-headphones",
            description="Reference studio monitor headphones.",
            sku="APX-1000",
            price=Decimal("1000.00"),
            stock_quantity=10,
            status=Product.Status.PUBLISHED,
        )
        self.address = Address.objects.create(
            user=self.customer,
            label="Home",
            recipient_name="Customer Test",
            phone_number="+8801711223344",
            address_line1="Road 7, Gulshan",
            city="Dhaka",
            country_code="BD",
            is_default=True,
        )

    def _checkout(self, method="bkash"):
        self.client.force_authenticate(self.customer)
        self.client.post("/api/v1/cart/", {"product_id": str(self.product.pk), "quantity": 1}, format="json")
        res = self.client.post(
            "/api/v1/checkout/",
            {
                "address_id": str(self.address.pk),
                "payment_method": method,
                "idempotency_key": str(uuid.uuid4()),
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        return res.data["id"]

    def test_commission_calculation_1000_bdt_at_10_percent_and_product_specific_override(self):
        # 1. Default 10% commission on 1,000 BDT -> 100 BDT platform commission, 900 BDT seller net earning
        order_id = self._checkout(method="cod")
        suborder = SellerOrder.objects.get(order_id=order_id)
        self.assertEqual(suborder.subtotal, Decimal("1000.00"))
        self.assertEqual(suborder.commission_amount, Decimal("100.00"))
        self.assertEqual(suborder.net_earnings, Decimal("900.00"))

        # 2. Product-specific commission override (15%) takes precedence over global/category rules
        CommissionRule.objects.create(category=self.category, percentage=Decimal("12.00"), is_active=True)
        CommissionRule.objects.create(product=self.product, percentage=Decimal("15.00"), is_active=True)
        order2_id = self._checkout(method="cod")
        suborder2 = SellerOrder.objects.get(order_id=order2_id)
        self.assertEqual(suborder2.commission_amount, Decimal("150.00"))
        self.assertEqual(suborder2.net_earnings, Decimal("850.00"))

    def test_payment_initiation_raw_card_rejection_webhook_idempotency_and_reconciliation(self):
        order_id = self._checkout(method="bkash")
        order = Order.objects.get(pk=order_id)
        self.assertEqual(order.status, Order.Status.PENDING_PAYMENT)

        # Raw card credentials must be rejected
        self.client.force_authenticate(self.customer)
        raw_card = self.client.post(
            f"/api/v1/payments/{order_id}/initiate/",
            {"method": "card", "card_number": "4111111111111111", "cvv": "123"},
            format="json",
        )
        self.assertEqual(raw_card.status_code, 400)

        init_res = self.client.post(
            f"/api/v1/payments/{order_id}/initiate/",
            {"method": "bkash"},
            format="json",
        )
        self.assertEqual(init_res.status_code, 200, init_res.data)
        tx_ref = init_res.data["transaction_reference"]
        sig = init_res.data["sandbox_webhook_signature"]

        # Valid webhook verifies payment, transitions order to PROCESSING, and posts gateway fee
        webhook_payload = {
            "event_id": "EVT-BKASH-001",
            "transaction_reference": tx_ref,
            "amount": "1000.00",
            "status": "VALID",
            "signature": sig,
        }
        wh1 = self.client.post("/api/v1/payments/webhook/bkash/", webhook_payload, format="json")
        self.assertEqual(wh1.status_code, 200, wh1.data)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PROCESSING)
        self.assertEqual(order.payment.status, Payment.Status.PAID)
        self.assertEqual(order.payment.gateway_fee, Decimal("15.00"))

        # Duplicate callback with same event_id is idempotently ignored
        wh_dup = self.client.post("/api/v1/payments/webhook/bkash/", webhook_payload, format="json")
        self.assertEqual(wh_dup.status_code, 200)
        self.assertEqual(wh_dup.data["status"], "duplicate_ignored")

        # Complete order and verify reconciliation report
        suborder = order.seller_orders.first()
        self.client.force_authenticate(self.seller_user)
        self.client.post(
            f"/api/v1/seller/orders/{suborder.pk}/fulfillment/",
            {"status": "shipped", "carrier": "DHL", "tracking_number": "DHL-991"},
            format="json",
        )
        self.client.post(f"/api/v1/seller/orders/{suborder.pk}/fulfillment/", {"status": "delivered"}, format="json")
        self.client.post(f"/api/v1/seller/orders/{suborder.pk}/fulfillment/", {"status": "completed"}, format="json")

        self.client.force_authenticate(self.owner)
        recon = self.client.get("/api/v1/owner/payments/reconciliation/")
        self.assertEqual(recon.status_code, 200, recon.data)
        self.assertTrue(recon.data["reconciled"])
        self.assertEqual(recon.data["discrepancy_amount"], "0.00")

    def test_payment_failure_webhook_restores_reserved_stock_and_owner_refund_updates_ledger(self):
        initial_stock = self.product.stock_quantity
        order_id = self._checkout(method="sslcommerz")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock - 1)

        self.client.force_authenticate(self.customer)
        init_res = self.client.post(
            f"/api/v1/payments/{order_id}/initiate/",
            {"method": "sslcommerz"},
            format="json",
        )
        tx_ref = init_res.data["transaction_reference"]

        fail_wh = self.client.post(
            "/api/v1/payments/webhook/sslcommerz/",
            {
                "event_id": "EVT-SSL-FAIL-01",
                "transaction_reference": tx_ref,
                "amount": "1000.00",
                "status": "FAILED",
                "signature": "SANDBOX_BYPASS",
            },
            format="json",
        )
        self.assertEqual(fail_wh.status_code, 200, fail_wh.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, initial_stock)

        # Now place a COD order, complete it, and execute an Owner refund
        paid_order_id = self._checkout(method="cod")
        suborder = SellerOrder.objects.get(order_id=paid_order_id)
        self.client.force_authenticate(self.seller_user)
        self.client.post(
            f"/api/v1/seller/orders/{suborder.pk}/fulfillment/",
            {"status": "shipped", "carrier": "Pathao", "tracking_number": "PTH-123"},
            format="json",
        )
        self.client.post(f"/api/v1/seller/orders/{suborder.pk}/fulfillment/", {"status": "delivered"}, format="json")
        self.client.post(f"/api/v1/seller/orders/{suborder.pk}/fulfillment/", {"status": "completed"}, format="json")

        # Admin cannot execute a refund (Rule 2 & 5)
        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.post(f"/api/v1/owner/payments/{paid_order_id}/refund/", {}, format="json").status_code,
            403,
        )

        # Owner executes refund -> stock restored, seller refund debit created, immutable ledger entry posted
        self.client.force_authenticate(self.owner)
        refund_res = self.client.post(
            f"/api/v1/owner/payments/{paid_order_id}/refund/",
            {"reason": "Defective unit replacement refund", "restore_stock": True},
            format="json",
        )
        self.assertEqual(refund_res.status_code, 200, refund_res.data)
        self.assertEqual(refund_res.data["order_status"], Order.Status.REFUNDED)
        self.assertTrue(
            FinancialLedgerEntry.objects.filter(
                order_id=paid_order_id,
                transaction_type=FinancialLedgerEntry.TransactionType.REFUND_DEDUCTION,
            ).exists()
        )
