"""Development-only demo data so every SHOPLEX portal can be explored end to end.

Orders are created through the real cart/checkout/fulfillment API so totals,
commission, stock reservation and seller earnings follow production rules.
Products are intentionally created without photos: sellers upload real images.
"""

import os
import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.catalog.models import Brand, Category, Product
from apps.commerce.models import Order, SellerOrder, ShippingRule
from apps.platform.models import ManagerProfile, SellerApplication, SellerProfile

DEMO_DOMAIN = "shoplex.local"
CATEGORIES = [
    ("Electronics", "Phones, audio, computing and smart devices."),
    ("Fashion", "Apparel, footwear and everyday essentials."),
    ("Home & Living", "Furniture, decor and kitchenware."),
    ("Beauty & Care", "Skincare, fragrance and grooming."),
    ("Sports & Outdoors", "Fitness gear and outdoor equipment."),
    ("Watches & Accessories", "Timepieces, bags and leather goods."),
    ("Books & Stationery", "Reading, writing and workspace tools."),
    ("Groceries", "Pantry staples and specialty foods."),
]
BRANDS = [("Northline", "Considered everyday technology."), ("Atelier Dhaka", "Contemporary South Asian fashion."), ("Verde Home", "Sustainable living essentials."), ("Lumen Care", "Clean, dermatologist-led skincare.")]
SELLERS = [
    ("seller", "Northline Electronics", "Authorised retailer of premium audio, wearables and smart-home devices."),
    ("seller2", "Atelier & Co.", "Independent fashion and lifestyle house with ethically made collections."),
]
PRODUCTS = [
    (0, "Electronics", "Northline", "Northline Studio Wireless Headphones", "18500", "22000", True, {"Battery": "40 hours", "Connectivity": "Bluetooth 5.3", "Noise cancelling": "Adaptive"}),
    (0, "Electronics", "Northline", "Northline Pulse Smartwatch", "12900", None, True, {"Display": "1.4\" AMOLED", "Water resistance": "5 ATM"}),
    (0, "Electronics", "Northline", "Compact 65W GaN Charger", "2450", "2900", False, {"Ports": "2× USB-C, 1× USB-A", "Output": "65W"}),
    (0, "Electronics", None, "Mechanical Keyboard — Low Profile", "7800", None, False, {"Switches": "Tactile", "Layout": "75%"}),
    (0, "Home & Living", "Verde Home", "Verde Ceramic Pour-Over Set", "3200", "3900", True, {"Material": "Stoneware", "Capacity": "600 ml"}),
    (0, "Watches & Accessories", None, "Minimalist Leather Card Holder", "1650", None, False, {"Material": "Full-grain leather"}),
    (1, "Fashion", "Atelier Dhaka", "Handloom Cotton Kurta", "3450", "4200", True, {"Fabric": "Handloom cotton", "Fit": "Relaxed"}),
    (1, "Fashion", "Atelier Dhaka", "Tailored Linen Shirt", "2890", None, False, {"Fabric": "European linen", "Fit": "Tailored"}),
    (1, "Fashion", None, "Everyday Canvas Sneakers", "4100", "4800", True, {"Upper": "Organic canvas", "Sole": "Natural rubber"}),
    (1, "Beauty & Care", "Lumen Care", "Lumen Vitamin C Serum 30 ml", "2200", None, True, {"Skin type": "All", "Volume": "30 ml"}),
    (1, "Beauty & Care", "Lumen Care", "Lumen Daily Mineral Sunscreen SPF 50", "1450", "1700", False, {"SPF": "50 PA++++"}),
    (1, "Watches & Accessories", None, "Classic Steel Automatic Watch", "26500", "31000", True, {"Movement": "Automatic", "Case": "40 mm steel"}),
    (1, "Sports & Outdoors", None, "Cork Yoga Mat", "3600", None, False, {"Thickness": "5 mm", "Material": "Natural cork"}),
    (0, "Books & Stationery", None, "A5 Dotted Notebook Set", "950", None, False, {"Pages": "192", "Paper": "100 gsm"}),
]
PENDING_PRODUCTS = [
    (0, "Electronics", "Northline", "Northline Portable Speaker Mini", "5400"),
    (1, "Home & Living", "Verde Home", "Verde Linen Throw Blanket", "4600"),
]


class Command(BaseCommand):
    help = "Seed development-only demo accounts, catalog and orders for every SHOPLEX portal."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Allow running when DEBUG is false (never use in production).")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("seed_demo is development-only. Set DJANGO_DEBUG=true or pass --force.")
        password = os.getenv("DEMO_PASSWORD", "Shoplex-Demo-2026!")
        if User.objects.filter(email=f"owner@{DEMO_DOMAIN}").exists():
            self.stdout.write(self.style.WARNING("Demo data already exists; nothing changed."))
            self._print_accounts(password)
            return
        with transaction.atomic():
            users = self._create_users(password)
            sellers = self._create_sellers(users)
            products = self._create_catalog(sellers)
            ShippingRule.objects.get_or_create(country_code="BD", defaults={"amount": Decimal("60.00"), "is_active": True})
        self._create_orders(users, sellers, products)
        self.stdout.write(self.style.SUCCESS("SHOPLEX demo data created."))
        self._print_accounts(password)

    def _user(self, local, first, last, password, roles):
        user = User.objects.create_user(email=f"{local}@{DEMO_DOMAIN}", password=password, first_name=first, last_name=last, status=User.Status.ACTIVE)
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at"])
        for key in roles:
            UserRole.objects.get_or_create(user=user, role=Role.objects.get(key=key))
        return user

    def _create_users(self, password):
        users = {
            "owner": self._user("owner", "Ariana", "Rahman", password, [Role.Key.OWNER]),
            "admin": self._user("admin", "Imran", "Hossain", password, [Role.Key.ADMIN]),
            "manager": self._user("manager", "Nadia", "Karim", password, [Role.Key.MANAGER]),
            "customer": self._user("customer", "Sara", "Ahmed", password, [Role.Key.CUSTOMER]),
            "seller": self._user("seller", "Tanvir", "Islam", password, [Role.Key.CUSTOMER, Role.Key.SELLER]),
            "seller2": self._user("seller2", "Maya", "Chowdhury", password, [Role.Key.CUSTOMER, Role.Key.SELLER]),
            "applicant": self._user("applicant", "Rafi", "Sultan", password, [Role.Key.CUSTOMER]),
        }
        ManagerProfile.objects.create(user=users["manager"], title="Regional Operations Manager", business_unit="Dhaka Division", created_by=users["owner"])
        SellerApplication.objects.create(user=users["applicant"], business_name="Sultan Crafts", business_type="artisan", business_address="House 12, Road 5, Dhanmondi, Dhaka", verification_reference="TRAD/DHK/2026/0412")
        return users

    def _create_sellers(self, users):
        sellers = []
        for key, name, description in SELLERS:
            profile = SellerProfile.objects.create(user=users[key], business_name=name, store_slug=slugify(name), store_description=description, business_type="retail", business_address="Gulshan Avenue, Dhaka", business_phone="+8801700000000", is_active=True)
            SellerApplication.objects.create(user=users[key], business_name=name, business_type="retail", business_address="Gulshan Avenue, Dhaka", status=SellerApplication.Status.APPROVED, reviewed_at=timezone.now())
            sellers.append(profile)
        return sellers

    def _create_catalog(self, sellers):
        categories = {name: Category.objects.create(name=name, slug=slugify(name), description=description, sort_order=index) for index, (name, description) in enumerate(CATEGORIES)}
        brands = {name: Brand.objects.create(name=name, slug=slugify(name), description=description) for name, description in BRANDS}
        now = timezone.now()
        products = []
        for index, (seller_index, category, brand, name, price, compare, featured, attributes) in enumerate(PRODUCTS):
            products.append(Product.objects.create(
                seller=sellers[seller_index], category=categories[category], brand=brands.get(brand), name=name, slug=slugify(name),
                description=f"{name} from {sellers[seller_index].business_name}. Carefully selected for quality, durability and everyday use.",
                sku=f"SLX-{index + 1:04d}", price=Decimal(price), compare_at_price=Decimal(compare) if compare else None,
                stock_quantity=random.randint(18, 60), attributes=attributes, status=Product.Status.PUBLISHED, approval_version=1,
                is_featured=featured, published_at=now - timedelta(days=len(PRODUCTS) - index),
            ))
        for seller_index, category, brand, name, price in PENDING_PRODUCTS:
            Product.objects.create(seller=sellers[seller_index], category=categories[category], brand=brands.get(brand), name=name, slug=slugify(name), description=f"{name} awaiting marketplace review.", price=Decimal(price), stock_quantity=25, status=Product.Status.PENDING_APPROVAL, approval_version=1)
        return products

    def _client(self, user):
        client = APIClient(HTTP_HOST="localhost")
        client.force_authenticate(user)
        return client

    def _create_orders(self, users, sellers, products):
        customer = self._client(users["customer"])
        address = customer.post("/api/v1/addresses/", {"label": "Home", "recipient_name": "Sara Ahmed", "phone_number": "+8801711000000", "address_line1": "Road 11, Banani", "city": "Dhaka", "country_code": "BD", "is_default": True}, format="json")
        if address.status_code != 201:
            raise CommandError(f"Demo address could not be created: {address.data}")
        rng = random.Random(2026)
        created = []
        for _ in range(18):
            for product in rng.sample(products, rng.randint(1, 3)):
                customer.post("/api/v1/cart/", {"product_id": str(product.id), "quantity": rng.randint(1, 2)}, format="json")
            response = customer.post("/api/v1/checkout/", {"address_id": address.data["id"], "payment_method": "cod", "idempotency_key": str(uuid.uuid4())}, format="json")
            if response.status_code != 201:
                raise CommandError(f"Demo checkout failed: {response.data}")
            created.append(response.data["id"])
        seller_clients = {profile.pk: self._client(profile.user) for profile in sellers}
        now = timezone.now()
        for index, order_id in enumerate(created):
            Order.objects.filter(pk=order_id).update(created_at=now - timedelta(days=13 - (index * 13 // len(created)), hours=rng.randint(0, 9)))
            steps = ["shipped", "delivered", "completed"][: rng.choice([0, 1, 2, 3, 3])]
            for suborder in SellerOrder.objects.filter(order_id=order_id):
                client = seller_clients[suborder.seller_id]
                for step in steps:
                    client.post(f"/api/v1/seller/orders/{suborder.pk}/fulfillment/", {"status": step, "carrier": "Pathao Courier", "tracking_number": f"PTH{rng.randint(100000, 999999)}"}, format="json")

    def _print_accounts(self, password):
        self.stdout.write("\nDemo accounts (password: %s)" % password)
        for local, portal in [("customer", "Customer  http://localhost:3000"), ("seller", "Seller    http://localhost:3001"), ("admin", "Admin     http://localhost:3002"), ("manager", "Manager   http://localhost:3003"), ("owner", "Owner     http://localhost:3004")]:
            self.stdout.write(f"  {portal}  →  {local}@{DEMO_DOMAIN}")
