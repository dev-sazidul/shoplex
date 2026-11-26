"""Phase 3 Admin & Owner Control Center endpoints with strict RBAC boundaries."""

from datetime import timedelta
from decimal import Decimal, InvalidOperation
import secrets

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.authorization.permissions import user_has_permission
from apps.catalog.models import Brand, Category, Product, ProductApproval, ProductReport
from apps.commerce.models import (
    FinancialLedgerEntry,
    Order,
    OrderItem,
    SellerEarning,
    SellerOrder,
    SellerPayoutRequest,
)
from apps.platform.audit import record_audit
from apps.platform.models import (
    AuditLog,
    AuthSession,
    MFADevice,
    Notification,
    PlatformSetting,
    SellerApplication,
    SellerApplicationApproval,
    SellerProfile,
)

EXCLUDED_ORDER_STATUSES = (Order.Status.CANCELLED, Order.Status.REFUNDED)

DEFAULT_PLATFORM_SETTINGS = {
    "website_info": {"site_name": "SHOPLEX", "tagline": "One Marketplace. Endless Opportunities.", "support_email": "concierge@shoplex.com"},
    "branding": {"primary_color": "#0F172A", "secondary_color": "#2563EB", "accent_color": "#C8A96B", "logo_text": "SHOPLEX."},
    "commission_defaults": {"default_percentage": "10.00", "settlement_hold_days": 3},
    "shipping_config": {"default_country": "BD", "default_fee": "60.00", "free_shipping_threshold": "15000.00"},
    "tax_settings": {"vat_enabled": True, "vat_percentage": "5.00", "tax_inclusive_pricing": True},
    "refund_policies": {"return_window_days": 7, "require_verified_delivery": True, "auto_restore_stock": False},
    "payment_gateways": {"cod_enabled": True, "online_gateway": "standby", "settlement_currency": "BDT"},
    "email_config": {"from_address": "SHOPLEX <no-reply@shoplex.com>", "login_alerts_enabled": True},
    "seo_settings": {"canonical_domain": "https://shoplex.com", "allow_indexing": True},
    "maintenance_mode": {"enabled": False, "message": "SHOPLEX is undergoing scheduled maintenance."},
    "notification_settings": {"notify_admin_on_submission": True, "notify_owner_on_payout": True},
}


def _money(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


def _is_owner(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.status == User.Status.ACTIVE
        and user.role_assignments.filter(role__key=Role.Key.OWNER).exists()
    )


def _require_owner(user):
    if not _is_owner(user):
        raise PermissionDenied("Only the platform Owner may access this resource.")


def _require_admin_or_owner(user):
    if not user or not user.is_authenticated or not user.is_active or user.status != User.Status.ACTIVE:
        raise PermissionDenied("Authentication is required.")
    roles = set(user.role_assignments.values_list("role__key", flat=True))
    if Role.Key.OWNER in roles:
        return "owner"
    if Role.Key.ADMIN in roles and (
        user_has_permission(user, "catalog.products.review")
        or user_has_permission(user, "seller.applications.review")
    ):
        return "admin"
    raise PermissionDenied("Only an authorized Admin or Owner may access operational moderation.")


def _verify_reauth_if_provided(user, password):
    if password and not user.check_password(password):
        raise PermissionDenied("Reauthentication failed: incorrect password.")


class AdminOperationsDashboardView(APIView):
    """Operational moderation dashboard for Admin (and Owner) with zero financial revenue/profit exposure."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        role = _require_admin_or_owner(request.user)
        recent_seller_approvals = [
            {
                "type": "seller_application",
                "target": item.application.business_name,
                "target_id": str(item.application_id),
                "reviewer_role": item.reviewer_role,
                "decision": item.decision,
                "reason": item.reason,
                "cycle": item.cycle,
                "created_at": item.created_at,
            }
            for item in SellerApplicationApproval.objects.select_related("application").order_by("-created_at")[:10]
        ]
        recent_product_approvals = [
            {
                "type": "product",
                "target": item.product.name,
                "target_id": str(item.product_id),
                "reviewer_role": item.reviewer_role,
                "decision": item.decision,
                "reason": item.reason,
                "cycle": item.version,
                "created_at": item.created_at,
            }
            for item in ProductApproval.objects.select_related("product").order_by("-created_at")[:10]
        ]
        recent_activities = sorted(
            [*recent_seller_approvals, *recent_product_approvals],
            key=lambda row: row["created_at"],
            reverse=True,
        )[:12]

        moderation_products = [
            {
                "id": str(prod.id),
                "name": prod.name,
                "slug": prod.slug,
                "sku": prod.sku,
                "price": _money(prod.price),
                "status": prod.status,
                "approval_version": prod.approval_version,
                "seller_name": prod.seller.business_name,
                "category_name": prod.category.name,
                "updated_at": prod.updated_at,
            }
            for prod in Product.objects.select_related("seller", "category").order_by("-updated_at")[:40]
        ]

        return Response({
            "viewer_role": role,
            "statistics": {
                "pending_seller_applications": SellerApplication.objects.filter(
                    status__in=[SellerApplication.Status.PENDING, SellerApplication.Status.NEEDS_INFO]
                ).count(),
                "pending_product_approvals": Product.objects.filter(status=Product.Status.PENDING_APPROVAL).count(),
                "approved_products": Product.objects.filter(
                    status__in=[Product.Status.APPROVED, Product.Status.PUBLISHED]
                ).count(),
                "published_products": Product.objects.filter(status=Product.Status.PUBLISHED).count(),
                "rejected_products": Product.objects.filter(status=Product.Status.REJECTED).count(),
                "changes_requested_products": Product.objects.filter(status=Product.Status.CHANGES_REQUESTED).count(),
                "suspended_products": Product.objects.filter(status=Product.Status.SUSPENDED).count(),
                "open_product_reports": ProductReport.objects.filter(status=ProductReport.Status.OPEN).count(),
            },
            "recent_approval_activities": recent_activities,
            "moderation_products": moderation_products,
        })


class ProductModerationStatusView(APIView):
    """Allows Admin or Owner to suspend inappropriate products; Owner can also restore suspended products."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, product_id):
        role = _require_admin_or_owner(request.user)
        action = str(request.data.get("action", "suspend")).strip().lower()
        reason = str(request.data.get("reason", "")).strip()
        try:
            product = Product.objects.select_for_update().select_related("seller__user").get(pk=product_id)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")

        if action == "suspend":
            product.status = Product.Status.SUSPENDED
            product.save(update_fields=["status", "updated_at"])
            Notification.objects.create(
                user=product.seller.user,
                category="product_moderation",
                title="Product suspended",
                body=f"{product.name} was suspended by {role}. {reason}".strip(),
                payload={"product_id": str(product.pk), "status": product.status},
            )
            record_audit(
                request,
                "product.suspended",
                resource_type="product",
                resource_id=product.pk,
                metadata={"actor_role": role, "reason": reason},
            )
        elif action == "restore":
            if role != "owner":
                raise PermissionDenied("Only the platform Owner can restore a suspended product.")
            product.status = Product.Status.PUBLISHED if product.published_at else Product.Status.DRAFT
            product.save(update_fields=["status", "updated_at"])
            Notification.objects.create(
                user=product.seller.user,
                category="product_moderation",
                title="Product restored",
                body=f"{product.name} has been restored by the platform Owner.",
                payload={"product_id": str(product.pk), "status": product.status},
            )
            record_audit(
                request,
                "product.restored",
                resource_type="product",
                resource_id=product.pk,
                metadata={"status": product.status},
            )
        else:
            raise ValidationError({"action": "Action must be 'suspend' or 'restore'."})

        return Response({"id": str(product.pk), "name": product.name, "status": product.status})


class ProductReportListCreateView(APIView):
    """Authenticated users can report a product; Admin and Owner can list all product reports."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_admin_or_owner(request.user)
        reports = ProductReport.objects.select_related("product__seller", "reporter", "resolved_by").all()[:50]
        return Response([
            {
                "id": str(r.id),
                "product_id": str(r.product_id),
                "product_name": r.product.name,
                "product_status": r.product.status,
                "seller_name": r.product.seller.business_name,
                "reporter_email": r.reporter.email if r.reporter else "Anonymous",
                "reason": r.reason,
                "details": r.details,
                "status": r.status,
                "resolution_note": r.resolution_note,
                "created_at": r.created_at,
                "resolved_at": r.resolved_at,
            }
            for r in reports
        ])

    @extend_schema(request=dict, responses={201: dict})
    def post(self, request):
        product_id = request.data.get("product_id")
        reason = str(request.data.get("reason", "")).strip()
        details = str(request.data.get("details", "")).strip()
        if not product_id or not reason:
            raise ValidationError({"reason": "Product and reason are required."})
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")
        report = ProductReport.objects.create(
            product=product,
            reporter=request.user,
            reason=reason[:120],
            details=details,
        )
        record_audit(request, "product.reported", resource_type="product_report", resource_id=report.pk)
        return Response(
            {"id": str(report.id), "product_name": product.name, "reason": report.reason, "status": report.status},
            status=status.HTTP_201_CREATED,
        )


class ProductReportResolveView(APIView):
    """Admin or Owner resolves or dismisses a product report, optionally suspending the product."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, report_id):
        role = _require_admin_or_owner(request.user)
        try:
            report = ProductReport.objects.select_for_update().select_related("product__seller__user").get(pk=report_id)
        except ProductReport.DoesNotExist:
            raise NotFound("Product report not found.")
        decision = str(request.data.get("status", ProductReport.Status.RESOLVED)).strip().lower()
        if decision not in {ProductReport.Status.RESOLVED, ProductReport.Status.DISMISSED}:
            raise ValidationError({"status": "Status must be 'resolved' or 'dismissed'."})
        note = str(request.data.get("resolution_note", "")).strip()
        suspend_product = bool(request.data.get("suspend_product", False))

        report.status = decision
        report.resolution_note = note
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.save(update_fields=["status", "resolution_note", "resolved_by", "resolved_at"])

        if suspend_product:
            report.product.status = Product.Status.SUSPENDED
            report.product.save(update_fields=["status", "updated_at"])

        record_audit(
            request,
            "product_report.resolved",
            resource_type="product_report",
            resource_id=report.pk,
            metadata={"actor_role": role, "status": decision, "suspended_product": suspend_product},
        )
        return Response({"id": str(report.id), "status": report.status, "product_status": report.product.status})


def _compute_financial_summary():
    non_cancelled_orders = Order.objects.exclude(status__in=EXCLUDED_ORDER_STATUSES)
    non_cancelled_suborders = SellerOrder.objects.exclude(status__in=EXCLUDED_ORDER_STATUSES)

    gross_sales = non_cancelled_orders.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    commission_revenue = non_cancelled_suborders.aggregate(total=Sum("commission_amount"))["total"] or Decimal("0.00")
    refund_orders = Order.objects.filter(status=Order.Status.REFUNDED).aggregate(total=Sum("total"))["total"] or Decimal("0.00")
    seller_refunds = SellerEarning.objects.filter(entry_type=SellerEarning.EntryType.REFUND).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    ledger_refunds = FinancialLedgerEntry.objects.filter(
        transaction_type=FinancialLedgerEntry.TransactionType.REFUND_DEDUCTION
    ).exclude(status=FinancialLedgerEntry.Status.REVERSED).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_refunds = max(refund_orders, seller_refunds, ledger_refunds)

    operational_expenses = FinancialLedgerEntry.objects.filter(
        transaction_type=FinancialLedgerEntry.TransactionType.OPERATIONAL_EXPENSE
    ).exclude(status=FinancialLedgerEntry.Status.REVERSED).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    payment_fees = FinancialLedgerEntry.objects.filter(
        transaction_type=FinancialLedgerEntry.TransactionType.PAYMENT_FEE
    ).exclude(status=FinancialLedgerEntry.Status.REVERSED).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    seller_credits = SellerEarning.objects.filter(
        entry_type__in=[SellerEarning.EntryType.SALE, SellerEarning.EntryType.ADJUSTMENT]
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    paid_payouts_amount = SellerPayoutRequest.objects.filter(status=SellerPayoutRequest.Status.PAID).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")
    pending_payouts_qs = SellerPayoutRequest.objects.filter(
        status__in=[SellerPayoutRequest.Status.PENDING, SellerPayoutRequest.Status.APPROVED]
    )
    pending_payouts_amount = pending_payouts_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    unsettled_suborder_earnings = non_cancelled_suborders.exclude(status=SellerOrder.Status.COMPLETED).aggregate(
        total=Sum("net_earnings")
    )["total"] or Decimal("0.00")

    outstanding_liabilities = max((seller_credits - seller_refunds - paid_payouts_amount) + unsettled_suborder_earnings, Decimal("0.00"))
    net_revenue = commission_revenue - total_refunds
    net_profit = net_revenue - operational_expenses - payment_fees

    return {
        "gross_sales": _money(gross_sales),
        "platform_commission_revenue": _money(commission_revenue),
        "total_refunds": _money(total_refunds),
        "operational_expenses": _money(operational_expenses),
        "payment_fees": _money(payment_fees),
        "net_revenue": _money(net_revenue),
        "net_platform_profit": _money(net_profit),
        "seller_outstanding_liabilities": _money(outstanding_liabilities),
        "pending_payouts_count": pending_payouts_qs.count(),
        "pending_payouts_amount": _money(pending_payouts_amount),
        "completed_payouts_count": SellerPayoutRequest.objects.filter(status=SellerPayoutRequest.Status.PAID).count(),
        "completed_payouts_amount": _money(paid_payouts_amount),
    }


class OwnerExecutiveDashboardView(APIView):
    """Owner-only executive dashboard with full business, financial, and multi-horizon chart data."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        business = {
            "total_customers": UserRole.objects.filter(role__key=Role.Key.CUSTOMER).values("user_id").distinct().count(),
            "total_sellers": SellerProfile.objects.count(),
            "active_sellers": SellerProfile.objects.filter(is_active=True).count(),
            "pending_applications": SellerApplication.objects.filter(
                status__in=[SellerApplication.Status.PENDING, SellerApplication.Status.NEEDS_INFO]
            ).count(),
            "total_products": Product.objects.count(),
            "pending_products": Product.objects.filter(status=Product.Status.PENDING_APPROVAL).count(),
            "published_products": Product.objects.filter(status=Product.Status.PUBLISHED).count(),
            "total_orders": Order.objects.count(),
            "completed_orders": Order.objects.filter(status=Order.Status.COMPLETED).count(),
            "cancelled_orders": Order.objects.filter(status=Order.Status.CANCELLED).count(),
        }
        financial = _compute_financial_summary()

        today = timezone.localdate()
        start_14 = today - timedelta(days=13)
        daily_map = {
            row["day"]: row
            for row in Order.objects.filter(created_at__date__gte=start_14)
            .exclude(status__in=EXCLUDED_ORDER_STATUSES)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(orders=Count("id"), sales=Sum("total"))
            .order_by()
        }
        daily_sales = []
        for offset in range(14):
            day = start_14 + timedelta(days=offset)
            row = daily_map.get(day, {})
            daily_sales.append({"date": day.isoformat(), "orders": row.get("orders", 0), "sales": _money(row.get("sales"))})

        monthly_rows = (
            Order.objects.exclude(status__in=EXCLUDED_ORDER_STATUSES)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(orders=Count("id"), revenue=Sum("total"))
            .order_by("month")[:12]
        )
        monthly_revenue = [
            {
                "month": row["month"].strftime("%Y-%m") if row["month"] else "Current",
                "orders": row["orders"],
                "revenue": _money(row["revenue"]),
            }
            for row in monthly_rows
        ]

        yearly_rows = (
            Order.objects.exclude(status__in=EXCLUDED_ORDER_STATUSES)
            .annotate(year=TruncYear("created_at"))
            .values("year")
            .annotate(orders=Count("id"), revenue=Sum("total"))
            .order_by("year")
        )
        yearly_revenue = [
            {
                "year": row["year"].strftime("%Y") if row["year"] else str(today.year),
                "orders": row["orders"],
                "revenue": _money(row["revenue"]),
            }
            for row in yearly_rows
        ]

        seller_performance = []
        for seller in SellerProfile.objects.select_related("user").all()[:20]:
            suborders = SellerOrder.objects.filter(seller=seller).exclude(status__in=EXCLUDED_ORDER_STATUSES)
            agg = suborders.aggregate(
                gross=Sum("subtotal"),
                commission=Sum("commission_amount"),
                net=Sum("net_earnings"),
                orders=Count("id"),
            )
            seller_performance.append({
                "id": seller.pk,
                "business_name": seller.business_name,
                "store_slug": seller.store_slug,
                "email": seller.user.email,
                "is_active": seller.is_active,
                "user_status": seller.user.status,
                "orders_count": agg["orders"] or 0,
                "gross_sales": _money(agg["gross"]),
                "commission_generated": _money(agg["commission"]),
                "net_earnings": _money(agg["net"]),
            })

        product_performance = [
            {
                "id": str(prod.id),
                "name": prod.name,
                "slug": prod.slug,
                "seller_name": prod.seller.business_name,
                "status": prod.status,
                "price": _money(prod.price),
                "stock_quantity": prod.stock_quantity,
                "units_sold": prod.units_sold or 0,
                "revenue": _money(prod.revenue),
            }
            for prod in Product.objects.select_related("seller")
            .annotate(
                units_sold=Sum(
                    "order_lines__quantity",
                    filter=~Q(order_lines__seller_order__status__in=EXCLUDED_ORDER_STATUSES),
                ),
                revenue=Sum(
                    "order_lines__line_total",
                    filter=~Q(order_lines__seller_order__status__in=EXCLUDED_ORDER_STATUSES),
                ),
            )
            .order_by("-revenue", "-units_sold")[:12]
        ]

        return Response({
            "business_metrics": business,
            "financial_metrics": financial,
            "charts": {
                "daily_sales": daily_sales,
                "monthly_revenue": monthly_revenue,
                "yearly_revenue": yearly_revenue,
                "orders_by_status": dict(Order.objects.values_list("status").annotate(total=Count("id")).order_by()),
            },
            "seller_performance": seller_performance,
            "product_performance": product_performance,
        })


class OwnerSellerManagementView(APIView):
    """Owner-only directory of all sellers with earnings, activity, and account status."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        rows = []
        for seller in SellerProfile.objects.select_related("user").order_by("-created_at"):
            suborders = SellerOrder.objects.filter(seller=seller).exclude(status__in=EXCLUDED_ORDER_STATUSES)
            agg = suborders.aggregate(
                gross=Sum("subtotal"),
                commission=Sum("commission_amount"),
                net=Sum("net_earnings"),
            )
            paid = SellerPayoutRequest.objects.filter(seller=seller, status=SellerPayoutRequest.Status.PAID).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0.00")
            rows.append({
                "id": seller.pk,
                "user_id": str(seller.user_id),
                "business_name": seller.business_name,
                "store_slug": seller.store_slug,
                "email": seller.user.email,
                "is_active": seller.is_active,
                "user_status": seller.user.status,
                "product_count": Product.objects.filter(seller=seller).count(),
                "published_products": Product.objects.filter(seller=seller, status=Product.Status.PUBLISHED).count(),
                "orders_count": suborders.count(),
                "gross_sales": _money(agg["gross"]),
                "commission_total": _money(agg["commission"]),
                "net_earnings": _money(agg["net"]),
                "paid_payouts": _money(paid),
                "created_at": seller.created_at,
            })
        return Response(rows)


class OwnerSellerStatusActionView(APIView):
    """Owner-only endpoint to suspend or reactivate a seller account and revoke active sessions."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, seller_id):
        _require_owner(request.user)
        _verify_reauth_if_provided(request.user, request.data.get("confirm_password"))
        action = str(request.data.get("action", "")).strip().lower()
        reason = str(request.data.get("reason", "")).strip()
        try:
            seller = SellerProfile.objects.select_for_update().select_related("user").get(pk=seller_id)
        except SellerProfile.DoesNotExist:
            raise NotFound("Seller not found.")

        if action == "suspend":
            seller.is_active = False
            seller.save(update_fields=["is_active", "updated_at"])
            if not seller.user.role_assignments.filter(role__key=Role.Key.OWNER).exists():
                seller.user.status = User.Status.SUSPENDED
                seller.user.save(update_fields=["status", "updated_at"])
                AuthSession.objects.filter(user=seller.user, revoked_at__isnull=True).update(revoked_at=timezone.now())
            Notification.objects.create(
                user=seller.user,
                category="account_status",
                title="Seller store suspended",
                body=f"Your seller account ({seller.business_name}) has been suspended. {reason}".strip(),
            )
            record_audit(
                request,
                "seller.suspended",
                resource_type="seller_profile",
                resource_id=seller.pk,
                metadata={"reason": reason},
            )
        elif action == "reactivate":
            seller.is_active = True
            seller.save(update_fields=["is_active", "updated_at"])
            seller.user.status = User.Status.ACTIVE
            seller.user.is_active = True
            seller.user.save(update_fields=["status", "is_active", "updated_at"])
            Notification.objects.create(
                user=seller.user,
                category="account_status",
                title="Seller store reactivated",
                body=f"Your seller account ({seller.business_name}) is active again.",
            )
            record_audit(
                request,
                "seller.reactivated",
                resource_type="seller_profile",
                resource_id=seller.pk,
                metadata={"reason": reason},
            )
        else:
            raise ValidationError({"action": "Action must be 'suspend' or 'reactivate'."})

        return Response({
            "id": seller.pk,
            "business_name": seller.business_name,
            "is_active": seller.is_active,
            "user_status": seller.user.status,
        })


class OwnerPayoutListView(APIView):
    """Owner-only view of all seller payout requests."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        payouts = SellerPayoutRequest.objects.select_related("seller__user").all()[:60]
        return Response([
            {
                "id": str(p.id),
                "seller_id": p.seller_id,
                "seller_name": p.seller.business_name,
                "seller_email": p.seller.user.email,
                "amount": _money(p.amount),
                "status": p.status,
                "review_reason": p.review_reason,
                "requested_at": p.requested_at,
                "reviewed_at": p.reviewed_at,
            }
            for p in payouts
        ])


class OwnerPayoutDecisionView(APIView):
    """Owner-only payout approval, settlement execution, or rejection with immutable ledger posting."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, payout_id):
        _require_owner(request.user)
        _verify_reauth_if_provided(request.user, request.data.get("confirm_password"))
        decision = str(request.data.get("decision", "")).strip().lower()
        reason = str(request.data.get("reason", "")).strip()
        try:
            payout = SellerPayoutRequest.objects.select_for_update().select_related("seller__user").get(pk=payout_id)
        except SellerPayoutRequest.DoesNotExist:
            raise NotFound("Payout request not found.")

        if payout.status in {SellerPayoutRequest.Status.PAID, SellerPayoutRequest.Status.REJECTED}:
            raise ValidationError("This payout request has already been finalized.")

        if decision == "approved":
            payout.status = SellerPayoutRequest.Status.APPROVED
        elif decision in {"paid", "settled"}:
            payout.status = SellerPayoutRequest.Status.PAID
            FinancialLedgerEntry.objects.create(
                transaction_type=FinancialLedgerEntry.TransactionType.SELLER_PAYOUT,
                amount=payout.amount,
                currency="BDT",
                reference_id=f"PAYOUT-{str(payout.id)[:8].upper()}",
                payout_request=payout,
                status=FinancialLedgerEntry.Status.SETTLED,
                description=f"Seller payout settled for {payout.seller.business_name}",
                recorded_by=request.user,
            )
        elif decision == "rejected":
            payout.status = SellerPayoutRequest.Status.REJECTED
        else:
            raise ValidationError({"decision": "Decision must be 'approved', 'paid', or 'rejected'."})

        payout.review_reason = reason
        payout.reviewed_at = timezone.now()
        payout.save(update_fields=["status", "review_reason", "reviewed_at"])

        Notification.objects.create(
            user=payout.seller.user,
            category="payout_settlement",
            title=f"Payout request {payout.status}",
            body=f"Your payout request of ৳{payout.amount} is now {payout.status}. {reason}".strip(),
            payload={"payout_id": str(payout.id), "status": payout.status},
        )
        record_audit(
            request,
            "payout.reviewed",
            resource_type="seller_payout_request",
            resource_id=payout.pk,
            metadata={"decision": payout.status, "amount": str(payout.amount)},
        )
        return Response({
            "id": str(payout.id),
            "seller_name": payout.seller.business_name,
            "amount": _money(payout.amount),
            "status": payout.status,
            "reviewed_at": payout.reviewed_at,
        })


class OwnerFinancialLedgerView(APIView):
    """Owner-only immutable financial ledger and transaction/settlement reporting."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        tx_type = request.query_params.get("transaction_type", "").strip()
        qs = FinancialLedgerEntry.objects.select_related("order", "payout_request__seller", "recorded_by").all()
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)
        entries = [
            {
                "id": str(entry.id),
                "transaction_type": entry.transaction_type,
                "amount": _money(entry.amount),
                "currency": entry.currency,
                "reference_id": entry.reference_id,
                "order_id": str(entry.order_id) if entry.order_id else None,
                "payout_request_id": str(entry.payout_request_id) if entry.payout_request_id else None,
                "status": entry.status,
                "description": entry.description,
                "recorded_by": entry.recorded_by.email if entry.recorded_by else "system",
                "created_at": entry.created_at,
            }
            for entry in qs[:100]
        ]
        return Response({
            "summary": _compute_financial_summary(),
            "entries": entries,
        })

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        tx_type = str(request.data.get("transaction_type", "")).strip()
        allowed_manual = {
            FinancialLedgerEntry.TransactionType.OPERATIONAL_EXPENSE,
            FinancialLedgerEntry.TransactionType.PAYMENT_FEE,
            FinancialLedgerEntry.TransactionType.REFUND_DEDUCTION,
        }
        if tx_type not in allowed_manual:
            raise ValidationError({"transaction_type": "Manual ledger entries must be operational_expense, payment_fee, or refund_deduction."})
        try:
            amount = Decimal(str(request.data.get("amount", "")))
        except (InvalidOperation, ValueError):
            raise ValidationError({"amount": "Enter a valid positive decimal amount."})
        if amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero."})
        reference_id = str(request.data.get("reference_id", "")).strip() or f"LEDGER-{secrets.token_hex(4).upper()}"
        description = str(request.data.get("description", "")).strip()

        entry = FinancialLedgerEntry.objects.create(
            transaction_type=tx_type,
            amount=amount,
            currency=str(request.data.get("currency", "BDT"))[:3].upper(),
            reference_id=reference_id[:120],
            status=FinancialLedgerEntry.Status.SETTLED,
            description=description[:255],
            recorded_by=request.user,
        )
        record_audit(
            request,
            "finance.ledger_entry_recorded",
            resource_type="financial_ledger_entry",
            resource_id=entry.pk,
            metadata={"transaction_type": tx_type, "amount": _money(amount), "reference_id": entry.reference_id},
        )
        return Response(
            {
                "id": str(entry.id),
                "transaction_type": entry.transaction_type,
                "amount": _money(entry.amount),
                "currency": entry.currency,
                "reference_id": entry.reference_id,
                "status": entry.status,
                "description": entry.description,
                "created_at": entry.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class OwnerCategoryManageView(APIView):
    """Owner-only category creation and management."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        name = str(request.data.get("name", "")).strip()
        description = str(request.data.get("description", "")).strip()
        if not name:
            raise ValidationError({"name": "Category name is required."})
        slug = slugify(request.data.get("slug") or name)
        category, created = Category.objects.update_or_create(
            slug=slug,
            defaults={"name": name[:100], "description": description, "is_active": True},
        )
        record_audit(request, "category.saved", resource_type="category", resource_id=category.pk)
        return Response(
            {"id": str(category.id), "name": category.name, "slug": category.slug, "description": category.description},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class OwnerBrandManageView(APIView):
    """Owner-only brand creation and management."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        name = str(request.data.get("name", "")).strip()
        description = str(request.data.get("description", "")).strip()
        if not name:
            raise ValidationError({"name": "Brand name is required."})
        slug = slugify(request.data.get("slug") or name)
        brand, created = Brand.objects.update_or_create(
            slug=slug,
            defaults={"name": name[:100], "description": description, "is_active": True},
        )
        record_audit(request, "brand.saved", resource_type="brand", resource_id=brand.pk)
        return Response(
            {"id": str(brand.id), "name": brand.name, "slug": brand.slug, "description": brand.description},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class OwnerPlatformSettingsView(APIView):
    """Owner-only platform settings management across website, branding, tax, refund, SEO, and maintenance."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        stored = {row.key: row.value for row in PlatformSetting.objects.all()}
        merged = {key: stored.get(key, default_val) for key, default_val in DEFAULT_PLATFORM_SETTINGS.items()}
        for key, val in stored.items():
            if key not in merged:
                merged[key] = val
        return Response(merged)

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def put(self, request):
        _require_owner(request.user)
        _verify_reauth_if_provided(request.user, request.data.get("confirm_password"))
        updates = request.data.get("settings", request.data)
        if not isinstance(updates, dict):
            raise ValidationError({"settings": "Settings payload must be a JSON object."})
        updated_keys = []
        for key, value in updates.items():
            if key == "confirm_password":
                continue
            slug_key = slugify(key).replace("-", "_")[:100]
            if not slug_key:
                continue
            PlatformSetting.objects.update_or_create(
                key=slug_key,
                defaults={"value": value if isinstance(value, dict) else {"value": value}, "updated_by": request.user},
            )
            updated_keys.append(slug_key)
        record_audit(
            request,
            "platform.settings_updated",
            resource_type="platform_setting",
            resource_id=",".join(updated_keys),
            metadata={"keys": updated_keys},
        )
        return self.get(request)


class OwnerSecurityCenterView(APIView):
    """Owner-only security console: mandatory MFA device status/enrollment, reauthentication, and login alerts."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        devices = MFADevice.objects.filter(user=request.user)
        sessions = AuthSession.objects.filter(user=request.user).order_by("-created_at")[:15]
        alerts = Notification.objects.filter(user=request.user, category="security_alert")[:15]
        return Response({
            "mfa_required": True,
            "mfa_enrolled": devices.filter(is_verified=True).exists(),
            "devices": [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "method": d.method,
                    "is_verified": d.is_verified,
                    "last_used_at": d.last_used_at,
                    "created_at": d.created_at,
                }
                for d in devices
            ],
            "active_sessions": [
                {
                    "id": str(s.id),
                    "ip_address": s.ip_address,
                    "user_agent": s.user_agent,
                    "created_at": s.created_at,
                    "revoked": s.revoked_at is not None,
                }
                for s in sessions
            ],
            "login_alerts": [
                {"id": str(a.id), "title": a.title, "body": a.body, "payload": a.payload, "created_at": a.created_at}
                for a in alerts
            ],
        })

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        action = str(request.data.get("action", "enroll_mfa")).strip().lower()
        password = str(request.data.get("password", ""))
        if not password or not request.user.check_password(password):
            raise PermissionDenied("Confirm your current Owner password to perform this security action.")

        if action == "enroll_mfa":
            device_name = str(request.data.get("name", "Owner Authenticator")).strip() or "Owner Authenticator"
            device, _ = MFADevice.objects.update_or_create(
                user=request.user,
                method=MFADevice.Method.TOTP,
                name=device_name[:80],
                defaults={
                    "secret_encrypted": f"totp:{secrets.token_hex(16)}",
                    "is_verified": True,
                    "last_used_at": timezone.now(),
                },
            )
            record_audit(request, "owner.mfa_enrolled", resource_type="mfa_device", resource_id=device.pk)
            return Response({"status": "mfa_enrolled", "device_id": str(device.id), "name": device.name, "is_verified": True})
        if action == "reauthenticate":
            record_audit(request, "owner.reauthenticated", resource_type="user", resource_id=request.user.pk)
            return Response({"status": "verified", "verified_at": timezone.now().isoformat()})
        raise ValidationError({"action": "Action must be 'enroll_mfa' or 'reauthenticate'."})


class OwnerAuditLogListView(APIView):
    """Owner-only immutable audit history viewer."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        action_filter = request.query_params.get("action", "").strip()
        qs = AuditLog.objects.select_related("actor").all()
        if action_filter:
            qs = qs.filter(action__icontains=action_filter)
        return Response([
            {
                "id": str(log.id),
                "actor_email": log.actor.email if log.actor else "system",
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "metadata": log.metadata,
                "created_at": log.created_at,
            }
            for log in qs[:100]
        ])
