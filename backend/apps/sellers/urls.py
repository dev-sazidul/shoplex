from django.urls import path

from apps.sellers.views import (
    MySellerApplicationView,
    SellerApplicationReviewQueueView,
    SellerApplicationReviewView,
    SellerDashboardView,
    SellerPayoutRequestView,
)
from apps.sellers.document_views import SellerDocumentDownloadView

urlpatterns = [
    path("seller/application/", MySellerApplicationView.as_view(), name="seller-application"),
    path("management/seller-applications/", SellerApplicationReviewQueueView.as_view(), name="seller-application-review-queue"),
    path("management/seller-applications/<int:application_id>/review/", SellerApplicationReviewView.as_view(), name="seller-application-review"),
    path("management/seller-applications/<int:application_id>/documents/<int:document_id>/", SellerDocumentDownloadView.as_view(), name="seller-application-document"),
    path("seller/dashboard/", SellerDashboardView.as_view(), name="seller-dashboard"),
    path("seller/payout-requests/", SellerPayoutRequestView.as_view(), name="seller-payout-requests"),
]
