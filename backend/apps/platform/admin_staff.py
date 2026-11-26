"""Final Owner & Admin Role Structure: Owner Admin-staff management & 16-permission engine."""

from decimal import Decimal, InvalidOperation
import secrets
import uuid

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User, UserProfile
from apps.authorization.models import Permission, Role, UserPermission, UserRole
from apps.authorization.permissions import user_has_permission
from apps.catalog.models import Brand, Category, Product, ProductVariant
from apps.commerce.control_center import _compute_financial_summary
from apps.commerce.models import (
    FinancialLedgerEntry,
    Order,
    Payment,
    ReturnRequest,
    SellerEarning,
    SellerOrder,
)
from apps.platform.audit import record_audit
from apps.platform.models import AuthSession, Notification, SellerProfile

ADMIN_STAFF_PERMISSION_KEYS = (
    "admin.products.create",
    "admin.products.edit",
    "admin.products.delete",
    "admin.products.publish",
    "admin.products.approve",
    "admin.sellers.manage",
    "admin.customers.manage",
    "admin.orders.manage",
    "admin.suppliers.manage",
    "admin.suppliers.import",
    "admin.coupons.manage",
    "admin.shipping.manage",
    "admin.support.manage",
    "admin.reports.analytics",
    "admin.refunds.process",
    "admin.finance.reports",
)


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
        raise PermissionDenied("Only the platform Owner has authority to perform this action.")


def _require_admin_permission(user, permission_key: str):
    if not (user and user.is_authenticated and user.is_active and user.status == User.Status.ACTIVE):
        raise PermissionDenied("Active authentication is required.")
    if _is_owner(user):
        return
    if not user.role_assignments.filter(role__key=Role.Key.ADMIN).exists():
        raise PermissionDenied("Only an authorized Admin staff member or Owner may access this resource.")
    if not user_has_permission(user, permission_key):
        raise PermissionDenied(f"Missing Owner-delegated permission: {permission_key}.")


def _get_or_create_shoplex_official_store(actor_user):
    """Returns the platform-owned SHOPLEX Official store, always owned by the Owner account (never an Admin)."""
    existing = SellerProfile.objects.filter(store_slug="shoplex-official").select_related("user").first()
    if existing:
        return existing
    owner_user = (
        actor_user
        if _is_owner(actor_user)
        else User.objects.filter(role_assignments__role__key=Role.Key.OWNER, is_active=True).order_by("created_at").first()
    )
    if not owner_user:
        raise ValidationError({"owner": "An active Owner account is required to own platform products."})
    store, _ = SellerProfile.objects.get_or_create(
        user=owner_user,
        defaults={
            "business_name": "SHOPLEX Official",
            "store_slug": "shoplex-official",
            "store_description": "Official platform-owned products curated and sold directly by SHOPLEX.",
            "business_type": "platform",
            "is_active": True,
        },
    )
    return store


def _serialize_admin_staff(user: User):
    perms = {key: user_has_permission(user, key) for key in ADMIN_STAFF_PERMISSION_KEYS}
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "status": user.status,
        "is_active": user.is_active and user.status == User.Status.ACTIVE,
        "permissions": perms,
        "granted_count": sum(1 for v in perms.values() if v),
        "created_at": user.created_at,
    }


def _serialize_platform_product(product: Product):
    return {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "sku": product.sku,
        "price": _money(product.price),
        "compare_at_price": _money(product.compare_at_price) if product.compare_at_price else None,
        "stock_quantity": product.stock_quantity,
        "status": product.status,
        "category": product.category.slug,
        "category_name": product.category.name,
        "brand": product.brand.slug if product.brand else None,
        "product_owner": product.seller.business_name,
        "ownership_type": product.ownership_type,
        "created_by_id": str(product.created_by_id) if product.created_by_id else None,
        "created_by_email": product.created_by.email if product.created_by else None,
        "product_source": product.product_source,
        "supplier_name": product.supplier_name,
        "created_at": product.created_at,
    }


class OwnerAdminStaffListCreateView(APIView):
    """Owner-only Admin employee directory and creation endpoint."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        admins = User.objects.filter(role_assignments__role__key=Role.Key.ADMIN).distinct().order_by("-created_at")
        return Response({
            "admins": [_serialize_admin_staff(a) for a in admins],
            "available_permissions": list(ADMIN_STAFF_PERMISSION_KEYS),
        })

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        email = str(request.data.get("email", "")).strip().lower()
        first_name = str(request.data.get("first_name", "")).strip() or "Admin"
        last_name = str(request.data.get("last_name", "")).strip() or "Staff"
        password = str(request.data.get("password", "")).strip()
        if not email:
            raise ValidationError({"email": "Admin email address is required."})

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(
                email=email,
                first_name=first_name[:100],
                last_name=last_name[:100],
                status=User.Status.ACTIVE,
                is_active=True,
                email_verified_at=timezone.now(),
            )
            if password:
                validate_password(password, user=user)
                user.set_password(password)
            else:
                user.set_password(f"Shoplex-Adm-{secrets.token_hex(6)}!")
            user.save()
            UserProfile.objects.get_or_create(user=user)
        else:
            user.status = User.Status.ACTIVE
            user.is_active = True
            user.email_verified_at = user.email_verified_at or timezone.now()
            if password:
                validate_password(password, user=user)
                user.set_password(password)
            user.save()

        admin_role = Role.objects.get(key=Role.Key.ADMIN)
        UserRole.objects.get_or_create(user=user, role=admin_role, defaults={"assigned_by": request.user})

        initial_perms = request.data.get("permissions")
        if isinstance(initial_perms, list):
            for key in ADMIN_STAFF_PERMISSION_KEYS:
                perm = Permission.objects.filter(key=key).first()
                if perm and key in initial_perms:
                    UserPermission.objects.update_or_create(
                        user=user,
                        permission=perm,
                        defaults={"is_granted": True, "assigned_by": request.user, "expires_at": None},
                    )

        Notification.objects.create(
            user=user,
            category="admin_staff",
            title="Admin staff account created",
            body="Your SHOPLEX Admin staff account is active under Owner supervision.",
        )
        record_audit(
            request,
            "owner.admin_staff_created",
            resource_type="user",
            resource_id=user.pk,
            metadata={"email": user.email},
        )
        return Response(_serialize_admin_staff(user), status=status.HTTP_201_CREATED)


class OwnerAdminStaffStatusView(APIView):
    """Owner-only endpoint to activate, suspend, or remove an Admin staff member with session revocation."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, admin_id):
        _require_owner(request.user)
        action = str(request.data.get("action", "")).strip().lower()
        reason = str(request.data.get("reason", "")).strip()
        try:
            admin_user = User.objects.select_for_update().get(pk=admin_id)
        except (User.DoesNotExist, ValueError):
            raise NotFound("Admin account not found.")
        if admin_user.role_assignments.filter(role__key=Role.Key.OWNER).exists():
            raise PermissionDenied("Owner accounts cannot be modified via Admin staff controls.")

        if action == "activate":
            admin_user.status = User.Status.ACTIVE
            admin_user.is_active = True
            admin_user.save(update_fields=["status", "is_active", "updated_at"])
            UserRole.objects.get_or_create(
                user=admin_user,
                role=Role.objects.get(key=Role.Key.ADMIN),
                defaults={"assigned_by": request.user},
            )
            record_audit(request, "owner.admin_staff_activated", resource_type="user", resource_id=admin_user.pk)
        elif action == "suspend":
            admin_user.status = User.Status.SUSPENDED
            admin_user.save(update_fields=["status", "updated_at"])
            AuthSession.objects.filter(user=admin_user, revoked_at__isnull=True).update(revoked_at=timezone.now())
            record_audit(
                request,
                "owner.admin_staff_suspended",
                resource_type="user",
                resource_id=admin_user.pk,
                metadata={"reason": reason},
            )
        elif action == "remove":
            UserRole.objects.filter(user=admin_user, role__key=Role.Key.ADMIN).delete()
            UserPermission.objects.filter(user=admin_user, permission__key__in=ADMIN_STAFF_PERMISSION_KEYS).update(
                is_granted=False
            )
            AuthSession.objects.filter(user=admin_user, revoked_at__isnull=True).update(revoked_at=timezone.now())
            record_audit(
                request,
                "owner.admin_staff_removed",
                resource_type="user",
                resource_id=admin_user.pk,
                metadata={"reason": reason},
            )
        else:
            raise ValidationError({"action": "Action must be 'activate', 'suspend', or 'remove'."})

        return Response(_serialize_admin_staff(admin_user))


class OwnerAdminStaffPermissionView(APIView):
    """Owner-only granular assignment/revocation of the 16 Admin staff permissions with immediate effect."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, admin_id):
        _require_owner(request.user)
        try:
            admin_user = User.objects.select_for_update().get(pk=admin_id, role_assignments__role__key=Role.Key.ADMIN)
        except (User.DoesNotExist, ValueError):
            raise NotFound("Admin staff account not found.")

        perm_key = str(request.data.get("permission", "")).strip()
        is_granted = bool(request.data.get("is_granted", True))
        if perm_key not in ADMIN_STAFF_PERMISSION_KEYS:
            raise ValidationError({"permission": f"Permission must be one of the 16 Admin permissions."})

        perm = Permission.objects.get(key=perm_key)
        UserPermission.objects.update_or_create(
            user=admin_user,
            permission=perm,
            defaults={"is_granted": is_granted, "assigned_by": request.user, "expires_at": None},
        )
        Notification.objects.create(
            user=admin_user,
            category="permission_change",
            title="Admin permission updated",
            body=f"Owner {'granted' if is_granted else 'revoked'} permission: {perm_key}.",
            payload={"permission": perm_key, "is_granted": is_granted},
        )
        record_audit(
            request,
            "owner.admin_permission_updated",
            resource_type="user_permission",
            resource_id=f"{admin_user.pk}:{perm_key}",
            metadata={"admin_email": admin_user.email, "permission": perm_key, "is_granted": is_granted},
        )
        return Response(_serialize_admin_staff(admin_user))


class AdminMyPermissionsView(APIView):
    """Returns the signed-in Admin's live backend-evaluated 16 permissions so Admin navigation stays in sync."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        user = request.user
        if not (user.is_active and user.status == User.Status.ACTIVE):
            raise PermissionDenied("Active account required.")
        is_owner = _is_owner(user)
        is_admin = user.role_assignments.filter(role__key=Role.Key.ADMIN).exists()
        if not (is_owner or is_admin):
            raise PermissionDenied("Admin or Owner role required.")
        return Response({
            "role": "owner" if is_owner else "admin",
            "permissions": {key: user_has_permission(user, key) for key in ADMIN_STAFF_PERMISSION_KEYS},
        })


class AdminPlatformProductListCreateView(APIView):
    """Lists or uploads platform-owned SHOPLEX products. Admin uploads are always owned by SHOPLEX / Owner."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        if not (
            _is_owner(request.user)
            or any(
                user_has_permission(request.user, k)
                for k in ("admin.products.create", "admin.products.edit", "admin.products.publish", "admin.products.approve")
            )
        ):
            raise PermissionDenied("You do not have permission to view platform-owned products.")
        products = Product.objects.filter(ownership_type=Product.OwnershipType.PLATFORM).select_related(
            "seller", "category", "brand", "created_by"
        ).order_by("-created_at")[:50]
        return Response({"products": [_serialize_platform_product(p) for p in products]})

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_admin_permission(request.user, "admin.products.create")
        name = str(request.data.get("name", "")).strip()
        description = str(request.data.get("description", "")).strip()
        category_slug = str(request.data.get("category", "")).strip()
        brand_slug = str(request.data.get("brand", "")).strip()
        sku = str(request.data.get("sku", "")).strip()
        source = str(request.data.get("product_source", Product.ProductSource.OWNER_PLATFORM)).strip().lower()
        supplier_name = str(request.data.get("supplier_name", "")).strip()

        if not name or not description or not category_slug:
            raise ValidationError({"name": "Name, description, and category are required."})
        if source not in {Product.ProductSource.OWNER_PLATFORM, Product.ProductSource.SUPPLIER}:
            raise ValidationError({"product_source": "Product source must be 'owner_platform' or 'supplier'."})

        category = Category.objects.filter(slug=category_slug, is_active=True).first()
        if not category:
            raise ValidationError({"category": "Valid active category slug is required."})
        brand = Brand.objects.filter(slug=brand_slug, is_active=True).first() if brand_slug else None

        try:
            price = Decimal(str(request.data.get("price", "")))
            compare_raw = request.data.get("compare_at_price")
            compare_at = Decimal(str(compare_raw)) if compare_raw not in (None, "") else None
            stock_quantity = int(request.data.get("stock_quantity", 0))
        except (InvalidOperation, ValueError):
            raise ValidationError({"price": "Enter valid numeric price and stock values."})

        if price <= 0 or stock_quantity < 0:
            raise ValidationError({"price": "Price must be positive and stock must be non-negative."})

        official_store = _get_or_create_shoplex_official_store(request.user)
        can_publish = _is_owner(request.user) or user_has_permission(request.user, "admin.products.publish")
        initial_status = Product.Status.PUBLISHED if can_publish else Product.Status.PENDING_APPROVAL

        product = Product.objects.create(
            seller=official_store,
            ownership_type=Product.OwnershipType.PLATFORM,
            created_by=request.user,
            product_source=source,
            supplier_name=supplier_name[:160],
            category=category,
            brand=brand,
            name=name[:180],
            slug=f"{slugify(name)[:180]}-{uuid.uuid4().hex[:8]}",
            description=description,
            sku=sku[:80] or f"SLX-PLT-{uuid.uuid4().hex[:6].upper()}",
            price=price,
            compare_at_price=compare_at,
            stock_quantity=stock_quantity,
            status=initial_status,
            published_at=timezone.now() if initial_status == Product.Status.PUBLISHED else None,
        )
        record_audit(
            request,
            "platform_product.created",
            resource_type="product",
            resource_id=product.pk,
            metadata={
                "product_owner": official_store.business_name,
                "created_by": request.user.email,
                "product_source": source,
                "status": initial_status,
            },
        )
        return Response(_serialize_platform_product(product), status=status.HTTP_201_CREATED)


class AdminPlatformProductDetailView(APIView):
    """Permission-gated edit and delete for platform-owned SHOPLEX products."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def patch(self, request, product_id):
        _require_admin_permission(request.user, "admin.products.edit")
        try:
            product = Product.objects.select_for_update().get(pk=product_id)
        except (Product.DoesNotExist, ValueError):
            raise NotFound("Product not found.")
        for field in ("name", "description", "sku", "supplier_name"):
            if field in request.data:
                setattr(product, field, str(request.data[field]).strip())
        if "price" in request.data:
            product.price = Decimal(str(request.data["price"]))
        if "stock_quantity" in request.data:
            product.stock_quantity = max(0, int(request.data["stock_quantity"]))
        product.save()
        record_audit(request, "platform_product.edited", resource_type="product", resource_id=product.pk)
        return Response(_serialize_platform_product(product))

    @extend_schema(responses={204: None})
    @transaction.atomic
    def delete(self, request, product_id):
        _require_admin_permission(request.user, "admin.products.delete")
        try:
            product = Product.objects.select_for_update().get(pk=product_id)
        except (Product.DoesNotExist, ValueError):
            raise NotFound("Product not found.")
        record_audit(
            request,
            "platform_product.deleted",
            resource_type="product",
            resource_id=product.pk,
            metadata={"name": product.name},
        )
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPlatformProductPublishView(APIView):
    """Permission-gated publish action for platform-owned SHOPLEX products."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={200: dict})
    @transaction.atomic
    def post(self, request, product_id):
        _require_admin_permission(request.user, "admin.products.publish")
        try:
            product = Product.objects.select_for_update().get(pk=product_id)
        except (Product.DoesNotExist, ValueError):
            raise NotFound("Product not found.")
        product.status = Product.Status.PUBLISHED
        product.published_at = timezone.now()
        product.save(update_fields=["status", "published_at", "updated_at"])
        record_audit(request, "platform_product.published", resource_type="product", resource_id=product.pk)
        return Response(_serialize_platform_product(product))


class AdminOrdersManageView(APIView):
    """Permission-gated order management view (requires admin.orders.manage)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_admin_permission(request.user, "admin.orders.manage")
        orders = Order.objects.select_related("customer").order_by("-created_at")[:40]
        return Response({
            "orders": [
                {
                    "id": str(o.id),
                    "order_number": o.order_number,
                    "customer_email": o.customer.email,
                    "status": o.status,
                    "payment_method": o.payment_method,
                    "total": _money(o.total),
                    "created_at": o.created_at,
                }
                for o in orders
            ]
        })


class AdminCustomersManageView(APIView):
    """Permission-gated customer directory (requires admin.customers.manage)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_admin_permission(request.user, "admin.customers.manage")
        customers = User.objects.filter(role_assignments__role__key=Role.Key.CUSTOMER).distinct().order_by("-created_at")[:50]
        return Response({
            "customers": [
                {
                    "id": str(c.id),
                    "email": c.email,
                    "name": f"{c.first_name} {c.last_name}".strip() or c.email,
                    "status": c.status,
                    "created_at": c.created_at,
                }
                for c in customers
            ]
        })


class AdminSelectedFinanceReportView(APIView):
    """Read-only selected financial report access (requires Owner-granted admin.finance.reports)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_admin_permission(request.user, "admin.finance.reports")
        summary = _compute_financial_summary()
        return Response({
            "read_only": True,
            "notice": "Selected financial report authorized by Owner. Admin cannot modify financial ledgers or claim earnings.",
            "gross_sales": summary["gross_sales"],
            "total_refunds": summary["total_refunds"],
            "completed_payouts_count": summary["completed_payouts_count"],
        })


class AdminRefundProcessView(APIView):
    """Permission-gated refund processing for Admin staff (requires Owner-granted admin.refunds.process)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, order_id):
        _require_admin_permission(request.user, "admin.refunds.process")
        reason = str(request.data.get("reason", "Owner-authorized Admin refund")).strip()
        try:
            order = Order.objects.select_for_update().select_related("payment").get(pk=order_id)
        except (Order.DoesNotExist, ValueError):
            raise NotFound("Order not found.")
        if order.status == Order.Status.REFUNDED:
            raise ValidationError({"order": "Order already refunded."})
        payment = Payment.objects.select_for_update().get(order=order)
        for suborder in order.seller_orders.select_for_update().prefetch_related("items"):
            for item in suborder.items.all():
                if item.variant_id:
                    ProductVariant.objects.filter(pk=item.variant_id).update(stock_quantity=F("stock_quantity") + item.quantity)
                elif item.product_id:
                    Product.objects.filter(pk=item.product_id).update(stock_quantity=F("stock_quantity") + item.quantity)
            suborder.status = SellerOrder.Status.REFUNDED
            suborder.save(update_fields=["status"])
            ReturnRequest.objects.filter(seller_order=suborder).update(status=ReturnRequest.Status.REFUNDED)
        payment.status = Payment.Status.REFUNDED
        payment.refunded_amount = order.total
        payment.save(update_fields=["status", "refunded_amount", "updated_at"])
        order.status = Order.Status.REFUNDED
        order.save(update_fields=["status", "updated_at"])
        FinancialLedgerEntry.objects.create(
            transaction_type=FinancialLedgerEntry.TransactionType.REFUND_DEDUCTION,
            amount=order.total,
            currency=payment.currency,
            reference_id=f"REFUND-{order.order_number}",
            order=order,
            status=FinancialLedgerEntry.Status.SETTLED,
            description=f"Admin-processed refund ({request.user.email}): {reason}"[:255],
            recorded_by=request.user,
        )
        record_audit(
            request,
            "admin_staff.refund_processed",
            resource_type="order",
            resource_id=order.pk,
            metadata={"actor": request.user.email, "amount": _money(order.total)},
        )
        return Response({"order_id": str(order.id), "status": order.status, "refunded_amount": _money(order.total)})
