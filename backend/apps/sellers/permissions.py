from rest_framework.permissions import BasePermission

from apps.authorization.models import Role


class IsActiveSeller(BasePermission):
    message = "An approved active seller profile is required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active or user.status != user.Status.ACTIVE:
            return False
        return user.role_assignments.filter(role__key=Role.Key.SELLER).exists() and hasattr(user, "seller_profile") and user.seller_profile.is_active
