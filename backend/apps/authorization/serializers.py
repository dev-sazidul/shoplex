from rest_framework import serializers

from apps.authorization.models import Permission, Role, UserRole


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "key", "description"]


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ["id", "key", "name", "permissions"]


class UserRoleSerializer(serializers.ModelSerializer):
    role_key = serializers.CharField(source="role.key", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.SlugRelatedField(slug_field="key", queryset=Role.objects.all(), write_only=True)

    class Meta:
        model = UserRole
        fields = ["id", "user_email", "role", "role_key", "assigned_at"]
        read_only_fields = ["id", "assigned_at"]
