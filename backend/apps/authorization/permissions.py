from django.utils import timezone
from rest_framework.permissions import BasePermission

from apps.authorization.models import Permission, Role, UserPermission


def user_has_permission(user, permission_key):
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.status != user.Status.ACTIVE:
        return False
    if user.role_assignments.filter(role__key=Role.Key.OWNER).exists():
        return True
    try:
        permission = Permission.objects.get(key=permission_key)
    except Permission.DoesNotExist:
        return False
    override = UserPermission.objects.filter(user=user, permission=permission).first()
    if override and (override.expires_at is None or override.expires_at > timezone.now()):
        return override.is_granted
    return user.role_assignments.filter(role__permissions=permission).exists()


class HasPlatformPermission(BasePermission):
    message = "You do not have the required platform permission."

    def has_permission(self, request, view):
        key = getattr(view, "required_permission", None)
        return bool(key and user_has_permission(request.user, key))


class IsSelfOrPlatformPermission(BasePermission):
    message = "You may only access your own resources."

    def has_object_permission(self, request, view, obj):
        if user_has_permission(request.user, getattr(view, "required_permission", "")):
            return True
        owner_id = getattr(obj, "user_id", None)
        return str(owner_id) == str(request.user.pk)
