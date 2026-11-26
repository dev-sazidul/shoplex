import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.catalog.models import Category, Product, ProductVariant
from apps.platform.models import SellerProfile


class Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shipping_addresses")
    label = models.CharField(max_length=60, default="Home")
    recipient_name = models.CharField(max_length=160)
    phone_number = models.CharField(max_length=30)
    address_line1 = models.CharField(max_length=240)
    address_line2 = models.CharField(max_length=240, blank=True)
    city = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country_code = models.CharField(max_length=2, default="BD")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]
        indexes = [models.Index(fields=["user", "is_default"])]


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    updated_at = models.DateTimeField(auto_now=True)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_lines")
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.CASCADE, related_name="cart_lines")
    quantity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["cart", "product", "variant"], name="uniq_cart_product_variant")]
        indexes = [models.Index(fields=["cart", "added_at"])]


class WishlistEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_entries")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="uniq_user_wishlist_product")]


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percent"
        FIXED = "fixed", "Fixed amount"

    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(max_length=8, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    minimum_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    redemption_count = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(discount_value__gt=0), name="coupon_value_positive")]


class CouponRedemption(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name="redemptions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="coupon_redemptions")
    order = models.OneToOneField("Order", on_delete=models.PROTECT, related_name="coupon_redemption")
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["coupon", "user"], name="uniq_coupon_user_redemption")]


class ShippingRule(models.Model):
    country_code = models.CharField(max_length=2, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    is_active = models.BooleanField(default=True)


class CommissionRule(models.Model):
    seller = models.ForeignKey(SellerProfile, null=True, blank=True, on_delete=models.CASCADE, related_name="commission_rules")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE, related_name="commission_rules")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.CASCADE, related_name="commission_rules")
    percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(percentage__gte=0) & Q(percentage__lte=100), name="commission_percentage_range")]
        indexes = [models.Index(fields=["seller", "category", "is_active"]), models.Index(fields=["product", "is_active"])]


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PAID = "paid", "Paid"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        COMPLETED = "completed", "Completed"
        PAYMENT_FAILED = "payment_failed", "Payment failed"
        CANCELLED = "cancelled", "Cancelled"
        RETURN_REQUESTED = "return_requested", "Return requested"
        RETURNED = "returned", "Returned"
        REFUND_PENDING = "refund_pending", "Refund pending"
        REFUNDED = "refunded", "Refunded"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on delivery"
        SSLCOMMERZ = "sslcommerz", "SSLCommerz"
        BKASH = "bkash", "bKash"
        NAGAD = "nagad", "Nagad"
        CARD = "card", "Debit / credit card"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=24, unique=True, db_index=True)
    idempotency_key = models.CharField(max_length=64, blank=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING, db_index=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["customer", "idempotency_key"], condition=~Q(idempotency_key=""), name="uniq_customer_checkout_key")]
        indexes = [models.Index(fields=["customer", "created_at"]), models.Index(fields=["customer", "status"])]


class SellerOrder(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PAID = "paid", "Paid"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        COMPLETED = "completed", "Completed"
        PAYMENT_FAILED = "payment_failed", "Payment failed"
        CANCELLED = "cancelled", "Cancelled"
        RETURN_REQUESTED = "return_requested", "Return requested"
        RETURNED = "returned", "Returned"
        REFUND_PENDING = "refund_pending", "Refund pending"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="seller_orders")
    seller = models.ForeignKey(SellerProfile, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING, db_index=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    net_earnings = models.DecimalField(max_digits=12, decimal_places=2)
    carrier = models.CharField(max_length=100, blank=True)
    tracking_number = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["order", "seller"], name="uniq_order_seller_suborder")]
        indexes = [models.Index(fields=["seller", "status", "created_at"])]


class OrderItem(models.Model):
    seller_order = models.ForeignKey(SellerOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="order_lines")
    variant = models.ForeignKey(ProductVariant, null=True, blank=True, on_delete=models.SET_NULL, related_name="order_lines")
    product_name = models.CharField(max_length=180)
    sku = models.CharField(max_length=80, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name="order_item_quantity_positive")]


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUND_PENDING = "refund_pending", "Refund pending"
        REFUNDED = "refunded", "Refunded"

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name="payment")
    method = models.CharField(max_length=20, choices=Order.PaymentMethod.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="BDT")
    provider_reference = models.CharField(max_length=120, blank=True, db_index=True)
    gateway_session_id = models.CharField(max_length=120, blank=True)
    gateway_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PaymentWebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=24, db_index=True)
    event_id = models.CharField(max_length=120, unique=True)
    transaction_reference = models.CharField(max_length=120, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-processed_at"]


class SellerEarning(models.Model):
    class EntryType(models.TextChoices):
        SALE = "sale", "Completed seller order"
        REFUND = "refund", "Refund deduction"
        ADJUSTMENT = "adjustment", "Authorized adjustment"

    seller = models.ForeignKey(SellerProfile, on_delete=models.PROTECT, related_name="earnings_ledger")
    seller_order = models.ForeignKey(SellerOrder, null=True, blank=True, on_delete=models.PROTECT, related_name="earning_entries")
    entry_type = models.CharField(max_length=12, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    reference = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="seller_earning_amount_positive"),
            models.UniqueConstraint(fields=["seller_order", "entry_type"], condition=Q(entry_type="sale"), name="uniq_seller_order_sale_earning"),
        ]
        indexes = [models.Index(fields=["seller", "entry_type", "created_at"])]


class SellerPayoutRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(SellerProfile, on_delete=models.PROTECT, related_name="payout_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-requested_at"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="payout_request_amount_positive")]
        indexes = [models.Index(fields=["seller", "status", "requested_at"])]


class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RECEIVED = "received", "Received"
        REFUNDED = "refunded", "Refunded"

    seller_order = models.ForeignKey(SellerOrder, on_delete=models.PROTECT, related_name="return_requests")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="return_requests")
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["customer", "created_at"])]



class FinancialLedgerEntry(models.Model):
    class TransactionType(models.TextChoices):
        GROSS_SALE = "gross_sale", "Gross sale"
        PLATFORM_COMMISSION = "platform_commission", "Platform commission"
        SELLER_LIABILITY = "seller_liability", "Seller liability"
        REFUND_DEDUCTION = "refund_deduction", "Refund deduction"
        OPERATIONAL_EXPENSE = "operational_expense", "Operational expense"
        PAYMENT_FEE = "payment_fee", "Payment fee"
        SELLER_PAYOUT = "seller_payout", "Seller payout settlement"

    class Status(models.TextChoices):
        POSTED = "posted", "Posted"
        SETTLED = "settled", "Settled"
        REVERSED = "reversed", "Reversed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_type = models.CharField(max_length=24, choices=TransactionType.choices, db_index=True)
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="BDT")
    reference_id = models.CharField(max_length=120, db_index=True)
    order = models.ForeignKey(
        Order,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    payout_request = models.ForeignKey(
        SellerPayoutRequest,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.POSTED, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries_recorded",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="financial_ledger_amount_positive"),
        ]
        indexes = [
            models.Index(fields=["transaction_type", "status", "created_at"]),
            models.Index(fields=["reference_id", "transaction_type"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("Financial ledger records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Financial ledger records are append-only.")
