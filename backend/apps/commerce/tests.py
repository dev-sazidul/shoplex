from django.test import TestCase
from decimal import Decimal
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.catalog.models import Category, Product
from apps.commerce.models import (
    Address,
    CartItem,
    CommissionRule,
    Order,
    Payment,
    SellerOrder,
    ShippingRule,
)
from apps.platform.models import SellerProfile


PASSWORD = "Phase-Two-Test_Password-290!"


def make_user(email, role_key):
    user = User.objects.create_user(email=email, password=PASSWORD, first_name=email.split("@")[0], status=User.Status.ACTIVE)
    UserRole.objects.create(user=user, role=Role.objects.get(key=role_key))
    return user


def make_seller(email, name):
    user = make_user(email, Role.Key.SELLER)
    profile = SellerProfile.objects.create(user=user, business_name=name, store_slug=name.lower().replace(" ", "-"), is_active=True)
    return user, profile


class MultiVendorCheckoutTests(TestCase):
    def setUp(self):
        self.customer = make_user("buyer@example.test", Role.Key.CUSTOMER)
        self.seller_one_user, self.seller_one = make_seller("one@example.test", "Northline Goods")
        self.seller_two_user, self.seller_two = make_seller("two@example.test", "Field Studio")
        category = Category.objects.create(name="Home", slug="home")
        self.product_one = Product.objects.create(
            seller=self.seller_one, category=category, name="Ceramic Cup", slug="ceramic-cup",
            description="Hand-finished cup.", sku="CUP-1", price="100.00", stock_quantity=8,
            status=Product.Status.PUBLISHED,
        )
        self.product_two = Product.objects.create(
            seller=self.seller_two, category=category, name="Linen Towel", slug="linen-towel",
            description="Soft woven towel.", sku="TOWEL-1", price="100.00", stock_quantity=6,
            status=Product.Status.PUBLISHED,
        )
        CommissionRule.objects.create(percentage="10.00")
        self.address = Address.objects.create(
            user=self.customer, recipient_name="Jamie Buyer", phone_number="+8801700000000",
            address_line1="12 River Road", city="Dhaka", country_code="BD", is_default=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def fill_cart(self):
        first = self.client.post("/api/v1/cart/", {"product_id": str(self.product_one.pk), "quantity": 2}, format="json")
        second = self.client.post("/api/v1/cart/", {"product_id": str(self.product_two.pk), "quantity": 1}, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)

    def test_multi_seller_checkout_splits_orders_and_retries_idempotently(self):
        self.fill_cart()
        key = "a0dc83a1-dff4-4d55-ae01-3de1fb837ee3"
        payload = {"address_id": str(self.address.pk), "payment_method": "cod", "idempotency_key": key}
        response = self.client.post("/api/v1/checkout/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["subtotal"], "300.00")
        self.assertEqual(len(response.data["seller_orders"]), 2)
        self.assertEqual(SellerOrder.objects.filter(order_id=response.data["id"]).count(), 2)
        for seller_order in SellerOrder.objects.filter(order_id=response.data["id"]):
            self.assertEqual(seller_order.commission_amount, seller_order.subtotal * 10 / 100)
            self.assertEqual(seller_order.net_earnings, seller_order.subtotal - seller_order.commission_amount)
        self.assertEqual(Payment.objects.get(order_id=response.data["id"]).status, Payment.Status.PENDING)

        retry = self.client.post("/api/v1/checkout/", payload, format="json")
        self.assertEqual(retry.status_code, 201, retry.data)
        self.assertEqual(retry.data["id"], response.data["id"])
        self.assertEqual(Order.objects.filter(customer=self.customer).count(), 1)
        self.product_one.refresh_from_db()
        self.product_two.refresh_from_db()
        self.assertEqual(self.product_one.stock_quantity, 6)
        self.assertEqual(self.product_two.stock_quantity, 5)

    def test_seller_order_endpoint_never_returns_another_sellers_suborder(self):
        self.fill_cart()
        checkout = self.client.post("/api/v1/checkout/", {
            "address_id": str(self.address.pk),
            "payment_method": "cod",
            "idempotency_key": "ec865f20-8db6-47bb-bf0f-d5ab14c5577b",
        }, format="json")
        self.assertEqual(checkout.status_code, 201, checkout.data)
        seller_one_order = SellerOrder.objects.get(order_id=checkout.data["id"], seller=self.seller_one)
        self.client.force_authenticate(self.seller_one_user)
        response = self.client.get("/api/v1/seller/orders/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(seller_one_order.pk))

    def test_cancel_restores_inventory_and_customer_orders_are_private(self):
        self.client.post("/api/v1/cart/", {"product_id": str(self.product_one.pk), "quantity": 1}, format="json")
        checkout = self.client.post("/api/v1/checkout/", {
            "address_id": str(self.address.pk),
            "payment_method": "cod",
            "idempotency_key": "d1f6b44b-5202-4e16-967a-dfa6327f85bc",
        }, format="json")
        self.assertEqual(checkout.status_code, 201, checkout.data)
        cancellation = self.client.post(f"/api/v1/orders/{checkout.data['id']}/cancel/")
        self.assertEqual(cancellation.status_code, 200, cancellation.data)
        self.product_one.refresh_from_db()
        self.assertEqual(self.product_one.stock_quantity, 8)

        stranger = make_user("stranger@example.test", Role.Key.CUSTOMER)
        self.client.force_authenticate(stranger)
        self.assertEqual(self.client.get(f"/api/v1/orders/{checkout.data['id']}/").status_code, 404)

    def test_shipping_quote_counts_distinct_sellers_in_cart(self):
        self.fill_cart()
        ShippingRule.objects.create(country_code="BD", amount="12.50")
        response = self.client.get(f"/api/v1/shipping/quote/?address_id={self.address.pk}")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["seller_count"], 2)
        self.assertEqual(response.data["shipping_total"], Decimal("25.00"))

    def test_seller_earnings_only_become_payout_eligible_when_completed(self):
        self.client.post("/api/v1/cart/", {"product_id": str(self.product_one.pk), "quantity": 1}, format="json")
        checkout = self.client.post("/api/v1/checkout/", {
            "address_id": str(self.address.pk),
            "payment_method": "cod",
            "idempotency_key": "c96b0584-b793-4773-b9a6-cbde4da94e56",
        }, format="json")
        self.assertEqual(checkout.status_code, 201, checkout.data)
        seller_order_id = checkout.data["seller_orders"][0]["id"]
        self.client.force_authenticate(self.seller_one_user)
        payout = self.client.post("/api/v1/seller/payout-requests/", {"amount": "1.00"}, format="json")
        self.assertEqual(payout.status_code, 400)

        for state, extra in (("shipped", {"carrier": "Parcel", "tracking_number": "TRACK-1"}), ("delivered", {}), ("completed", {})):
            response = self.client.post(f"/api/v1/seller/orders/{seller_order_id}/fulfillment/", {"status": state, **extra}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
        dashboard = self.client.get("/api/v1/seller/dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["finance"]["net_earnings"], Decimal("90.00"))
        payout = self.client.post("/api/v1/seller/payout-requests/", {"amount": "90.00"}, format="json")
        self.assertEqual(payout.status_code, 201, payout.data)

    def test_payment_history_is_private_to_the_customer(self):
        self.client.post("/api/v1/cart/", {"product_id": str(self.product_one.pk), "quantity": 1}, format="json")
        order = self.client.post("/api/v1/checkout/", {
            "address_id": str(self.address.pk),
            "payment_method": "cod",
            "idempotency_key": "f9762b6f-05ef-4672-acfb-ae8ea3d213ca",
        }, format="json")
        self.assertEqual(order.status_code, 201, order.data)
        history = self.client.get("/api/v1/payments/")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.data["results"][0]["order_number"], order.data["order_number"])
        self.client.force_authenticate(make_user("another-buyer@example.test", Role.Key.CUSTOMER))
        self.assertEqual(self.client.get("/api/v1/payments/").data["count"], 0)
