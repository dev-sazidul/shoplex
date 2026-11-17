from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.authorization.models import Permission, Role, UserRole
from apps.authorization.permissions import HasPlatformPermission
from apps.authorization.serializers import PermissionSerializer, RoleSerializer, UserRoleSerializer
from apps.platform.audit import record_audit


class RoleListView(generics.ListAPIView):
    queryset = Role.objects.prefetch_related("permissions").all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, HasPlatformPermission]
    required_permission = "authorization.roles.read"


class PermissionListView(generics.ListAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, HasPlatformPermission]
    required_permission = "authorization.permissions.read"


class RoleAssignmentView(APIView):
    permission_classes = [IsAuthenticated, HasPlatformPermission]
    required_permission = "authorization.users.assign_role"

    @extend_schema(responses=UserRoleSerializer(many=True))
    def get(self, request, user_id):
        target = get_object_or_404(get_user_model(), pk=user_id)
        assignments = UserRole.objects.filter(user=target).select_related("role")
        return Response(UserRoleSerializer(assignments, many=True).data)

    @extend_schema(request=UserRoleSerializer, responses=UserRoleSerializer)
    def post(self, request, user_id):
        target = get_object_or_404(get_user_model(), pk=user_id)
        serializer = UserRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        if role.key == Role.Key.OWNER:
            return Response({"detail": "Owner access must be bootstrapped administratively."}, status=status.HTTP_403_FORBIDDEN)
        assignment, created = UserRole.objects.get_or_create(user=target, role=role, defaults={"assigned_by": request.user})
        if created:
            record_audit(request, "authorization.role_assigned", resource_type="user", resource_id=target.pk, metadata={"role": role.key})
        return Response(UserRoleSerializer(assignment).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @extend_schema(responses={204: None, 400: dict, 404: dict})
    def delete(self, request, user_id):
        target = get_object_or_404(get_user_model(), pk=user_id)
        role_key = request.query_params.get("role")
        if not role_key or role_key == Role.Key.OWNER:
            return Response({"detail": "A removable role key is required."}, status=status.HTTP_400_BAD_REQUEST)
        assignment = get_object_or_404(UserRole, user=target, role__key=role_key)
        assignment.delete()
        record_audit(request, "authorization.role_removed", resource_type="user", resource_id=target.pk, metadata={"role": role_key})
        return Response(status=status.HTTP_204_NO_CONTENT)
