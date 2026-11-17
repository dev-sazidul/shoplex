from django.urls import path

from apps.authorization.views import PermissionListView, RoleAssignmentView, RoleListView

urlpatterns = [
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("permissions/", PermissionListView.as_view(), name="permission-list"),
    path("users/<uuid:user_id>/roles/", RoleAssignmentView.as_view(), name="user-role-assignments"),
]
