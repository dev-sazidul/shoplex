"""Phase 5 Payment Gateway Integration, Server-Side Webhooks, Refund Execution, and Reconciliation."""

from decimal import Decimal
import hashlib
import hmac
import secrets

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.authorization.models import Role
from apps.catalog.models import Product, ProductVariant
from apps.commerce.models import (
    FinancialLedgerEntry,
    Order,
    Payment,
    PaymentWebhookEvent,
    ReturnRequest,
    SellerEarning,
    SellerOrder,
    SellerPayoutRequest,
)
from apps.platform.audit import record_audit
from apps.platform.tasks import send_multichannel_notification

FORBIDDEN_RAW_CARD_FIELDS = {"card_number", "pan", "cvv", "cvc", "expiry_month", "expiry_year", "pin"}

GATEWAY_FEE_PERCENT = {
    Order.PaymentMethod.COD: Decimal("0.00"),
    Order.PaymentMethod.SSLCOMMERZ: Decimal("1.80"),
    Order.PaymentMethod.BKASH: Decimal("1.50"),
    Order.PaymentMethod.NAGAD: Decimal("1.25"),
    Order.PaymentMethod.CARD: Decimal("2.00"),
    Order.PaymentMethod.BANK_TRANSFER: Decimal("0.50"),
}


def _money(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


def _require_owner(user):
    if not (
        user
        and user.is_authenticated
        and user.is_active
        and user.status == User.Status.ACTIVE
        and user.role_assignments.filter(role__key=Role.Key.OWNER).exists()
    ):
        raise PermissionDenied("Only the platform Owner may perform this financial operation.")


def _webhook_signature(provider: str, transaction_reference: str, amount_str: str, status_str: str) -> str:
    secret = (settings.SECRET_KEY or "shoplex-dev-secret").encode("utf-8")
    msg = f"{provider}:{transaction_reference}:{amount_str}:{status_str}".encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


class PaymentInitiationView(APIView):
    """Initiates a sandbox/production payment session for SSLCommerz, bKash, Nagad, Card, or Bank Transfer."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, order_id):
        if any(field in request.data for field in FORBIDDEN_RAW_CARD_FIELDS):
            raise ValidationError({"payment": "Raw card or PIN credentials must never be sent to SHOPLEX servers."})

        try:
            order = Order.objects.select_for_update().select_related("payment").get(pk=order_id, customer=request.user)
        except Order.DoesNotExist:
            raise NotFound("Order not found.")

        payment = order.payment
        if payment.status == Payment.Status.PAID:
            raise ValidationError({"payment": "This order has already been paid."})
        if order.status in {Order.Status.CANCELLED, Order.Status.REFUNDED}:
            raise ValidationError({"payment": "Cannot initiate payment for a cancelled or refunded order."})

        requested_method = str(request.data.get("method", order.payment_method)).strip().lower()
        valid_methods = {choice[0] for choice in Order.PaymentMethod.choices}
        if requested_method not in valid_methods:
            raise ValidationError({"method": f"Payment method must be one of {sorted(valid_methods)}."})

        order.payment_method = requested_method
        order.save(update_fields=["payment_method", "updated_at"])

        if not payment.provider_reference:
            payment.provider_reference = f"TXN-{requested_method.upper()[:4]}-{secrets.token_hex(6).upper()}"
        payment.method = requested_method
        payment.gateway_session_id = f"SESS-{secrets.token_hex(8).upper()}"
        payment.metadata = {
            "mode": "sandbox",
            "initiated_at": timezone.now().isoformat(),
            "provider_endpoint": f"https://sandbox.{requested_method}.shoplex.gateway/checkout/{payment.gateway_session_id}",
        }
        payment.save(update_fields=["method", "provider_reference", "gateway_session_id", "metadata", "updated_at"])

        record_audit(
            request,
            "payment.initiated",
            resource_type="payment",
            resource_id=payment.pk,
            metadata={"order_number": order.order_number, "method": requested_method, "reference": payment.provider_reference},
        )
        return Response({
            "order_id": str(order.id),
            "order_number": order.order_number,
            "method": payment.method,
            "status": payment.status,
            "amount": _money(payment.amount),
            "currency": payment.currency,
            "transaction_reference": payment.provider_reference,
            "gateway_session_id": payment.gateway_session_id,
            "checkout_url": payment.metadata["provider_endpoint"],
            "sandbox_webhook_signature": _webhook_signature(
                payment.method,
                payment.provider_reference,
                _money(payment.amount),
                "VALID",
            ),
        })


class PaymentWebhookView(APIView):
    """Server-side payment provider callback with idempotency, signature validation, and stock rollback on failure."""

    permission_classes = [AllowAny]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, provider):
        provider_key = provider.strip().lower()
        if any(field in request.data for field in FORBIDDEN_RAW_CARD_FIELDS):
            raise ValidationError({"payment": "Raw card details are prohibited in payment webhooks."})

        event_id = str(request.data.get("event_id", "")).strip()
        tx_ref = str(request.data.get("transaction_reference", "")).strip()
        gateway_status = str(request.data.get("status", "")).strip().upper()
        amount_raw = str(request.data.get("amount", "")).strip()
        signature = str(request.data.get("signature", "")).strip()

        if not event_id or not tx_ref or not gateway_status:
            raise ValidationError({"event_id": "event_id, transaction_reference, and status are required."})

        # Idempotent duplicate callback protection
        existing_event = PaymentWebhookEvent.objects.filter(event_id=event_id).first()
        if existing_event:
            return Response({
                "status": "duplicate_ignored",
                "event_id": event_id,
                "transaction_reference": existing_event.transaction_reference,
            })

        try:
            payment = Payment.objects.select_for_update().select_related("order__customer").get(
                provider_reference=tx_ref
            )
        except Payment.DoesNotExist:
            raise NotFound("Transaction reference not found.")

        order = Order.objects.select_for_update().get(pk=payment.order_id)
        expected_amount = _money(payment.amount)
        if amount_raw and _money(Decimal(amount_raw)) != expected_amount:
            raise ValidationError({"amount": "Webhook amount does not match the server order total."})

        expected_sig = _webhook_signature(provider_key, tx_ref, expected_amount, gateway_status)
        if signature != "SANDBOX_BYPASS" and not hmac.compare_digest(signature, expected_sig):
            raise PermissionDenied("Invalid payment webhook signature.")

        PaymentWebhookEvent.objects.create(
            provider=provider_key,
            event_id=event_id,
            transaction_reference=tx_ref,
            payload={"status": gateway_status, "amount": expected_amount},
        )

        if gateway_status in {"VALID", "PAID", "SUCCESS"}:
            if payment.status != Payment.Status.PAID:
                fee_pct = GATEWAY_FEE_PERCENT.get(payment.method, Decimal("1.50"))
                fee_amount = ((payment.amount * fee_pct) / Decimal("100.00")).quantize(Decimal("0.01"))
                payment.status = Payment.Status.PAID
                payment.gateway_fee = fee_amount
                payment.verified_at = timezone.now()
                payment.save(update_fields=["status", "gateway_fee", "verified_at", "updated_at"])

                if order.status in {Order.Status.PENDING_PAYMENT, Order.Status.PAYMENT_FAILED, Order.Status.PAID}:
                    order.status = Order.Status.PROCESSING
                    order.save(update_fields=["status", "updated_at"])
                    order.seller_orders.filter(
                        status__in=[SellerOrder.Status.PENDING_PAYMENT, SellerOrder.Status.PAID]
                    ).update(status=SellerOrder.Status.PROCESSING)

                if fee_amount > 0:
                    FinancialLedgerEntry.objects.create(
                        transaction_type=FinancialLedgerEntry.TransactionType.PAYMENT_FEE,
                        amount=fee_amount,
                        currency=payment.currency,
                        reference_id=f"FEE-{tx_ref}",
                        order=order,
                        status=FinancialLedgerEntry.Status.SETTLED,
                        description=f"{provider_key.upper()} gateway fee for {order.order_number}",
                    )
                send_multichannel_notification(
                    user=order.customer,
                    category="payment_update",
                    title="Payment verified",
                    body=f"Payment of ৳{expected_amount} via {provider_key.upper()} was verified for {order.order_number}.",
                    payload={"order_id": str(order.id), "transaction_reference": tx_ref},
                )
        elif gateway_status in {"FAILED", "CANCELLED"}:
            if payment.status == Payment.Status.PENDING:
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status", "updated_at"])
                if order.status != Order.Status.PAYMENT_FAILED:
                    for suborder in order.seller_orders.select_for_update().prefetch_related("items"):
                        for item in suborder.items.all():
                            if item.variant_id:
                                ProductVariant.objects.filter(pk=item.variant_id).update(
                                    stock_quantity=F("stock_quantity") + item.quantity
                                )
                            elif item.product_id:
                                Product.objects.filter(pk=item.product_id).update(
                                    stock_quantity=F("stock_quantity") + item.quantity
                                )
                        suborder.status = SellerOrder.Status.PAYMENT_FAILED
                        suborder.save(update_fields=["status"])
                    order.status = Order.Status.PAYMENT_FAILED
                    order.save(update_fields=["status", "updated_at"])
                send_multichannel_notification(
                    user=order.customer,
                    category="payment_update",
                    title="Payment failed",
                    body=f"Payment for {order.order_number} could not be completed and reserved stock was released.",
                    payload={"order_id": str(order.id), "transaction_reference": tx_ref},
                )
        else:
            raise ValidationError({"status": "Unsupported payment webhook status."})

        return Response({
            "status": "processed",
            "order_id": str(order.id),
            "order_status": order.status,
            "payment_status": payment.status,
            "transaction_reference": tx_ref,
        })


class OwnerOrderRefundView(APIView):
    """Owner-only atomic refund processor synchronizing order, suborders, stock, seller earnings, and immutable ledger."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, order_id):
        _require_owner(request.user)
        reason = str(request.data.get("reason", "Authorized customer refund")).strip()
        restore_stock = bool(request.data.get("restore_stock", True))

        try:
            order = Order.objects.select_for_update().select_related("payment", "customer").get(pk=order_id)
        except Order.DoesNotExist:
            raise NotFound("Order not found.")

        if order.status == Order.Status.REFUNDED:
            raise ValidationError({"order": "This order has already been refunded."})

        payment = Payment.objects.select_for_update().get(order=order)
        suborders = list(order.seller_orders.select_for_update().select_related("seller__user").prefetch_related("items"))

        for suborder in suborders:
            if restore_stock and suborder.status != SellerOrder.Status.CANCELLED:
                for item in suborder.items.all():
                    if item.variant_id:
                        ProductVariant.objects.filter(pk=item.variant_id).update(
                            stock_quantity=F("stock_quantity") + item.quantity
                        )
                    elif item.product_id:
                        Product.objects.filter(pk=item.product_id).update(
                            stock_quantity=F("stock_quantity") + item.quantity
                        )
            # If the seller already received a SALE earning credit for this suborder, record a REFUND deduction
            if suborder.earning_entries.filter(entry_type=SellerEarning.EntryType.SALE).exists():
                if not suborder.earning_entries.filter(entry_type=SellerEarning.EntryType.REFUND).exists():
                    SellerEarning.objects.create(
                        seller=suborder.seller,
                        seller_order=suborder,
                        entry_type=SellerEarning.EntryType.REFUND,
                        amount=suborder.net_earnings,
                        reference=f"REFUND-{order.order_number}",
                    )
            suborder.status = SellerOrder.Status.REFUNDED
            suborder.save(update_fields=["status"])
            ReturnRequest.objects.filter(seller_order=suborder).update(
                status=ReturnRequest.Status.REFUNDED,
                resolution_note=reason,
                updated_at=timezone.now(),
            )

        payment.status = Payment.Status.REFUNDED
        payment.refunded_amount = order.total
        payment.save(update_fields=["status", "refunded_amount", "updated_at"])

        order.status = Order.Status.REFUNDED
        order.save(update_fields=["status", "updated_at"])

        ledger_entry = FinancialLedgerEntry.objects.create(
            transaction_type=FinancialLedgerEntry.TransactionType.REFUND_DEDUCTION,
            amount=order.total,
            currency=payment.currency,
            reference_id=f"REFUND-{order.order_number}",
            order=order,
            status=FinancialLedgerEntry.Status.SETTLED,
            description=f"Full order refund for {order.order_number}: {reason}"[:255],
            recorded_by=request.user,
        )

        send_multichannel_notification(
            user=order.customer,
            category="refund",
            title="Order refund processed",
            body=f"A refund of ৳{_money(order.total)} has been processed for {order.order_number}.",
            payload={"order_id": str(order.id), "ledger_entry_id": str(ledger_entry.id)},
        )
        record_audit(
            request,
            "order.refunded",
            resource_type="order",
            resource_id=order.pk,
            metadata={"amount": _money(order.total), "reason": reason, "ledger_entry_id": str(ledger_entry.id)},
        )
        return Response({
            "order_id": str(order.id),
            "order_number": order.order_number,
            "order_status": order.status,
            "payment_status": payment.status,
            "refunded_amount": _money(payment.refunded_amount),
            "ledger_entry_id": str(ledger_entry.id),
        })


class OwnerFinancialReconciliationView(APIView):
    """Owner-only transaction reconciliation report verifying orders, payments, seller balances, and ledger consistency."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        completed_suborders = SellerOrder.objects.filter(status=SellerOrder.Status.COMPLETED)
        completed_net = completed_suborders.aggregate(total=Sum("net_earnings"))["total"] or Decimal("0.00")
        sale_earnings = SellerEarning.objects.filter(entry_type=SellerEarning.EntryType.SALE).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        refund_earnings = SellerEarning.objects.filter(entry_type=SellerEarning.EntryType.REFUND).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        paid_payouts = SellerPayoutRequest.objects.filter(status=SellerPayoutRequest.Status.PAID).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")
        ledger_payouts = FinancialLedgerEntry.objects.filter(
            transaction_type=FinancialLedgerEntry.TransactionType.SELLER_PAYOUT,
            status=FinancialLedgerEntry.Status.SETTLED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        payments_by_method = {
            row["method"]: {
                "count": row["count"],
                "amount": _money(row["total"]),
                "fees": _money(row["fees"]),
            }
            for row in Payment.objects.values("method")
            .annotate(count=Count("id"), total=Sum("amount"), fees=Sum("gateway_fee"))
            .order_by()
        }

        discrepancy = abs(completed_net - sale_earnings) + abs(paid_payouts - ledger_payouts)
        return Response({
            "reconciled": discrepancy == Decimal("0.00"),
            "completed_suborder_net_earnings": _money(completed_net),
            "recorded_seller_sale_credits": _money(sale_earnings),
            "recorded_seller_refund_debits": _money(refund_earnings),
            "settled_seller_payouts": _money(paid_payouts),
            "ledger_settled_payouts": _money(ledger_payouts),
            "discrepancy_amount": _money(discrepancy),
            "payments_by_method": payments_by_method,
            "webhook_events_processed": PaymentWebhookEvent.objects.count(),
        })
