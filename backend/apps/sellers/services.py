from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.authorization.models import Role, UserRole
from apps.authorization.permissions import user_has_permission
from apps.platform.audit import record_audit
from apps.platform.models import (
    Notification,
    SellerApplication,
    SellerApplicationApproval,
    SellerProfile,
)


def reviewer_role_for(user):
    roles = set(user.role_assignments.values_list("role__key", flat=True))
    if Role.Key.OWNER in roles:
        if not user_has_permission(user, "seller.applications.review"):
            raise PermissionDenied("You do not have permission to review seller applications.")
        return SellerApplicationApproval.ReviewerRole.OWNER
    if Role.Key.ADMIN in roles:
        if not user_has_permission(user, "seller.applications.review"):
            raise PermissionDenied("You do not have permission to review seller applications.")
        return SellerApplicationApproval.ReviewerRole.ADMIN
    raise PermissionDenied("Only an Admin or Owner may review seller applications.")


@transaction.atomic
def review_seller_application(request, application_id, decision, reason=""):
    reviewer_role = reviewer_role_for(request.user)
    try:
        application = SellerApplication.objects.select_for_update().select_related("user").get(pk=application_id)
    except SellerApplication.DoesNotExist:
        from rest_framework.exceptions import NotFound
        raise NotFound()
    if application.status in [SellerApplication.Status.APPROVED, SellerApplication.Status.REJECTED]:
        raise ValidationError("This application has already reached a final decision.")
    if application.user_id == request.user.pk:
        raise PermissionDenied("You cannot review your own seller application.")

    SellerApplicationApproval.objects.create(
        application=application,
        reviewer=request.user,
        reviewer_role=reviewer_role,
        decision=decision,
        reason=reason,
        cycle=application.review_cycle,
    )
    latest_decisions = {}
    for approval in application.approval_history.filter(cycle=application.review_cycle).order_by("created_at"):
        latest_decisions[approval.reviewer_role] = approval.decision

    profile = SellerProfile.objects.filter(user=application.user).first()
    if decision == SellerApplicationApproval.Decision.REJECTED:
        application.status = SellerApplication.Status.REJECTED
        application.review_reason = reason
        if profile:
            profile.is_active = False
            profile.save(update_fields=["is_active", "updated_at"])
    elif decision == SellerApplicationApproval.Decision.NEEDS_INFO:
        application.status = SellerApplication.Status.NEEDS_INFO
        application.review_reason = reason
        if profile:
            profile.is_active = False
            profile.save(update_fields=["is_active", "updated_at"])
    elif all(latest_decisions.get(role) == SellerApplicationApproval.Decision.APPROVED for role in ("admin", "owner")):
        application.status = SellerApplication.Status.APPROVED
        application.review_reason = ""
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        if profile:
            profile.is_active = True
            profile.save(update_fields=["is_active", "updated_at"])
        seller_role, _ = Role.objects.get_or_create(key=Role.Key.SELLER, defaults={"name": "Seller"})
        UserRole.objects.get_or_create(user=application.user, role=seller_role, defaults={"assigned_by": request.user})
    else:
        application.status = SellerApplication.Status.PENDING
        application.review_reason = ""

    if application.status in [SellerApplication.Status.APPROVED, SellerApplication.Status.REJECTED, SellerApplication.Status.NEEDS_INFO]:
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
    application.save(update_fields=["status", "review_reason", "reviewed_by", "reviewed_at"])

    Notification.objects.create(
        user=application.user,
        category="seller_application",
        title="Seller application update",
        body=f"Your application is {application.get_status_display().lower()}. {reason}".strip(),
        payload={"application_id": str(application.pk), "status": application.status},
    )
    record_audit(
        request,
        "seller_application.reviewed",
        resource_type="seller_application",
        resource_id=application.pk,
        metadata={"reviewer_role": reviewer_role, "decision": decision, "cycle": application.review_cycle},
    )
    return application
