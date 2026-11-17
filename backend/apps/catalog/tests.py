from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.catalog.models import Category, Product, ProductApproval, ProductImage
from apps.commerce.models import Address
from apps.platform.models import SellerProfile


PASSWORD = "Phase-Two-Test_Password-290!"
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDATx\x9cc\x00\x02"
    b"\x00\x00\x05\x00\x01\xa5\xf6E\x8d\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_user(email, role_key):
    user = User.objects.create_user(email=email, password=PASSWORD, first_name=email.split("@")[0], status=User.Status.ACTIVE)
    UserRole.objects.create(user=user, role=Role.objects.get(key=role_key))
    return user


def make_seller(email, name):
    user = make_user(email, Role.Key.SELLER)
    profile = SellerProfile.objects.create(user=user, business_name=name, store_slug=name.lower().replace(" ", "-"), is_active=True)
    return user, profile


class ProductWorkflowTests(TestCase):
    def setUp(self):
        self.seller, self.seller_profile = make_seller("seller@example.test", "Northline Goods")
        self.other_seller, self.other_profile = make_seller("other@example.test", "Field Studio")
        self.admin = make_user("admin@example.test", Role.Key.ADMIN)
        self.owner = make_user("owner@example.test", Role.Key.OWNER)
        self.category = Category.objects.create(name="Home", slug="home")
        self.client = APIClient()

    def product_for(self, seller, slug):
        product = Product.objects.create(
            seller=seller,
            category=self.category,
            name=slug.title(),
            slug=slug,
            description="A thoughtfully made product for everyday use.",
            sku=f"SKU-{slug}",
            price="100.00",
            stock_quantity=5,
        )
        ProductImage.objects.create(
            product=product,
            image=SimpleUploadedFile(f"{slug}.png", TINY_PNG, content_type="image/png"),
            alt_text=slug.title(),
        )
        return product

    def test_product_is_not_public_until_admin_and_owner_both_approve(self):
        product = self.product_for(self.seller_profile, "northline-vase")
        self.client.force_authenticate(self.seller)
        submitted = self.client.post(f"/api/v1/seller/products/{product.pk}/submit/")
        self.assertEqual(submitted.status_code, 202, submitted.data)
        self.assertEqual(submitted.data["status"], Product.Status.PENDING_APPROVAL)
        self.assertEqual(self.client.get("/api/v1/products/").data["count"], 0)

        self.client.force_authenticate(self.admin)
        admin_review = self.client.post(f"/api/v1/management/products/{product.pk}/review/", {"decision": ProductApproval.Decision.APPROVED}, format="json")
        self.assertEqual(admin_review.status_code, 200, admin_review.data)
        product.refresh_from_db()
        self.assertEqual(product.status, Product.Status.PENDING_APPROVAL)

        self.client.force_authenticate(self.owner)
        owner_review = self.client.post(f"/api/v1/management/products/{product.pk}/review/", {"decision": ProductApproval.Decision.APPROVED}, format="json")
        self.assertEqual(owner_review.status_code, 200, owner_review.data)
        product.refresh_from_db()
        self.assertEqual(product.status, Product.Status.PUBLISHED)
        self.assertEqual(self.client.get("/api/v1/products/").data["count"], 1)

    def test_seller_product_listing_is_scoped_to_own_store(self):
        self.product_for(self.seller_profile, "northline-cup")
        self.product_for(self.other_profile, "field-tray")
        self.client.force_authenticate(self.seller)
        response = self.client.get("/api/v1/seller/products/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["slug"], "northline-cup")

    def test_review_by_a_single_admin_cannot_publish(self):
        product = self.product_for(self.seller_profile, "northline-lamp")
        self.client.force_authenticate(self.seller)
        self.client.post(f"/api/v1/seller/products/{product.pk}/submit/")
        self.client.force_authenticate(self.admin)
        self.client.post(f"/api/v1/management/products/{product.pk}/review/", {"decision": ProductApproval.Decision.APPROVED}, format="json")
        self.assertEqual(self.client.get("/api/v1/products/").data["count"], 0)

    def test_only_customers_with_delivered_orders_can_review_once(self):
        from apps.commerce.models import Order, OrderItem, SellerOrder
        customer = make_user("buyer@example.test", Role.Key.CUSTOMER)
        product = self.product_for(self.seller_profile, "northline-review-cup")
        product.status = Product.Status.PUBLISHED
        product.save(update_fields=["status"])
        order = Order.objects.create(order_number="SLX-REVIEW-0001", customer=customer, payment_method="cod", subtotal="100", total="100")
        seller_order = SellerOrder.objects.create(order=order, seller=self.seller_profile, status=SellerOrder.Status.DELIVERED, subtotal="100", commission_amount="10", net_earnings="90")
        OrderItem.objects.create(seller_order=seller_order, product=product, product_name=product.name, unit_price="100", quantity=1, line_total="100")
        self.client.force_authenticate(customer)
        payload = {"rating": 5, "title": "Thoughtful finish", "body": "This arrived as described."}
        first = self.client.post(f"/api/v1/products/{product.slug}/reviews/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertTrue(first.data["is_verified_purchase"])
        duplicate = self.client.post(f"/api/v1/products/{product.slug}/reviews/", payload, format="json")
        self.assertEqual(duplicate.status_code, 400)
