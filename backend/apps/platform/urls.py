from django.urls import path

from apps.platform.manager_governance import (
    ManagerPortalDashboardView,
    OwnerAdminAssignmentView,
    OwnerManagerListCreateView,
    OwnerManagerPermissionView,
    OwnerManagerStatusActionView,
    OwnerShareAllocationCreateView,
    OwnerShareDocumentCreateView,
    OwnerShareOfferCreateView,
    OwnerSharePlanListCreateView,
    OwnerShareTransferCreateView,
)
from apps.platform.views import NotificationListView, NotificationReadView

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/<uuid:notification_id>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("manager/dashboard/", ManagerPortalDashboardView.as_view(), name="manager-portal-dashboard"),
    path("owner/managers/", OwnerManagerListCreateView.as_view(), name="owner-manager-list-create"),
    path("owner/managers/<int:manager_id>/status/", OwnerManagerStatusActionView.as_view(), name="owner-manager-status"),
    path("owner/managers/<int:manager_id>/permissions/", OwnerManagerPermissionView.as_view(), name="owner-manager-permissions"),
    path("owner/admin-assignments/", OwnerAdminAssignmentView.as_view(), name="owner-admin-assignments"),
    path("owner/shares/plans/", OwnerSharePlanListCreateView.as_view(), name="owner-share-plans"),
    path("owner/shares/offers/", OwnerShareOfferCreateView.as_view(), name="owner-share-offers"),
    path("owner/shares/allocations/", OwnerShareAllocationCreateView.as_view(), name="owner-share-allocations"),
    path("owner/shares/transfers/", OwnerShareTransferCreateView.as_view(), name="owner-share-transfers"),
    path("owner/shares/documents/", OwnerShareDocumentCreateView.as_view(), name="owner-share-documents"),
]
