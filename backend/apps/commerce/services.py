from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.catalog.models import Product, ProductVariant
from apps.commerce.models import (
    Cart,
    CartItem,
    CommissionRule,
    Coupon,
    CouponRedemption,
    Order,
    OrderItem,
    Payment,
    ReturnRequest,
    SellerEarning,
    SellerOrder,
    ShippingRule,
)
from apps.platform.audit import record_audit
from apps.platform.models import Notification

CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def unit_price(product, variant):
    return variant.price if variant and variant.price is not None else product.price


def commission_percentage(seller, category):
    rules = CommissionRule.objects.filter(is_active=True)
    for seller_filter, category_filter in (
        (seller, category),
        (seller, None),
        (None, category),
        (None, None),
    ):
        rule = rules.filter(seller=seller_filter, category=category_filter).order_by("-created_at").first()
        if rule:
            return rule.percentage
    return settings.DEFAULT_PLATFORM_COMMISSION_PERCENT


@transaction.atomic
def create_order(request, address_id, payment_method, idempotency_key, coupon_code=""):
    user = request.user
    type(user).objects.select_for_update().get(pk=user.pk)
    existing = Order.objects.filter(customer=user, idempotency_key=str(idempotency_key)).first()
    if existing:
        return existing
    try:
        address = user.shipping_addresses.get(pk=address_id)
    except user.shipping_addresses.model.DoesNotExist:
        raise NotFound("Shipping address not found.")
    cart = Cart.objects.filter(user=user).first()
    if not cart:
        raise ValidationError({"cart": "Your cart is empty."})
    cart_items = list(cart.items.select_for_update().select_related("product__seller__user", "product__category", "variant").order_by("product_id", "variant_id"))
    if not cart_items:
        raise ValidationError({"cart": "Your cart is empty."})

    groups = defaultdict(list)
    subtotal = Decimal("0")
    for cart_item in cart_items:
        product = Product.objects.select_for_update().select_related("seller", "category").get(pk=cart_item.product_id)
        variant = None
        if cart_item.variant_id:
            variant = ProductVariant.objects.select_for_update().get(pk=cart_item.variant_id, product=product)
        if product.status != Product.Status.PUBLISHED or not product.seller.is_active:
            raise ValidationError({"cart": f"{product.name} is no longer available."})
        if variant:
            if not variant.is_active or variant.stock_quantity < cart_item.quantity:
                raise ValidationError({"cart": f"Insufficient stock for {product.name} ({variant.name})."})
        elif product.stock_quantity < cart_item.quantity:
            raise ValidationError({"cart": f"Insufficient stock for {product.name}."})
        price = money(unit_price(product, variant))
        line_total = money(price * cart_item.quantity)
        subtotal += line_total
        groups[product.seller_id].append((cart_item, product, variant, price, line_total))

    subtotal = money(subtotal)
    coupon = None
    discount_total = Decimal("0")
    if coupon_code:
        try:
            coupon = Coupon.objects.select_for_update().get(code__iexact=coupon_code.strip(), is_active=True)
        except Coupon.DoesNotExist:
            raise ValidationError({"coupon": "This coupon is not valid."})
        now = timezone.now()
        if coupon.starts_at and coupon.starts_at > now or coupon.ends_at and coupon.ends_at < now:
            raise ValidationError({"coupon": "This coupon is not currently available."})
        if coupon.max_redemptions is not None and coupon.redemption_count >= coupon.max_redemptions:
            raise ValidationError({"coupon": "This coupon has reached its redemption limit."})
        if CouponRedemption.objects.filter(coupon=coupon, user=user).exists():
            raise ValidationError({"coupon": "This coupon has already been used by your account."})
        if subtotal < coupon.minimum_subtotal:
            raise ValidationError({"coupon": "The order does not meet the minimum subtotal for this coupon."})
        if coupon.discount_type == Coupon.DiscountType.PERCENT:
            discount_total = money(subtotal * coupon.discount_value / Decimal("100"))
        else:
            discount_total = money(coupon.discount_value)
        discount_total = min(discount_total, subtotal)

    shipping_rule = ShippingRule.objects.filter(country_code=address.country_code, is_active=True).first()
    per_seller_shipping = shipping_rule.amount if shipping_rule else Decimal("0")
    shipping_total = money(per_seller_shipping * len(groups))
    total = money(subtotal - discount_total + shipping_total)
    order = Order.objects.create(
        order_number=f"SLX-{uuid.uuid4().hex[:12].upper()}",
        idempotency_key=str(idempotency_key),
        customer=user,
        payment_method=payment_method,
        subtotal=subtotal,
        discount_total=discount_total,
        shipping_total=shipping_total,
        total=total,
        shipping_snapshot={
            "recipient_name": address.recipient_name,
            "phone_number": address.phone_number,
            "address_line1": address.address_line1,
            "address_line2": address.address_line2,
            "city": address.city,
            "region": address.region,
            "postal_code": address.postal_code,
            "country_code": address.country_code,
        },
    )

    seller_totals = []
    for seller_id, lines in groups.items():
        seller_subtotal = money(sum((line[4] for line in lines), Decimal("0")))
        seller_discount = money(discount_total * seller_subtotal / subtotal) if subtotal else Decimal("0")
        seller_commission = Decimal("0")
        for _, product, _, _, line_total in lines:
            allocated = money(discount_total * line_total / subtotal) if subtotal else Decimal("0")
            seller_commission += money(max(line_total - allocated, Decimal("0")) * commission_percentage(product.seller, product.category) / Decimal("100"))
        seller_totals.append((seller_id, lines, seller_subtotal, seller_discount, money(seller_commission)))

    # Allocate rounding residue to the final seller so split totals equal the parent order exactly.
    if seller_totals and discount_total:
        allocated_total = sum((entry[3] for entry in seller_totals), Decimal("0"))
        seller_id, lines, group_subtotal, group_discount, group_commission = seller_totals[-1]
        residue = discount_total - allocated_total
        seller_totals[-1] = (seller_id, lines, group_subtotal, group_discount + residue, group_commission)

    for seller_id, lines, seller_subtotal, seller_discount, seller_commission in seller_totals:
        seller = lines[0][1].seller
        seller_order = SellerOrder.objects.create(
            order=order,
            seller=seller,
            subtotal=seller_subtotal,
            discount_amount=seller_discount,
            shipping_amount=per_seller_shipping,
            commission_amount=seller_commission,
            net_earnings=money(seller_subtotal - seller_discount - seller_commission),
        )
        for cart_item, product, variant, price, line_total in lines:
            OrderItem.objects.create(
                seller_order=seller_order,
                product=product,
                variant=variant,
                product_name=product.name,
                sku=variant.sku if variant else product.sku,
                unit_price=price,
                quantity=cart_item.quantity,
                line_total=line_total,
            )
            if variant:
                variant.stock_quantity = F("stock_quantity") - cart_item.quantity
                variant.save(update_fields=["stock_quantity"])
            else:
                product.stock_quantity = F("stock_quantity") - cart_item.quantity
                product.save(update_fields=["stock_quantity"])
        Notification.objects.create(
            user=seller.user,
            category="seller_order",
            title="New order received",
            body=f"Order {order.order_number} contains items from your store.",
            payload={"seller_order_id": str(seller_order.pk)},
        )
    Payment.objects.create(order=order, method=payment_method, amount=total, status=Payment.Status.PENDING)
    if coupon:
        CouponRedemption.objects.create(coupon=coupon, user=user, order=order)
        Coupon.objects.filter(pk=coupon.pk).update(redemption_count=F("redemption_count") + 1)
    CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()
    Notification.objects.create(
        user=user,
        category="order",
        title="Order confirmed",
        body=f"Your order {order.order_number} has been placed.",
        payload={"order_id": str(order.pk)},
    )
    record_audit(request, "order.created", resource_type="order", resource_id=order.pk, metadata={"seller_count": len(groups), "total": str(total)})
    return order


@transaction.atomic
def cancel_order(request, order):
    order = Order.objects.select_for_update().get(pk=order.pk, customer=request.user)
    suborders = list(order.seller_orders.select_for_update().prefetch_related("items"))
    if not suborders or any(row.status not in [SellerOrder.Status.PROCESSING] for row in suborders):
        raise ValidationError("This order can no longer be cancelled. Request a return instead.")
    for seller_order in suborders:
        for item in seller_order.items.all():
            if item.variant_id:
                ProductVariant.objects.filter(pk=item.variant_id).update(stock_quantity=F("stock_quantity") + item.quantity)
            elif item.product_id:
                Product.objects.filter(pk=item.product_id).update(stock_quantity=F("stock_quantity") + item.quantity)
        seller_order.status = SellerOrder.Status.CANCELLED
        seller_order.save(update_fields=["status"])
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    record_audit(request, "order.cancelled", resource_type="order", resource_id=order.pk)
    return order


@transaction.atomic
def update_seller_order(request, seller_order, status_value, carrier="", tracking_number=""):
    seller_order = SellerOrder.objects.select_for_update().get(pk=seller_order.pk, seller=request.user.seller_profile)
    allowed = {
        SellerOrder.Status.PROCESSING: {SellerOrder.Status.SHIPPED, SellerOrder.Status.CANCELLED},
        SellerOrder.Status.SHIPPED: {SellerOrder.Status.DELIVERED},
        SellerOrder.Status.DELIVERED: {SellerOrder.Status.COMPLETED},
    }
    if status_value not in allowed.get(seller_order.status, set()):
        raise ValidationError({"status": "This fulfillment status transition is not allowed."})
    if status_value == SellerOrder.Status.SHIPPED and not tracking_number.strip():
        raise ValidationError({"tracking_number": "Tracking information is required when shipping an order."})
    seller_order.status = status_value
    if carrier:
        seller_order.carrier = carrier[:100]
    if tracking_number:
        seller_order.tracking_number = tracking_number[:120]
    if status_value == SellerOrder.Status.CANCELLED:
        for item in seller_order.items.select_related("product", "variant"):
            if item.variant_id:
                ProductVariant.objects.filter(pk=item.variant_id).update(stock_quantity=F("stock_quantity") + item.quantity)
            elif item.product_id:
                Product.objects.filter(pk=item.product_id).update(stock_quantity=F("stock_quantity") + item.quantity)
    if status_value == SellerOrder.Status.COMPLETED:
        seller_order.completed_at = timezone.now()
        if seller_order.net_earnings > 0:
            SellerEarning.objects.get_or_create(
                seller=seller_order.seller,
                seller_order=seller_order,
                entry_type=SellerEarning.EntryType.SALE,
                defaults={"amount": seller_order.net_earnings, "reference": seller_order.order.order_number},
            )
    seller_order.save(update_fields=["status", "carrier", "tracking_number", "completed_at"])
    order = seller_order.order
    statuses = list(order.seller_orders.values_list("status", flat=True))
    if statuses and all(value == SellerOrder.Status.CANCELLED for value in statuses):
        order.status = Order.Status.CANCELLED
    elif statuses and all(value in [SellerOrder.Status.COMPLETED, SellerOrder.Status.REFUNDED] for value in statuses):
        order.status = Order.Status.COMPLETED
    elif SellerOrder.Status.RETURN_REQUESTED in statuses:
        order.status = Order.Status.RETURN_REQUESTED
    elif SellerOrder.Status.DELIVERED in statuses:
        order.status = Order.Status.DELIVERED
    elif SellerOrder.Status.SHIPPED in statuses:
        order.status = Order.Status.SHIPPED
    order.save(update_fields=["status", "updated_at"])
    Notification.objects.create(
        user=order.customer,
        category="order_fulfillment",
        title="Order status updated",
        body=f"{order.order_number} is now {seller_order.get_status_display().lower()}.",
        payload={"order_id": str(order.pk), "seller_order_id": str(seller_order.pk), "status": seller_order.status},
    )
    record_audit(request, "seller_order.status_updated", resource_type="seller_order", resource_id=seller_order.pk, metadata={"status": status_value})
    return seller_order


@transaction.atomic
def request_return(request, seller_order_id, reason):
    try:
        seller_order = SellerOrder.objects.select_for_update().select_related("order").get(pk=seller_order_id, order__customer=request.user)
    except SellerOrder.DoesNotExist:
        raise NotFound()
    if seller_order.status not in [SellerOrder.Status.DELIVERED, SellerOrder.Status.COMPLETED]:
        raise ValidationError("A return can only be requested for a delivered order.")
    if seller_order.return_requests.filter(status__in=[ReturnRequest.Status.REQUESTED, ReturnRequest.Status.APPROVED]).exists():
        raise ValidationError("A return request is already in progress.")
    return_request = ReturnRequest.objects.create(seller_order=seller_order, customer=request.user, reason=reason)
    seller_order.status = SellerOrder.Status.RETURN_REQUESTED
    seller_order.save(update_fields=["status"])
    seller_order.order.status = Order.Status.RETURN_REQUESTED
    seller_order.order.save(update_fields=["status", "updated_at"])
    Notification.objects.create(
        user=seller_order.seller.user,
        category="return_request",
        title="Return request received",
        body=f"A return was requested for order {seller_order.order.order_number}.",
        payload={"return_request_id": str(return_request.pk)},
    )
    record_audit(request, "return.requested", resource_type="seller_order", resource_id=seller_order.pk)
    return return_request
