"""Phase 4 Manager Portal, Admin Assignment, and Business Ownership Management APIs."""

from datetime import timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import secrets

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
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
from apps.catalog.models import Category, Product, ProductApproval, ProductReport
from apps.commerce.models import Order, SellerOrder
from apps.platform.audit import record_audit
from apps.platform.models import (
    AdminAssignment,
    AdminAssignmentHistory,
    AuthSession,
    BusinessShare,
    BusinessSharePlan,
    ManagerInvitation,
    ManagerProfile,
    Notification,
    OwnershipHistory,
    SellerApplication,
    SellerApplicationApproval,
    SellerProfile,
    ShareAllocation,
    ShareDocument,
    ShareOffer,
    ShareTransaction,
)

EXCLUDED_ORDER_STATUSES = (Order.Status.CANCELLED, Order.Status.REFUNDED)

MANAGER_PERMISSION_KEYS = (
    "manager.analytics.business",
    "manager.reports.sellers",
    "manager.reports.products",
    "manager.reports.orders",
    "manager.reports.finance",
    "manager.admins.monitor",
    "manager.shares.read",
    "manager.shares.documents",
)


def _money(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


def _pct(value):
    return str((value or Decimal("0.00")).quantize(Decimal("0.01")))


def _require_owner(user):
    if not (
        user
        and user.is_authenticated
        and user.is_active
        and user.status == User.Status.ACTIVE
        and user.role_assignments.filter(role__key=Role.Key.OWNER).exists()
    ):
        raise PermissionDenied("Only the platform Owner may perform this operation.")


def _require_active_manager(user):
    if not (user and user.is_authenticated and user.is_active and user.status == User.Status.ACTIVE):
        raise PermissionDenied("Active manager authentication is required.")
    roles = set(user.role_assignments.values_list("role__key", flat=True))
    if Role.Key.OWNER in roles:
        return getattr(user, "manager_profile", None)
    if Role.Key.MANAGER not in roles:
        raise PermissionDenied("Only an authorized Manager may access this resource.")
    profile = ManagerProfile.objects.filter(user=user, is_active=True).first()
    if not profile:
        raise PermissionDenied("Your manager profile is not active.")
    return profile


def _serialize_manager(profile: ManagerProfile):
    user = profile.user
    permissions = {key: user_has_permission(user, key) for key in MANAGER_PERMISSION_KEYS}
    assigned_admins = [
        {
            "assignment_id": str(a.id),
            "admin_id": str(a.admin_id),
            "admin_email": a.admin.email,
            "admin_name": f"{a.admin.first_name} {a.admin.last_name}".strip() or a.admin.email,
            "responsibilities": a.responsibilities,
            "assigned_at": a.assigned_at,
        }
        for a in profile.admin_assignments.filter(is_active=True).select_related("admin")
    ]
    total_share_pct = (
        ShareAllocation.objects.filter(holder=user, status=ShareAllocation.Status.ACTIVE).aggregate(
            total=Sum("ownership_percentage")
        )["total"]
        or Decimal("0.00")
    )
    return {
        "id": profile.pk,
        "user_id": str(user.pk),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "title": profile.title,
        "business_unit": profile.business_unit,
        "responsibilities": profile.responsibilities,
        "is_active": profile.is_active and user.status == User.Status.ACTIVE and user.is_active,
        "user_status": user.status,
        "permissions": permissions,
        "assigned_admins": assigned_admins,
        "ownership_percentage": _pct(total_share_pct),
        "created_at": profile.created_at,
    }


class OwnerManagerListCreateView(APIView):
    """Owner-only endpoint to list all managers or create/invite a new manager account."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        profiles = ManagerProfile.objects.select_related("user").order_by("-created_at")
        invitations = ManagerInvitation.objects.order_by("-created_at")[:20]
        return Response({
            "managers": [_serialize_manager(p) for p in profiles],
            "invitations": [
                {
                    "id": str(inv.id),
                    "email": inv.email,
                    "expires_at": inv.expires_at,
                    "accepted_at": inv.accepted_at,
                    "created_at": inv.created_at,
                }
                for inv in invitations
            ],
            "available_permissions": list(MANAGER_PERMISSION_KEYS),
        })

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        email = str(request.data.get("email", "")).strip().lower()
        first_name = str(request.data.get("first_name", "")).strip() or "Partner"
        last_name = str(request.data.get("last_name", "")).strip() or "Manager"
        title = str(request.data.get("title", "Operations Manager")).strip()
        business_unit = str(request.data.get("business_unit", "Core Marketplace")).strip()
        responsibilities = request.data.get("responsibilities", [])
        if isinstance(responsibilities, str):
            responsibilities = [item.strip() for item in responsibilities.split(",") if item.strip()]
        password = str(request.data.get("password", "")).strip()

        if not email:
            raise ValidationError({"email": "Manager email address is required."})

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
                user.set_password(f"Shoplex-Mgr-{secrets.token_hex(6)}!")
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

        manager_role = Role.objects.get(key=Role.Key.MANAGER)
        UserRole.objects.get_or_create(user=user, role=manager_role, defaults={"assigned_by": request.user})

        profile, _ = ManagerProfile.objects.update_or_create(
            user=user,
            defaults={
                "title": title[:120],
                "business_unit": business_unit[:120],
                "responsibilities": responsibilities if isinstance(responsibilities, list) else [],
                "is_active": True,
                "created_by": request.user,
            },
        )

        raw_token = secrets.token_urlsafe(24)
        digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        invitation = ManagerInvitation.objects.create(
            email=user.email,
            invited_by=request.user,
            token_digest=digest,
            expires_at=timezone.now() + timedelta(days=7),
            accepted_at=timezone.now(),
        )

        granted_list = request.data.get("permissions")
        if isinstance(granted_list, list):
            for key in MANAGER_PERMISSION_KEYS:
                perm = Permission.objects.filter(key=key).first()
                if perm:
                    UserPermission.objects.update_or_create(
                        user=user,
                        permission=perm,
                        defaults={"is_granted": key in granted_list, "assigned_by": request.user},
                    )

        Notification.objects.create(
            user=user,
            category="manager_onboarding",
            title="Manager access granted",
            body=f"You have been appointed as {profile.title} ({profile.business_unit}).",
        )
        record_audit(
            request,
            "manager.created",
            resource_type="manager_profile",
            resource_id=profile.pk,
            metadata={"email": user.email, "invitation_id": str(invitation.id)},
        )
        return Response(_serialize_manager(profile), status=status.HTTP_201_CREATED)


class OwnerManagerStatusActionView(APIView):
    """Owner-only endpoint to activate, suspend, or remove a manager with immediate session invalidation."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, manager_id):
        _require_owner(request.user)
        action = str(request.data.get("action", "")).strip().lower()
        reason = str(request.data.get("reason", "")).strip()
        try:
            profile = ManagerProfile.objects.select_for_update().select_related("user").get(pk=manager_id)
        except ManagerProfile.DoesNotExist:
            raise NotFound("Manager not found.")

        user = profile.user
        if "responsibilities" in request.data:
            resp = request.data.get("responsibilities")
            if isinstance(resp, str):
                resp = [item.strip() for item in resp.split(",") if item.strip()]
            if isinstance(resp, list):
                profile.responsibilities = resp
                profile.save(update_fields=["responsibilities", "updated_at"])

        if action == "activate":
            profile.is_active = True
            profile.save(update_fields=["is_active", "updated_at"])
            user.status = User.Status.ACTIVE
            user.is_active = True
            user.save(update_fields=["status", "is_active", "updated_at"])
            UserRole.objects.get_or_create(
                user=user,
                role=Role.objects.get(key=Role.Key.MANAGER),
                defaults={"assigned_by": request.user},
            )
            record_audit(request, "manager.activated", resource_type="manager_profile", resource_id=profile.pk)
        elif action == "suspend":
            profile.is_active = False
            profile.save(update_fields=["is_active", "updated_at"])
            if not user.role_assignments.filter(role__key=Role.Key.OWNER).exists():
                user.status = User.Status.SUSPENDED
                user.save(update_fields=["status", "updated_at"])
            AuthSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
            record_audit(
                request,
                "manager.suspended",
                resource_type="manager_profile",
                resource_id=profile.pk,
                metadata={"reason": reason},
            )
        elif action == "remove":
            profile.is_active = False
            profile.save(update_fields=["is_active", "updated_at"])
            AdminAssignment.objects.filter(manager=profile, is_active=True).update(is_active=False, updated_at=timezone.now())
            UserRole.objects.filter(user=user, role__key=Role.Key.MANAGER).delete()
            UserPermission.objects.filter(user=user, permission__key__in=MANAGER_PERMISSION_KEYS).update(is_granted=False)
            AuthSession.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
            record_audit(
                request,
                "manager.removed",
                resource_type="manager_profile",
                resource_id=profile.pk,
                metadata={"reason": reason},
            )
        else:
            raise ValidationError({"action": "Action must be 'activate', 'suspend', or 'remove'."})

        return Response(_serialize_manager(profile))


class OwnerManagerPermissionView(APIView):
    """Owner-only granular permission grant/revoke for a Manager with immediate effect."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request, manager_id):
        _require_owner(request.user)
        try:
            profile = ManagerProfile.objects.select_for_update().select_related("user").get(pk=manager_id)
        except ManagerProfile.DoesNotExist:
            raise NotFound("Manager not found.")

        perm_key = str(request.data.get("permission", "")).strip()
        is_granted = bool(request.data.get("is_granted", True))
        if perm_key not in MANAGER_PERMISSION_KEYS:
            raise ValidationError({"permission": f"Permission must be one of { ', '.join(MANAGER_PERMISSION_KEYS)}."})

        perm = Permission.objects.get(key=perm_key)
        UserPermission.objects.update_or_create(
            user=profile.user,
            permission=perm,
            defaults={"is_granted": is_granted, "assigned_by": request.user, "expires_at": None},
        )
        if not is_granted:
            # Invalidate active sessions or notify manager immediately
            Notification.objects.create(
                user=profile.user,
                category="permission_change",
                title="Permission revoked",
                body=f"Access to {perm_key} was revoked by the platform Owner.",
            )
        record_audit(
            request,
            "manager.permission_updated",
            resource_type="manager_profile",
            resource_id=profile.pk,
            metadata={"permission": perm_key, "is_granted": is_granted},
        )
        return Response(_serialize_manager(profile))


class OwnerAdminAssignmentView(APIView):
    """Owner-only Admin-to-Manager assignment, reassignment, removal, and history."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        admin_users = User.objects.filter(role_assignments__role__key=Role.Key.ADMIN).distinct()
        assignments = AdminAssignment.objects.filter(is_active=True).select_related("manager__user", "admin")
        history = AdminAssignmentHistory.objects.select_related("admin", "manager__user", "actor")[:30]
        return Response({
            "admins": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "name": f"{u.first_name} {u.last_name}".strip() or u.email,
                    "status": u.status,
                }
                for u in admin_users
            ],
            "active_assignments": [
                {
                    "id": str(a.id),
                    "manager_id": a.manager_id,
                    "manager_email": a.manager.user.email,
                    "manager_name": f"{a.manager.user.first_name} {a.manager.user.last_name}".strip(),
                    "admin_id": str(a.admin_id),
                    "admin_email": a.admin.email,
                    "admin_name": f"{a.admin.first_name} {a.admin.last_name}".strip(),
                    "responsibilities": a.responsibilities,
                    "assigned_at": a.assigned_at,
                }
                for a in assignments
            ],
            "history": [
                {
                    "id": str(h.id),
                    "action": h.action,
                    "admin_email": h.admin.email,
                    "manager_email": h.manager.user.email if h.manager else None,
                    "actor_email": h.actor.email,
                    "note": h.note,
                    "created_at": h.created_at,
                }
                for h in history
            ],
        })

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        action = str(request.data.get("action", "assign")).strip().lower()
        admin_id = request.data.get("admin_id")
        manager_id = request.data.get("manager_id")
        responsibilities = str(request.data.get("responsibilities", "Seller & Product Approvals")).strip()

        try:
            admin_user = User.objects.get(pk=admin_id, role_assignments__role__key=Role.Key.ADMIN)
        except (User.DoesNotExist, ValueError):
            raise ValidationError({"admin_id": "Select a valid Admin user."})

        if action == "remove":
            if manager_id:
                qs = AdminAssignment.objects.filter(admin=admin_user, manager_id=manager_id, is_active=True)
            else:
                qs = AdminAssignment.objects.filter(admin=admin_user, is_active=True)
            removed_count = qs.update(is_active=False, updated_at=timezone.now())
            AdminAssignmentHistory.objects.create(
                admin=admin_user,
                manager=ManagerProfile.objects.filter(pk=manager_id).first() if manager_id else None,
                action=AdminAssignmentHistory.Action.REMOVED,
                note=f"Removed ({removed_count} active assignment(s))",
                actor=request.user,
            )
            record_audit(
                request,
                "admin_assignment.removed",
                resource_type="user",
                resource_id=admin_user.pk,
                metadata={"manager_id": manager_id},
            )
            return self.get(request)

        try:
            manager_profile = ManagerProfile.objects.select_related("user").get(pk=manager_id, is_active=True)
        except (ManagerProfile.DoesNotExist, ValueError):
            raise ValidationError({"manager_id": "Select an active Manager profile."})

        if action == "reassign":
            AdminAssignment.objects.filter(admin=admin_user, is_active=True).exclude(manager=manager_profile).update(
                is_active=False, updated_at=timezone.now()
            )
            hist_action = AdminAssignmentHistory.Action.REASSIGNED
        else:
            hist_action = AdminAssignmentHistory.Action.ASSIGNED

        assignment, _ = AdminAssignment.objects.update_or_create(
            manager=manager_profile,
            admin=admin_user,
            is_active=True,
            defaults={
                "responsibilities": responsibilities[:255],
                "assigned_by": request.user,
            },
        )
        AdminAssignmentHistory.objects.create(
            admin=admin_user,
            manager=manager_profile,
            action=hist_action,
            note=responsibilities[:255],
            actor=request.user,
        )
        Notification.objects.create(
            user=manager_profile.user,
            category="admin_assignment",
            title="Admin assigned to your team",
            body=f"{admin_user.email} is now assigned to you ({responsibilities}).",
        )
        record_audit(
            request,
            f"admin_assignment.{hist_action}",
            resource_type="admin_assignment",
            resource_id=assignment.pk,
            metadata={"admin_email": admin_user.email, "manager_email": manager_profile.user.email},
        )
        return self.get(request)


def _serialize_share_plan(plan: BusinessSharePlan):
    active_allocs = plan.allocations.filter(status=ShareAllocation.Status.ACTIVE).select_related("holder")
    allocated_pct = active_allocs.aggregate(total=Sum("ownership_percentage"))["total"] or Decimal("0.00")
    allocated_shares = active_allocs.aggregate(total=Sum("allocated_shares"))["total"] or 0
    remaining_pct = max(plan.max_allocated_percentage - allocated_pct, Decimal("0.00"))
    return {
        "id": str(plan.id),
        "name": plan.name,
        "code": plan.code,
        "total_authorized_shares": plan.total_authorized_shares,
        "max_allocated_percentage": _pct(plan.max_allocated_percentage),
        "allocated_percentage": _pct(allocated_pct),
        "remaining_percentage": _pct(remaining_pct),
        "owner_retained_percentage": _pct(Decimal("100.00") - allocated_pct),
        "allocated_shares": allocated_shares,
        "available_shares": max(plan.total_authorized_shares - allocated_shares, 0),
        "company_valuation": _money(plan.company_valuation),
        "currency": plan.currency,
        "is_active": plan.is_active,
        "share_classes": [
            {
                "id": str(sc.id),
                "class_name": sc.class_name,
                "share_count": sc.share_count,
                "percentage_represented": _pct(sc.percentage_represented),
                "unit_price": _money(sc.unit_price),
            }
            for sc in plan.share_classes.all()
        ],
        "offers": [
            {
                "id": str(o.id),
                "partner_id": str(o.partner_id),
                "partner_email": o.partner.email,
                "offered_shares": o.offered_shares,
                "offered_percentage": _pct(o.offered_percentage),
                "valuation_at_offer": _money(o.valuation_at_offer),
                "status": o.status,
                "terms_note": o.terms_note,
                "created_at": o.created_at,
            }
            for o in plan.offers.select_related("partner").all()[:20]
        ],
        "allocations": [
            {
                "id": str(al.id),
                "holder_id": str(al.holder_id),
                "holder_email": al.holder.email,
                "holder_name": f"{al.holder.first_name} {al.holder.last_name}".strip() or al.holder.email,
                "allocated_shares": al.allocated_shares,
                "ownership_percentage": _pct(al.ownership_percentage),
                "implied_value": _money((plan.company_valuation * al.ownership_percentage) / Decimal("100.00")),
                "status": al.status,
                "allocated_at": al.allocated_at,
            }
            for al in active_allocs
        ],
        "transactions": [
            {
                "id": str(tx.id),
                "transaction_type": tx.transaction_type,
                "from_holder_email": tx.from_holder.email if tx.from_holder else None,
                "to_holder_email": tx.to_holder.email if tx.to_holder else None,
                "shares_count": tx.shares_count,
                "percentage_delta": _pct(tx.percentage_delta),
                "valuation_snapshot": _money(tx.valuation_snapshot),
                "legal_reference": tx.legal_reference,
                "created_at": tx.created_at,
            }
            for tx in plan.transactions.select_related("from_holder", "to_holder").all()[:25]
        ],
        "ownership_history": [
            {
                "id": str(oh.id),
                "holder_email": oh.holder.email,
                "previous_percentage": _pct(oh.previous_percentage),
                "new_percentage": _pct(oh.new_percentage),
                "reason": oh.reason,
                "created_at": oh.created_at,
            }
            for oh in plan.ownership_history.select_related("holder").all()[:25]
        ],
        "documents": [
            {
                "id": str(doc.id),
                "holder_email": doc.holder.email if doc.holder else "All Partners",
                "title": doc.title,
                "document_type": doc.document_type,
                "reference_number": doc.reference_number,
                "summary": doc.summary,
                "created_at": doc.created_at,
            }
            for doc in plan.documents.select_related("holder").all()[:20]
        ],
    }


class OwnerSharePlanListCreateView(APIView):
    """Owner-only business share plan and valuation management."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        _require_owner(request.user)
        plans = BusinessSharePlan.objects.all()
        return Response([_serialize_share_plan(plan) for plan in plans])

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        name = str(request.data.get("name", "")).strip()
        if not name:
            raise ValidationError({"name": "Share plan name is required."})
        code = slugify(request.data.get("code") or name)[:80]
        try:
            total_shares = int(request.data.get("total_authorized_shares", 100000))
            max_pct = Decimal(str(request.data.get("max_allocated_percentage", "40.00")))
            valuation = Decimal(str(request.data.get("company_valuation", "50000000.00")))
        except (InvalidOperation, ValueError):
            raise ValidationError({"company_valuation": "Provide valid numeric share and valuation figures."})

        if total_shares <= 0 or max_pct <= 0 or max_pct > Decimal("100.00") or valuation <= 0:
            raise ValidationError({"max_allocated_percentage": "Max allocated percentage must be between 0.01 and 100.00."})

        plan, created = BusinessSharePlan.objects.update_or_create(
            code=code,
            defaults={
                "name": name[:160],
                "total_authorized_shares": total_shares,
                "max_allocated_percentage": max_pct,
                "company_valuation": valuation,
                "currency": str(request.data.get("currency", "BDT"))[:3].upper(),
                "is_active": True,
                "created_by": request.user,
            },
        )
        unit_price = (valuation / Decimal(total_shares)).quantize(Decimal("0.01"))
        BusinessShare.objects.update_or_create(
            plan=plan,
            class_name=str(request.data.get("class_name", "Class A Partner Equity"))[:120],
            defaults={
                "share_count": int((Decimal(total_shares) * max_pct) / Decimal("100.00")),
                "percentage_represented": max_pct,
                "unit_price": unit_price,
            },
        )
        record_audit(
            request,
            "shares.plan_saved",
            resource_type="business_share_plan",
            resource_id=plan.pk,
            metadata={"code": plan.code, "max_percentage": _pct(max_pct), "valuation": _money(valuation)},
        )
        return Response(
            _serialize_share_plan(plan),
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class OwnerShareOfferCreateView(APIView):
    """Owner-only share offer creation for a selected partner."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        plan_id = request.data.get("plan_id")
        partner_email = str(request.data.get("partner_email", "")).strip().lower()
        try:
            plan = BusinessSharePlan.objects.select_for_update().get(pk=plan_id)
        except (BusinessSharePlan.DoesNotExist, ValueError):
            raise NotFound("Share plan not found.")
        partner = User.objects.filter(email__iexact=partner_email).first()
        if not partner:
            raise ValidationError({"partner_email": "Partner user account not found."})

        try:
            pct = Decimal(str(request.data.get("offered_percentage", "0")))
        except (InvalidOperation, ValueError):
            raise ValidationError({"offered_percentage": "Enter a valid ownership percentage."})
        if pct <= 0 or pct > Decimal("100.00"):
            raise ValidationError({"offered_percentage": "Offered percentage must be between 0.01 and 100.00."})

        current_allocated = (
            plan.allocations.filter(status=ShareAllocation.Status.ACTIVE).aggregate(total=Sum("ownership_percentage"))[
                "total"
            ]
            or Decimal("0.00")
        )
        if current_allocated + pct > plan.max_allocated_percentage:
            raise ValidationError({
                "offered_percentage": f"Offer exceeds the plan's maximum permitted allocation ({plan.max_allocated_percentage}%)."
            })

        shares = int((Decimal(plan.total_authorized_shares) * pct) / Decimal("100.00"))
        offer = ShareOffer.objects.create(
            plan=plan,
            partner=partner,
            offered_shares=max(shares, 1),
            offered_percentage=pct,
            valuation_at_offer=plan.company_valuation,
            terms_note=str(request.data.get("terms_note", "")).strip(),
            offered_by=request.user,
        )
        Notification.objects.create(
            user=partner,
            category="share_offer",
            title="Business share offer recorded",
            body=f"An internal share offer of {_pct(pct)}% under {plan.name} has been recorded.",
        )
        record_audit(
            request,
            "shares.offer_created",
            resource_type="share_offer",
            resource_id=offer.pk,
            metadata={"partner_email": partner.email, "percentage": _pct(pct)},
        )
        return Response(_serialize_share_plan(plan), status=status.HTTP_201_CREATED)


class OwnerShareAllocationCreateView(APIView):
    """Owner-only transactional share allocation enforcing ceiling and append-only history."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        plan_id = request.data.get("plan_id")
        holder_email = str(request.data.get("holder_email", "")).strip().lower()
        legal_reference = str(request.data.get("legal_reference", "")).strip() or f"DEED-{secrets.token_hex(4).upper()}"
        try:
            plan = BusinessSharePlan.objects.select_for_update().get(pk=plan_id)
        except (BusinessSharePlan.DoesNotExist, ValueError):
            raise NotFound("Share plan not found.")

        holder = User.objects.filter(email__iexact=holder_email).first()
        if not holder:
            raise ValidationError({"holder_email": "Partner/manager account not found."})

        try:
            pct = Decimal(str(request.data.get("ownership_percentage", "0")))
        except (InvalidOperation, ValueError):
            raise ValidationError({"ownership_percentage": "Enter a valid ownership percentage."})
        if pct <= 0 or pct > Decimal("100.00"):
            raise ValidationError({"ownership_percentage": "Ownership percentage must be between 0.01 and 100.00."})

        active_allocs = plan.allocations.select_for_update().filter(status=ShareAllocation.Status.ACTIVE)
        current_total = active_allocs.aggregate(total=Sum("ownership_percentage"))["total"] or Decimal("0.00")
        if current_total + pct > plan.max_allocated_percentage or current_total + pct > Decimal("100.00"):
            raise ValidationError({
                "ownership_percentage": (
                    f"Total allocated ownership ({_pct(current_total + pct)}%) cannot exceed "
                    f"the permitted plan limit ({_pct(plan.max_allocated_percentage)}%)."
                )
            })

        holder_prev = (
            active_allocs.filter(holder=holder).aggregate(total=Sum("ownership_percentage"))["total"] or Decimal("0.00")
        )
        shares = max(int((Decimal(plan.total_authorized_shares) * pct) / Decimal("100.00")), 1)
        allocation = ShareAllocation.objects.create(
            plan=plan,
            holder=holder,
            allocated_shares=shares,
            ownership_percentage=pct,
            status=ShareAllocation.Status.ACTIVE,
            allocated_by=request.user,
        )
        ShareOffer.objects.filter(plan=plan, partner=holder, status=ShareOffer.Status.OFFERED).update(
            status=ShareOffer.Status.ACCEPTED, responded_at=timezone.now()
        )
        ShareTransaction.objects.create(
            plan=plan,
            transaction_type=ShareTransaction.TransactionType.ALLOCATION,
            to_holder=holder,
            shares_count=shares,
            percentage_delta=pct,
            valuation_snapshot=plan.company_valuation,
            legal_reference=legal_reference[:160],
            recorded_by=request.user,
        )
        OwnershipHistory.objects.create(
            plan=plan,
            holder=holder,
            previous_percentage=holder_prev,
            new_percentage=holder_prev + pct,
            reason=f"Share allocation ({legal_reference})",
            recorded_by=request.user,
        )
        Notification.objects.create(
            user=holder,
            category="share_allocation",
            title="Business ownership shares allocated",
            body=f"{_pct(pct)}% ownership ({shares} shares) allocated under {plan.name}.",
        )
        record_audit(
            request,
            "shares.allocated",
            resource_type="share_allocation",
            resource_id=allocation.pk,
            metadata={"holder_email": holder.email, "percentage": _pct(pct), "legal_reference": legal_reference},
        )
        return Response(_serialize_share_plan(plan), status=status.HTTP_201_CREATED)


class OwnerShareTransferCreateView(APIView):
    """Owner-only legally documented share transfer between two partners."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={200: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        allocation_id = request.data.get("allocation_id")
        to_email = str(request.data.get("to_holder_email", "")).strip().lower()
        legal_reference = str(request.data.get("legal_reference", "")).strip()
        if not legal_reference:
            raise ValidationError({"legal_reference": "A legal transfer reference number is required."})

        try:
            source_alloc = ShareAllocation.objects.select_for_update().select_related("plan", "holder").get(
                pk=allocation_id, status=ShareAllocation.Status.ACTIVE
            )
        except (ShareAllocation.DoesNotExist, ValueError):
            raise NotFound("Active source share allocation not found.")

        target_user = User.objects.filter(email__iexact=to_email).first()
        if not target_user:
            raise ValidationError({"to_holder_email": "Recipient partner account not found."})
        if target_user.pk == source_alloc.holder_id:
            raise ValidationError({"to_holder_email": "Source and recipient holders must be different."})

        try:
            transfer_pct = Decimal(str(request.data.get("percentage", "0")))
        except (InvalidOperation, ValueError):
            raise ValidationError({"percentage": "Provide a valid transfer percentage."})
        if transfer_pct <= 0 or transfer_pct > source_alloc.ownership_percentage:
            raise ValidationError({"percentage": "Transfer percentage exceeds the source allocation."})

        plan = source_alloc.plan
        from_holder = source_alloc.holder
        from_prev = (
            plan.allocations.filter(holder=from_holder, status=ShareAllocation.Status.ACTIVE).aggregate(
                total=Sum("ownership_percentage")
            )["total"]
            or Decimal("0.00")
        )
        to_prev = (
            plan.allocations.filter(holder=target_user, status=ShareAllocation.Status.ACTIVE).aggregate(
                total=Sum("ownership_percentage")
            )["total"]
            or Decimal("0.00")
        )

        transfer_shares = max(int((Decimal(plan.total_authorized_shares) * transfer_pct) / Decimal("100.00")), 1)
        if transfer_pct == source_alloc.ownership_percentage:
            source_alloc.status = ShareAllocation.Status.TRANSFERRED
            source_alloc.save(update_fields=["status", "updated_at"])
        else:
            source_alloc.ownership_percentage -= transfer_pct
            source_alloc.allocated_shares = max(source_alloc.allocated_shares - transfer_shares, 1)
            source_alloc.save(update_fields=["ownership_percentage", "allocated_shares", "updated_at"])

        new_alloc = ShareAllocation.objects.create(
            plan=plan,
            holder=target_user,
            allocated_shares=transfer_shares,
            ownership_percentage=transfer_pct,
            status=ShareAllocation.Status.ACTIVE,
            allocated_by=request.user,
        )
        ShareTransaction.objects.create(
            plan=plan,
            transaction_type=ShareTransaction.TransactionType.TRANSFER,
            from_holder=from_holder,
            to_holder=target_user,
            shares_count=transfer_shares,
            percentage_delta=transfer_pct,
            valuation_snapshot=plan.company_valuation,
            legal_reference=legal_reference[:160],
            recorded_by=request.user,
        )
        OwnershipHistory.objects.create(
            plan=plan,
            holder=from_holder,
            previous_percentage=from_prev,
            new_percentage=from_prev - transfer_pct,
            reason=f"Transfer to {target_user.email} ({legal_reference})",
            recorded_by=request.user,
        )
        OwnershipHistory.objects.create(
            plan=plan,
            holder=target_user,
            previous_percentage=to_prev,
            new_percentage=to_prev + transfer_pct,
            reason=f"Transfer from {from_holder.email} ({legal_reference})",
            recorded_by=request.user,
        )
        record_audit(
            request,
            "shares.transferred",
            resource_type="share_allocation",
            resource_id=new_alloc.pk,
            metadata={
                "from_email": from_holder.email,
                "to_email": target_user.email,
                "percentage": _pct(transfer_pct),
                "legal_reference": legal_reference,
            },
        )
        return Response(_serialize_share_plan(plan))


class OwnerShareDocumentCreateView(APIView):
    """Owner-only ownership document recording."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=dict, responses={201: dict})
    @transaction.atomic
    def post(self, request):
        _require_owner(request.user)
        plan_id = request.data.get("plan_id")
        try:
            plan = BusinessSharePlan.objects.get(pk=plan_id)
        except (BusinessSharePlan.DoesNotExist, ValueError):
            raise NotFound("Share plan not found.")
        holder_email = str(request.data.get("holder_email", "")).strip().lower()
        holder = User.objects.filter(email__iexact=holder_email).first() if holder_email else None
        title = str(request.data.get("title", "")).strip()
        ref_num = str(request.data.get("reference_number", "")).strip()
        if not title or not ref_num:
            raise ValidationError({"title": "Document title and reference number are required."})
        doc = ShareDocument.objects.create(
            plan=plan,
            holder=holder,
            title=title[:180],
            document_type=str(request.data.get("document_type", ShareDocument.DocumentType.CERTIFICATE))[:24],
            reference_number=ref_num[:120],
            summary=str(request.data.get("summary", "")).strip(),
            uploaded_by=request.user,
        )
        record_audit(
            request,
            "shares.document_added",
            resource_type="share_document",
            resource_id=doc.pk,
            metadata={"reference_number": doc.reference_number, "holder_email": holder.email if holder else None},
        )
        return Response(_serialize_share_plan(plan), status=status.HTTP_201_CREATED)


class ManagerPortalDashboardView(APIView):
    """Permission-scoped Manager Portal dashboard returning only Owner-authorized modules."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        profile = _require_active_manager(request.user)
        user = request.user
        permissions = {key: user_has_permission(user, key) for key in MANAGER_PERMISSION_KEYS}

        # 1. Business Overview & Order Reports
        business_overview = None
        if permissions["manager.analytics.business"]:
            business_overview = {
                "active_sellers": SellerProfile.objects.filter(is_active=True).count(),
                "published_products": Product.objects.filter(status=Product.Status.PUBLISHED).count(),
                "pending_products": Product.objects.filter(status=Product.Status.PENDING_APPROVAL).count(),
                "active_categories": Category.objects.filter(is_active=True).count(),
                "total_orders": Order.objects.count(),
                "completed_orders": Order.objects.filter(status=Order.Status.COMPLETED).count(),
            }

        order_reports = None
        if permissions["manager.reports.orders"]:
            today = timezone.localdate()
            start_14 = today - timedelta(days=13)
            daily_rows = {
                row["day"]: row
                for row in Order.objects.filter(created_at__date__gte=start_14)
                .exclude(status__in=EXCLUDED_ORDER_STATUSES)
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(orders=Count("id"))
                .order_by()
            }
            daily_orders = [
                {
                    "date": (start_14 + timedelta(days=offset)).isoformat(),
                    "orders": daily_rows.get(start_14 + timedelta(days=offset), {}).get("orders", 0),
                }
                for offset in range(14)
            ]
            order_reports = {
                "orders_by_status": dict(Order.objects.values_list("status").annotate(total=Count("id")).order_by()),
                "daily_orders": daily_orders,
            }

        # 2. Authorized Financial / Revenue Analytics (STRICTLY isolated by manager.reports.finance)
        revenue_analytics = None
        if permissions["manager.reports.finance"]:
            non_cancelled = Order.objects.exclude(status__in=EXCLUDED_ORDER_STATUSES)
            suborders = SellerOrder.objects.exclude(status__in=EXCLUDED_ORDER_STATUSES)
            gmv = non_cancelled.aggregate(total=Sum("total"))["total"] or Decimal("0.00")
            comm = suborders.aggregate(total=Sum("commission_amount"))["total"] or Decimal("0.00")
            count = non_cancelled.count()
            today = timezone.localdate()
            start_14 = today - timedelta(days=13)
            rev_rows = {
                row["day"]: row
                for row in non_cancelled.filter(created_at__date__gte=start_14)
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(revenue=Sum("total"))
                .order_by()
            }
            revenue_analytics = {
                "gross_merchandise_value": _money(gmv),
                "platform_commission": _money(comm),
                "average_order_value": _money(gmv / count if count else Decimal("0.00")),
                "daily_revenue": [
                    {
                        "date": (start_14 + timedelta(days=offset)).isoformat(),
                        "revenue": _money(rev_rows.get(start_14 + timedelta(days=offset), {}).get("revenue")),
                    }
                    for offset in range(14)
                ],
            }

        # 3. Seller Performance Reports
        seller_reports = None
        if permissions["manager.reports.sellers"]:
            seller_reports = []
            for s in SellerProfile.objects.filter(is_active=True)[:15]:
                subs = SellerOrder.objects.filter(seller=s).exclude(status__in=EXCLUDED_ORDER_STATUSES)
                seller_reports.append({
                    "id": s.pk,
                    "business_name": s.business_name,
                    "store_slug": s.store_slug,
                    "published_products": Product.objects.filter(seller=s, status=Product.Status.PUBLISHED).count(),
                    "orders_count": subs.count(),
                })

        # 4. Product Compliance Reports
        product_reports = None
        if permissions["manager.reports.products"]:
            product_reports = [
                {
                    "id": str(r.id),
                    "product_name": r.product.name,
                    "seller_name": r.product.seller.business_name,
                    "reason": r.reason,
                    "status": r.status,
                    "created_at": r.created_at,
                }
                for r in ProductReport.objects.select_related("product__seller").all()[:20]
            ]

        # 5. Assigned Admin Monitoring & Team Activity (Strictly scoped to THIS Manager's assigned Admins)
        assigned_admins = None
        team_activity = None
        if permissions["manager.admins.monitor"]:
            assignments = (
                AdminAssignment.objects.filter(manager=profile, is_active=True).select_related("admin")
                if profile
                else AdminAssignment.objects.filter(is_active=True).select_related("admin")
            )
            admin_ids = [a.admin_id for a in assignments]
            assigned_admins = [
                {
                    "assignment_id": str(a.id),
                    "admin_id": str(a.admin_id),
                    "email": a.admin.email,
                    "name": f"{a.admin.first_name} {a.admin.last_name}".strip() or a.admin.email,
                    "responsibilities": a.responsibilities,
                    "assigned_at": a.assigned_at,
                }
                for a in assignments
            ]
            seller_acts = [
                {
                    "type": "seller_review",
                    "admin_email": act.reviewer.email,
                    "target": act.application.business_name,
                    "decision": act.decision,
                    "created_at": act.created_at,
                }
                for act in SellerApplicationApproval.objects.filter(reviewer_id__in=admin_ids)
                .select_related("reviewer", "application")
                .order_by("-created_at")[:10]
            ]
            product_acts = [
                {
                    "type": "product_review",
                    "admin_email": act.reviewer.email,
                    "target": act.product.name,
                    "decision": act.decision,
                    "created_at": act.created_at,
                }
                for act in ProductApproval.objects.filter(reviewer_id__in=admin_ids)
                .select_related("reviewer", "product")
                .order_by("-created_at")[:10]
            ]
            team_activity = sorted([*seller_acts, *product_acts], key=lambda r: r["created_at"], reverse=True)[:12]

        # 6. Own Authorized Business Share Information
        share_ownership = None
        if permissions["manager.shares.read"]:
            my_allocs = ShareAllocation.objects.filter(
                holder=user, status=ShareAllocation.Status.ACTIVE
            ).select_related("plan")
            my_offers = ShareOffer.objects.filter(partner=user).select_related("plan")
            my_history = OwnershipHistory.objects.filter(holder=user).select_related("plan")[:15]
            total_pct = my_allocs.aggregate(total=Sum("ownership_percentage"))["total"] or Decimal("0.00")
            total_shares = my_allocs.aggregate(total=Sum("allocated_shares"))["total"] or 0
            documents = None
            if permissions["manager.shares.documents"]:
                documents = [
                    {
                        "id": str(d.id),
                        "plan_name": d.plan.name,
                        "title": d.title,
                        "document_type": d.document_type,
                        "reference_number": d.reference_number,
                        "summary": d.summary,
                        "created_at": d.created_at,
                    }
                    for d in ShareDocument.objects.filter(holder=user).select_related("plan")
                ]
            share_ownership = {
                "total_ownership_percentage": _pct(total_pct),
                "total_allocated_shares": total_shares,
                "allocations": [
                    {
                        "id": str(a.id),
                        "plan_name": a.plan.name,
                        "plan_code": a.plan.code,
                        "allocated_shares": a.allocated_shares,
                        "ownership_percentage": _pct(a.ownership_percentage),
                        "company_valuation": _money(a.plan.company_valuation),
                        "implied_value": _money((a.plan.company_valuation * a.ownership_percentage) / Decimal("100.00")),
                        "allocated_at": a.allocated_at,
                    }
                    for a in my_allocs
                ],
                "offers": [
                    {
                        "id": str(o.id),
                        "plan_name": o.plan.name,
                        "offered_shares": o.offered_shares,
                        "offered_percentage": _pct(o.offered_percentage),
                        "status": o.status,
                        "terms_note": o.terms_note,
                        "created_at": o.created_at,
                    }
                    for o in my_offers
                ],
                "history": [
                    {
                        "id": str(h.id),
                        "plan_name": h.plan.name,
                        "previous_percentage": _pct(h.previous_percentage),
                        "new_percentage": _pct(h.new_percentage),
                        "reason": h.reason,
                        "created_at": h.created_at,
                    }
                    for h in my_history
                ],
                "documents": documents,
            }

        return Response({
            "profile": {
                "email": user.email,
                "name": f"{user.first_name} {user.last_name}".strip() or user.email,
                "title": profile.title if profile else "Executive Partner",
                "business_unit": profile.business_unit if profile else "Platform Governance",
                "responsibilities": profile.responsibilities if profile else ["All Marketplace Operations"],
            },
            "permissions": permissions,
            "business_overview": business_overview,
            "order_reports": order_reports,
            "revenue_analytics": revenue_analytics,
            "seller_reports": seller_reports,
            "product_reports": product_reports,
            "assigned_admins": assigned_admins,
            "team_activity": team_activity,
            "share_ownership": share_ownership,
        })
