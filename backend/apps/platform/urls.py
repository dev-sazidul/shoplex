from django.urls import path

from apps.platform.admin_staff import (
    AdminCustomersManageView,
    AdminMyPermissionsView,
    AdminOrdersManageView,
    AdminPlatformProductDetailView,
    AdminPlatformProductListCreateView,
    AdminPlatformProductPublishView,
    AdminRefundProcessView,
    AdminSelectedFinanceReportView,
    OwnerAdminStaffListCreateView,
    OwnerAdminStaffPermissionView,
    OwnerAdminStaffStatusView,
)
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
    path("owner/admins/", OwnerAdminStaffListCreateView.as_view(), name="owner-admin-staff-list-create"),
    path("owner/admins/<uuid:admin_id>/status/", OwnerAdminStaffStatusView.as_view(), name="owner-admin-staff-status"),
    path("owner/admins/<uuid:admin_id>/permissions/", OwnerAdminStaffPermissionView.as_view(), name="owner-admin-staff-permissions"),
    path("admin-staff/me/permissions/", AdminMyPermissionsView.as_view(), name="admin-my-permissions"),
    path("admin-staff/products/", AdminPlatformProductListCreateView.as_view(), name="admin-platform-products"),
    path("admin-staff/products/<uuid:product_id>/", AdminPlatformProductDetailView.as_view(), name="admin-platform-product-detail"),
    path("admin-staff/products/<uuid:product_id>/publish/", AdminPlatformProductPublishView.as_view(), name="admin-platform-product-publish"),
    path("admin-staff/orders/", AdminOrdersManageView.as_view(), name="admin-orders-manage"),
    path("admin-staff/customers/", AdminCustomersManageView.as_view(), name="admin-customers-manage"),
    path("admin-staff/finance-report/", AdminSelectedFinanceReportView.as_view(), name="admin-finance-report"),
    path("admin-staff/refunds/<uuid:order_id>/", AdminRefundProcessView.as_view(), name="admin-refund-process"),
]
