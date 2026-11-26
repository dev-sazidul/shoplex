from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.accounts.models import User
from apps.authorization.models import Role
from apps.catalog.models import Product
from apps.commerce.models import SellerOrder, SellerPayoutRequest
from apps.commerce.serializers import PayoutRequestInputSerializer, PayoutRequestSerializer
from apps.platform.models import SellerApplication, SellerApplicationApproval
from apps.sellers.permissions import IsActiveSeller
from apps.sellers.serializers import (
    SellerApplicationDecisionSerializer,
    SellerApplicationSerializer,
    SellerApplicationSubmissionSerializer,
)
from apps.sellers.services import review_seller_application, reviewer_role_for


class MySellerApplicationView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(responses={200: dict})
    def get(self, request):
        application = SellerApplication.objects.filter(user=request.user).prefetch_related("approval_history", "documents").order_by("-submitted_at").first()
        if not application:
            return Response({"status": "not_applied"})
        return Response(SellerApplicationSerializer(application).data)

    @extend_schema(request=SellerApplicationSubmissionSerializer, responses=SellerApplicationSerializer)
    def post(self, request):
        serializer = SellerApplicationSubmissionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        return Response(SellerApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class SellerApplicationReviewQueueView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SellerApplicationSerializer

    def get_queryset(self):
        reviewer_role_for(self.request.user)
        return SellerApplication.objects.filter(status__in=[SellerApplication.Status.PENDING, SellerApplication.Status.NEEDS_INFO]).select_related("user").prefetch_related("approval_history", "documents")


class SellerApplicationReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=SellerApplicationDecisionSerializer, responses=SellerApplicationSerializer)
    def post(self, request, application_id):
        serializer = SellerApplicationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = review_seller_application(
            request,
            application_id,
            serializer.validated_data["decision"],
            serializer.validated_data.get("reason", ""),
        )
        return Response(SellerApplicationSerializer(application).data)


class SellerDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]

    @extend_schema(responses={200: dict})
    def get(self, request):
        seller = request.user.seller_profile
        products = Product.objects.filter(seller=seller)
        seller_orders = SellerOrder.objects.filter(seller=seller)
        completed = seller_orders.filter(status=SellerOrder.Status.COMPLETED)
        pending_payouts = SellerPayoutRequest.objects.filter(seller=seller, status__in=[SellerPayoutRequest.Status.PENDING, SellerPayoutRequest.Status.APPROVED])
        paid_payouts = SellerPayoutRequest.objects.filter(seller=seller, status=SellerPayoutRequest.Status.PAID)
        sale_total = seller.earnings_ledger.filter(entry_type__in=["sale", "adjustment"]).aggregate(total=Sum("amount"))["total"] or 0
        refund_total = seller.earnings_ledger.filter(entry_type="refund").aggregate(total=Sum("amount"))["total"] or 0
        earning_total = sale_total - refund_total
        sales_total = completed.aggregate(total=Sum("subtotal"))["total"] or 0
        commission_total = completed.aggregate(total=Sum("commission_amount"))["total"] or 0
        pending_order_earnings = seller_orders.exclude(status__in=[SellerOrder.Status.COMPLETED, SellerOrder.Status.CANCELLED, SellerOrder.Status.REFUNDED]).aggregate(total=Sum("net_earnings"))["total"] or 0
        return Response({
            "products": {
                "total": products.count(),
                "published": products.filter(status=Product.Status.PUBLISHED).count(),
                "pending": products.filter(status=Product.Status.PENDING_APPROVAL).count(),
                "rejected": products.filter(status=Product.Status.REJECTED).count(),
                "drafts": products.filter(status=Product.Status.DRAFT).count(),
            },
            "orders": {
                "total": seller_orders.count(),
                "completed": completed.count(),
                "units_sold": completed.aggregate(total=Sum("items__quantity"))["total"] or 0,
            },
            "finance": {
                "gross_sales": sales_total,
                "platform_commission": commission_total,
                "refunds": refund_total,
                "net_earnings": earning_total,
                "pending_settlement": pending_order_earnings,
                "available_balance": max(earning_total - (pending_payouts.aggregate(total=Sum("amount"))["total"] or 0), 0),
                "pending_payouts": pending_payouts.count(),
                "completed_payouts": paid_payouts.count(),
            },
        })


class SellerPayoutRequestView(APIView):
    permission_classes = [IsAuthenticated, IsActiveSeller]

    @extend_schema(responses={200: PayoutRequestSerializer(many=True)})
    def get(self, request):
        requests = SellerPayoutRequest.objects.filter(seller=request.user.seller_profile)
        return Response([{"id": str(row.pk), "amount": row.amount, "status": row.status, "requested_at": row.requested_at} for row in requests])

    @extend_schema(request=PayoutRequestInputSerializer, responses=PayoutRequestSerializer)
    def post(self, request):
        from decimal import Decimal, InvalidOperation
        from django.db import transaction
        from django.db.models import Sum
        from rest_framework.exceptions import ValidationError

        try:
            amount = Decimal(str(request.data.get("amount", "")))
        except (InvalidOperation, ValueError):
            raise ValidationError({"amount": "Enter a valid payout amount."})
        if amount <= 0:
            raise ValidationError({"amount": "Payout amount must be positive."})
        with transaction.atomic():
            seller = request.user.seller_profile.__class__.objects.select_for_update().get(pk=request.user.seller_profile.pk)
            lifetime_credits = seller.earnings_ledger.filter(entry_type__in=["sale", "adjustment"]).aggregate(total=Sum("amount"))["total"] or 0
            lifetime_debits = seller.earnings_ledger.filter(entry_type="refund").aggregate(total=Sum("amount"))["total"] or 0
            reserved = SellerPayoutRequest.objects.filter(seller=seller, status__in=["pending", "approved"]).aggregate(total=Sum("amount"))["total"] or 0
            available = lifetime_credits - lifetime_debits - reserved
            if amount > available:
                raise ValidationError({"amount": "Requested amount exceeds the available balance."})
            payout = SellerPayoutRequest.objects.create(seller=seller, amount=amount)
        return Response({"id": str(payout.pk), "amount": payout.amount, "status": payout.status}, status=status.HTTP_201_CREATED)
