from rest_framework import serializers
from decimal import Decimal

from apps.catalog.models import Product, ProductVariant
from apps.commerce.models import (
    Address,
    CartItem,
    CommissionRule,
    Order,
    OrderItem,
    Payment,
    ReturnRequest,
    SellerOrder,
    SellerPayoutRequest,
    ShippingRule,
    WishlistEntry,
)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = ["user", "created_at", "updated_at"]
        read_only_fields = ["id"]


class CartItemInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField(required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, max_value=99)

    def validate(self, attrs):
        try:
            product = Product.objects.select_related("seller").get(
                pk=attrs["product_id"], status=Product.Status.PUBLISHED, seller__is_active=True,
            )
        except Product.DoesNotExist:
            raise serializers.ValidationError({"product_id": "This product is not available."})
        variant = None
        if attrs.get("variant_id"):
            try:
                variant = ProductVariant.objects.get(pk=attrs["variant_id"], product=product, is_active=True)
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError({"variant_id": "This product option is not available."})
        available = variant.stock_quantity if variant else product.stock_quantity
        if available < attrs["quantity"]:
            raise serializers.ValidationError({"quantity": "Requested quantity is not available."})
        attrs["product"] = product
        attrs["variant"] = variant
        return attrs


class CartItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["quantity"]

    def validate_quantity(self, quantity):
        item = self.instance
        stock = item.variant.stock_quantity if item.variant_id else item.product.stock_quantity
        if quantity > stock:
            raise serializers.ValidationError("Requested quantity is not available.")
        return quantity


class WishlistInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()

    def validate_product_id(self, product_id):
        try:
            return Product.objects.get(pk=product_id, status=Product.Status.PUBLISHED, seller__is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("This product is not available.")


class CheckoutSerializer(serializers.Serializer):
    address_id = serializers.UUIDField()
    payment_method = serializers.ChoiceField(choices=Order.PaymentMethod.choices)
    idempotency_key = serializers.UUIDField()
    coupon_code = serializers.CharField(required=False, allow_blank=True, max_length=40)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product_name", "sku", "unit_price", "quantity", "line_total"]


class SellerOrderReadSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.business_name")
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = SellerOrder
        fields = ["id", "order_number", "seller_name", "status", "subtotal", "discount_amount", "shipping_amount", "commission_amount", "net_earnings", "carrier", "tracking_number", "created_at", "items"]


class CustomerOrderSerializer(serializers.ModelSerializer):
    seller_orders = SellerOrderReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "order_number", "status", "payment_method", "subtotal", "discount_total", "shipping_total", "total", "shipping_snapshot", "created_at", "seller_orders"]


class PaymentHistorySerializer(serializers.ModelSerializer):
    order_id = serializers.UUIDField(source="order.id", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "order_id", "order_number", "method", "status", "amount", "currency", "created_at"]


class SellerFulfillmentSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SellerOrder.Status.choices)
    carrier = serializers.CharField(required=False, allow_blank=True, max_length=100)
    tracking_number = serializers.CharField(required=False, allow_blank=True, max_length=120)


class ReturnRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=8, max_length=2000)


class ReturnRequestSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="seller_order.order.order_number", read_only=True)

    class Meta:
        model = ReturnRequest
        fields = ["id", "seller_order", "order_number", "reason", "status", "resolution_note", "created_at", "updated_at"]
        read_only_fields = ["id", "seller_order", "order_number", "status", "resolution_note", "created_at", "updated_at"]


class SellerReturnDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[("approved", "Approve"), ("rejected", "Reject")])
    resolution_note = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class PayoutRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerPayoutRequest
        fields = ["id", "amount", "status", "requested_at", "reviewed_at", "review_reason"]
        read_only_fields = ["id", "status", "requested_at", "reviewed_at", "review_reason"]


class PayoutRequestInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, amount):
        if amount < Decimal("0.01"):
            raise serializers.ValidationError("Amount must be at least 0.01.")
        return amount


class CommissionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionRule
        fields = ["id", "seller", "category", "percentage", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class ShippingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingRule
        fields = ["id", "country_code", "amount", "is_active"]
