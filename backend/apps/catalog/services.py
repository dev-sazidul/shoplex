from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.authorization.models import Role, UserRole
from apps.authorization.permissions import user_has_permission
from apps.catalog.models import Product, ProductApproval
from apps.platform.audit import record_audit
from apps.platform.models import Notification


def reviewer_role_for(user):
    roles = set(user.role_assignments.values_list("role__key", flat=True))
    if Role.Key.OWNER in roles:
        if not user_has_permission(user, "catalog.products.review"):
            raise PermissionDenied("You do not have permission to review products.")
        return ProductApproval.ReviewerRole.OWNER
    if Role.Key.ADMIN in roles:
        if not user_has_permission(user, "catalog.products.review"):
            raise PermissionDenied("You do not have permission to review products.")
        return ProductApproval.ReviewerRole.ADMIN
    raise PermissionDenied("Only an Admin or Owner may review products.")


def notify_product_reviewers(product):
    reviewers = UserRole.objects.filter(role__key__in=[Role.Key.ADMIN, Role.Key.OWNER], user__is_active=True, user__status="active").values_list("user_id", flat=True).distinct()
    Notification.objects.bulk_create([
        Notification(
            user_id=reviewer_id,
            category="product_approval",
            title="Product needs review",
            body=f"{product.name} was submitted for approval.",
            payload={"product_id": str(product.pk), "version": product.approval_version},
        ) for reviewer_id in reviewers
    ])


@transaction.atomic
def submit_product(request, product_id):
    try:
        product = Product.objects.select_for_update().get(pk=product_id, seller=request.user.seller_profile)
    except Product.DoesNotExist:
        raise NotFound()
    if product.status not in [Product.Status.DRAFT, Product.Status.REJECTED, Product.Status.CHANGES_REQUESTED]:
        raise ValidationError("Only draft or returned products can be submitted for review.")
    if not product.images.exists():
        raise ValidationError({"images": "Add at least one product image before submission."})
    if product.stock_quantity < 1 and not product.variants.filter(is_active=True, stock_quantity__gt=0).exists():
        raise ValidationError({"stock_quantity": "Add available inventory before submission."})
    product.status = Product.Status.PENDING_APPROVAL
    product.approval_version += 1
    product.save(update_fields=["status", "approval_version", "updated_at"])
    notify_product_reviewers(product)
    record_audit(request, "product.submitted", resource_type="product", resource_id=product.pk, metadata={"version": product.approval_version})
    return product


@transaction.atomic
def review_product(request, product_id, decision, reason=""):
    reviewer_role = reviewer_role_for(request.user)
    try:
        product = Product.objects.select_for_update().select_related("seller__user").get(pk=product_id)
    except Product.DoesNotExist:
        raise NotFound()
    if product.status != Product.Status.PENDING_APPROVAL:
        raise ValidationError("This product is not awaiting approval.")
    if product.seller.user_id == request.user.pk:
        raise PermissionDenied("You cannot review your own product.")
    ProductApproval.objects.create(
        product=product,
        version=product.approval_version,
        reviewer=request.user,
        reviewer_role=reviewer_role,
        decision=decision,
        reason=reason,
    )
    latest_decisions = {}
    for approval in product.approval_history.filter(version=product.approval_version).order_by("created_at"):
        latest_decisions[approval.reviewer_role] = approval.decision

    if decision == ProductApproval.Decision.REJECTED:
        product.status = Product.Status.REJECTED
    elif decision == ProductApproval.Decision.CHANGES_REQUESTED:
        product.status = Product.Status.CHANGES_REQUESTED
    elif all(latest_decisions.get(role) == ProductApproval.Decision.APPROVED for role in ("admin", "owner")):
        product.status = Product.Status.PUBLISHED
        product.published_at = timezone.now()
    product.save(update_fields=["status", "published_at", "updated_at"])
    Notification.objects.create(
        user=product.seller.user,
        category="product_approval",
        title="Product review update",
        body=f"{product.name}: {product.get_status_display().lower()}. {reason}".strip(),
        payload={"product_id": str(product.pk), "status": product.status},
    )
    record_audit(
        request,
        "product.reviewed",
        resource_type="product",
        resource_id=product.pk,
        metadata={"reviewer_role": reviewer_role, "decision": decision, "version": product.approval_version},
    )
    return product
