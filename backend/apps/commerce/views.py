from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.authorization.models import Role
from apps.catalog.models import Product
from apps.catalog.serializers import PublicProductSerializer
from apps.commerce.models import (
    Address,
    Cart,
    CartItem,
    CommissionRule,
    Coupon,
    Order,
    ReturnRequest,
    SellerEarning,
    SellerOrder,
    SellerPayoutRequest,
    ShippingRule,
    WishlistEntry,
)
from apps.commerce.serializers import (
    AddressSerializer,
    CartItemInputSerializer,
    CartItemUpdateSerializer,
    CheckoutSerializer,
    CommissionRuleSerializer,
    CustomerOrderSerializer,
    OrderItemSerializer,
    PaymentHistorySerializer,
    PayoutRequestInputSerializer,
    PayoutRequestSerializer,
    ReturnRequestCreateSerializer,
    ReturnRequestSerializer,
    SellerFulfillmentSerializer,
    SellerOrderReadSerializer,
    SellerReturnDecisionSerializer,
    ShippingRuleSerializer,
    WishlistInputSerializer,
)
from apps.commerce.schema import CartSchema, CouponInputSchema
from apps.commerce.services import cancel_order, create_order, request_return, update_seller_order
from apps.platform.audit import record_audit
from apps.sellers.permissions import IsActiveSeller


def cart_payload(request, cart):
    rows = []
    subtotal = Decimal("0.00")
    for item in cart.items.select_related("product__category", "product__brand", "product__seller", "variant").prefetch_related("product__images"):
        product = item.product
        price = item.variant.price if item.variant_id and item.variant.price is not None else product.price
        line_total = price * item.quantity
        subtotal += line_total
        rows.append({
            "id": item.pk,
            "product": PublicProductSerializer(product, context={"request": request}).data,
            "variant": {"id": str(item.variant_id), "name": item.variant.name, "options": item.variant.options} if item.variant_id else None,
            "quantity": item.quantity,
            "unit_price": price,
            "line_total": line_total,
        })
    return {"items": rows, "subtotal": subtotal, "item_count": sum(item["quantity"] for item in rows)}


class AddressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        is_default = serializer.validated_data.get("is_default", False)
        if is_default or not Address.objects.filter(user=self.request.user).exists():
            Address.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
            is_default = True
        serializer.save(user=self.request.user, is_default=is_default)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        if serializer.validated_data.get("is_default"):
            Address.objects.filter(user=self.request.user, is_default=True).exclude(pk=self.get_object().pk).update(is_default=False)
        serializer.save()


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=CartSchema)
    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        return Response(cart_payload(request, cart))

    @extend_schema(request=CartItemInputSerializer, responses=CartSchema)
    def post(self, request):
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        product = serializer.validated_data["product"]
        variant = serializer.validated_data["variant"]
        quantity = serializer.validated_data["quantity"]
        lookup = {"cart": cart, "product": product, "variant": variant}
        if variant is None:
            lookup["variant__isnull"] = True
        item = CartItem.objects.filter(**lookup).first()
        new_quantity = quantity + (item.quantity if item else 0)
        stock = variant.stock_quantity if variant else product.stock_quantity
        if new_quantity > stock:
            raise ValidationError({"quantity": "Requested quantity is greater than available stock."})
        if item:
            item.quantity = new_quantity
            item.save(update_fields=["quantity"])
        else:
            item = CartItem.objects.create(cart=cart, product=product, variant=variant, quantity=quantity)
        return Response(cart_payload(request, cart), status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CartItemUpdateSerializer, responses=CartSchema)
    def patch(self, request, item_id):
        item = get_object_or_404(CartItem.objects.select_related("variant", "product"), pk=item_id, cart__user=request.user)
        serializer = CartItemUpdateSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(cart_payload(request, item.cart))

    @extend_schema(request=None, responses=CartSchema)
    def delete(self, request, item_id):
        item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
        cart = item.cart
        item.delete()
        return Response(cart_payload(request, cart))


class WishlistView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=PublicProductSerializer(many=True))
    def get(self, request):
        products = Product.objects.filter(wishlisted_by__user=request.user, status=Product.Status.PUBLISHED, seller__is_active=True).select_related("category", "brand", "seller").prefetch_related("images", "variants")
        return Response(PublicProductSerializer(products, many=True, context={"request": request}).data)

    @extend_schema(request=WishlistInputSerializer, responses={200: dict, 201: dict})
    def post(self, request):
        serializer = WishlistInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["product_id"]
        _, created = WishlistEntry.objects.get_or_create(user=request.user, product=product)
        return Response({"detail": "Added to wishlist."}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class WishlistRemoveView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None, 404: None})
    def delete(self, request, product_id):
        entry = get_object_or_404(WishlistEntry, user=request.user, product_id=product_id)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CouponValidateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CouponInputSchema, responses={200: dict})
    def post(self, request):
        try:
            subtotal = Decimal(str(request.data.get("subtotal", "0")))
        except (InvalidOperation, ValueError):
            raise ValidationError({"subtotal": "Enter a valid subtotal."})
        if subtotal < 0:
            raise ValidationError({"subtotal": "Subtotal cannot be negative."})
        code = str(request.data.get("code", "")).strip()
        coupon = Coupon.objects.filter(code__iexact=code, is_active=True).first()
        now = timezone.now()
        if not coupon or coupon.starts_at and coupon.starts_at > now or coupon.ends_at and coupon.ends_at < now:
            raise ValidationError({"code": "This coupon is not currently valid."})
        if coupon.max_redemptions is not None and coupon.redemption_count >= coupon.max_redemptions:
            raise ValidationError({"code": "This coupon has reached its redemption limit."})
        if coupon.minimum_subtotal > subtotal:
            raise ValidationError({"subtotal": "The order does not meet the coupon minimum."})
        if coupon.redemptions.filter(user=request.user).exists():
            raise ValidationError({"code": "This coupon has already been used by your account."})
        discount = subtotal * coupon.discount_value / Decimal("100") if coupon.discount_type == Coupon.DiscountType.PERCENT else coupon.discount_value
        discount = min(discount, subtotal).quantize(Decimal("0.01"))
        return Response({"code": coupon.code, "discount": discount, "subtotal": subtotal, "total_after_discount": subtotal - discount})


class ShippingQuoteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: dict})
    def get(self, request):
        address_id = request.query_params.get("address_id")
        address = get_object_or_404(Address, pk=address_id, user=request.user)
        cart = Cart.objects.filter(user=request.user).first()
        seller_count = cart.items.filter(product__status=Product.Status.PUBLISHED, product__seller__is_active=True).values("product__seller_id").distinct().count() if cart else 0
        shipping_rule = ShippingRule.objects.filter(country_code=address.country_code, is_active=True).first()
        per_seller = shipping_rule.amount if shipping_rule else Decimal("0.00")
        return Response({"country_code": address.country_code, "seller_count": seller_count, "per_seller": per_seller, "shipping_total": per_seller * seller_count, "currency": "BDT"})


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CheckoutSerializer, responses=CustomerOrderSerializer)
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = create_order(
            request,
            serializer.validated_data["address_id"],
            serializer.validated_data["payment_method"],
            serializer.validated_data["idempotency_key"],
            serializer.validated_data.get("coupon_code", ""),
        )
        order = Order.objects.prefetch_related("seller_orders__items").get(pk=order.pk)
        return Response(CustomerOrderSerializer(order).data, status=status.HTTP_201_CREATED)


class CustomerOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerOrderSerializer

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).prefetch_related("seller_orders__seller", "seller_orders__items")


class CustomerOrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CustomerOrderSerializer
    lookup_field = "pk"

    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).prefetch_related("seller_orders__seller", "seller_orders__items")


class PaymentHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentHistorySerializer

    def get_queryset(self):
        from apps.commerce.models import Payment
        return Payment.objects.filter(order__customer=self.request.user).select_related("order").order_by("-created_at")


class CustomerOrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=CustomerOrderSerializer)
    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id, customer=request.user)
        order = cancel_order(request, order)
        return Response(CustomerOrderSerializer(order).data)


class InvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={(200, "text/html"): OpenApiResponse(response=str, description="Printable order invoice")})
    def get(self, request, order_id):
        order = get_object_or_404(Order.objects.prefetch_related("seller_orders__items"), pk=order_id, customer=request.user)
        return render(request, "commerce/invoice.html", {"order": order}, content_type="text/html")


class ReturnRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ReturnRequestCreateSerializer, responses=ReturnRequestSerializer)
    def post(self, request, seller_order_id):
        serializer = ReturnRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return_request = request_return(request, seller_order_id, serializer.validated_data["reason"])
        return Response(ReturnRequestSerializer(return_request).data, status=status.HTTP_201_CREATED)


class SellerOrderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    serializer_class = CustomerOrderSerializer

    def get_queryset(self):
        return Order.objects.filter(seller_orders__seller=self.request.user.seller_profile).distinct().prefetch_related("seller_orders__seller", "seller_orders__items")


class SellerSuborderListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    serializer_class = SellerOrderReadSerializer

    def get_queryset(self):
        return SellerOrder.objects.filter(seller=self.request.user.seller_profile).select_related("order", "seller").prefetch_related("items").order_by("-created_at")


class SellerFulfillmentView(APIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]

    @extend_schema(request=SellerFulfillmentSerializer, responses=SellerOrderReadSerializer)
    def post(self, request, seller_order_id):
        seller_order = get_object_or_404(SellerOrder, pk=seller_order_id, seller=request.user.seller_profile)
        serializer = SellerFulfillmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seller_order = update_seller_order(
            request, seller_order,
            serializer.validated_data["status"],
            serializer.validated_data.get("carrier", ""),
            serializer.validated_data.get("tracking_number", ""),
        )
        return Response(SellerOrderReadSerializer(seller_order).data)


class SellerReturnListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]
    serializer_class = ReturnRequestSerializer

    def get_queryset(self):
        return ReturnRequest.objects.filter(seller_order__seller=self.request.user.seller_profile).select_related("seller_order__order")


class SellerReturnDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]

    @extend_schema(request=SellerReturnDecisionSerializer, responses=ReturnRequestSerializer)
    @transaction.atomic
    def post(self, request, return_id):
        return_request = get_object_or_404(ReturnRequest.objects.select_for_update(), pk=return_id, seller_order__seller=request.user.seller_profile)
        if return_request.status != ReturnRequest.Status.REQUESTED:
            raise ValidationError("This return request has already been reviewed.")
        serializer = SellerReturnDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        return_request.status = decision
        return_request.resolution_note = serializer.validated_data.get("resolution_note", "")
        return_request.save(update_fields=["status", "resolution_note", "updated_at"])
        if decision == ReturnRequest.Status.REJECTED:
            return_request.seller_order.status = SellerOrder.Status.DELIVERED
            return_request.seller_order.save(update_fields=["status"])
            return_request.seller_order.order.status = Order.Status.DELIVERED
            return_request.seller_order.order.save(update_fields=["status", "updated_at"])
        from apps.platform.models import Notification
        Notification.objects.create(user=return_request.customer, category="return_request", title="Return request update", body=f"Your return request was {decision}.", payload={"return_request_id": str(return_request.pk)})
        record_audit(request, "return.reviewed", resource_type="return_request", resource_id=return_request.pk, metadata={"decision": decision})
        return Response(ReturnRequestSerializer(return_request).data)


class CommissionRuleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CommissionRuleSerializer

    def _require_owner(self):
        if not self.request.user.role_assignments.filter(role__key=Role.Key.OWNER).exists():
            raise PermissionDenied("Only the platform Owner can configure commission rules.")

    def get_queryset(self):
        self._require_owner()
        return CommissionRule.objects.select_related("seller", "category").all()

    def perform_create(self, serializer):
        self._require_owner()
        serializer.save()


class ShippingRuleListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ShippingRuleSerializer

    def _require_owner(self):
        if not self.request.user.role_assignments.filter(role__key=Role.Key.OWNER).exists():
            raise PermissionDenied("Only the platform Owner can configure shipping rules.")

    def get_queryset(self):
        self._require_owner()
        return ShippingRule.objects.all()

    def perform_create(self, serializer):
        self._require_owner()
        serializer.save()
