"""Read-only, permission-scoped marketplace overview for portal dashboards."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.authorization.models import Permission, Role, UserRole
from apps.authorization.permissions import user_has_permission
from apps.catalog.models import Category, Product
from apps.commerce.models import Order, SellerOrder
from apps.platform.models import SellerApplication, SellerProfile

ANALYTICS_PERMISSION = "platform.analytics.read"
OPERATIONS_PERMISSIONS = ("seller.applications.review", "catalog.products.review", ANALYTICS_PERMISSION)
EXCLUDED_REVENUE_STATUSES = (Order.Status.CANCELLED, Order.Status.REFUNDED)
TREND_DAYS = 14


def _money(value):
    return str((value or Decimal("0")).quantize(Decimal("0.01")))


def _operations():
    return {
        "pending_seller_applications": SellerApplication.objects.filter(
            status__in=[SellerApplication.Status.PENDING, SellerApplication.Status.NEEDS_INFO]
        ).count(),
        "pending_products": Product.objects.filter(status=Product.Status.PENDING_APPROVAL).count(),
        "published_products": Product.objects.filter(status=Product.Status.PUBLISHED).count(),
        "products_by_status": dict(Product.objects.values_list("status").annotate(total=Count("id")).order_by()),
        "active_sellers": SellerProfile.objects.filter(is_active=True).count(),
        "active_categories": Category.objects.filter(is_active=True).count(),
    }


def _commerce():
    revenue_orders = Order.objects.exclude(status__in=EXCLUDED_REVENUE_STATUSES)
    totals = revenue_orders.aggregate(gmv=Sum("total"), orders=Count("id"))
    commission = SellerOrder.objects.exclude(status__in=EXCLUDED_REVENUE_STATUSES).aggregate(total=Sum("commission_amount"))["total"]
    today = timezone.localdate()
    start = today - timedelta(days=TREND_DAYS - 1)
    daily_rows = {
        row["day"]: row
        for row in Order.objects.filter(created_at__date__gte=start)
        .exclude(status__in=EXCLUDED_REVENUE_STATUSES)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(orders=Count("id"), revenue=Sum("total"))
        .order_by()
    }
    daily = []
    for offset in range(TREND_DAYS):
        day = start + timedelta(days=offset)
        row = daily_rows.get(day, {})
        daily.append({"date": day.isoformat(), "orders": row.get("orders", 0), "revenue": _money(row.get("revenue"))})
    order_count = totals["orders"] or 0
    return {
        "gross_merchandise_value": _money(totals["gmv"]),
        "platform_commission": _money(commission),
        "orders_total": Order.objects.count(),
        "average_order_value": _money((totals["gmv"] or Decimal("0")) / order_count if order_count else Decimal("0")),
        "orders_by_status": dict(Order.objects.values_list("status").annotate(total=Count("id")).order_by()),
        "daily": daily,
    }


def _users():
    by_role = dict(UserRole.objects.values_list("role__key").annotate(total=Count("user", distinct=True)).order_by())
    return {
        "total": User.objects.count(),
        "active": User.objects.filter(status=User.Status.ACTIVE, is_active=True).count(),
        "by_role": {key: by_role.get(key, 0) for key in Role.Key.values},
    }


class ManagementOverviewView(APIView):
    """Returns only the sections the signed-in user is authorized to see."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        user = request.user
        granted = [key for key in Permission.objects.order_by("key").values_list("key", flat=True) if user_has_permission(user, key)]
        can_view_operations = any(key in granted for key in OPERATIONS_PERMISSIONS)
        can_view_analytics = ANALYTICS_PERMISSION in granted
        if not can_view_operations and not can_view_analytics:
            raise PermissionDenied("You do not have access to marketplace analytics.")
        return Response({
            "viewer": {
                "roles": sorted(user.role_assignments.values_list("role__key", flat=True)),
                "permissions": granted,
            },
            "operations": _operations() if can_view_operations else None,
            "commerce": _commerce() if can_view_analytics else None,
            "users": _users() if can_view_analytics else None,
            "generated_at": timezone.now().isoformat(),
        })
