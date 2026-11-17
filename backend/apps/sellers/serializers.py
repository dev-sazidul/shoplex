from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import UserProfile
from apps.authorization.models import Role, UserRole
from apps.platform.models import (
    SellerApplication,
    SellerApplicationApproval,
    SellerDocument,
    SellerProfile,
)

User = get_user_model()


class SellerDocumentSummarySerializer(serializers.ModelSerializer):
    download_path = serializers.SerializerMethodField()

    class Meta:
        model = SellerDocument
        fields = ["id", "original_name", "content_type", "uploaded_at", "download_path"]
        read_only_fields = fields

    def get_download_path(self, document) -> str:
        return f"/api/v1/management/seller-applications/{document.application_id}/documents/{document.pk}/"


class SellerApplicationApprovalSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = SellerApplicationApproval
        fields = ["reviewer_role", "decision", "reason", "reviewer_name", "created_at", "cycle"]

    def get_reviewer_name(self, approval) -> str:
        return f"{approval.reviewer.first_name} {approval.reviewer.last_name}".strip()


class SellerApplicationSerializer(serializers.ModelSerializer):
    approvals = serializers.SerializerMethodField()
    documents = SellerDocumentSummarySerializer(many=True, read_only=True)

    class Meta:
        model = SellerApplication
        fields = [
            "id", "business_name", "business_type", "business_address", "verification_reference",
            "status", "review_reason", "review_cycle", "submitted_at", "reviewed_at", "approvals", "documents",
        ]
        read_only_fields = fields

    @extend_schema_field(SellerApplicationApprovalSerializer(many=True))
    def get_approvals(self, application) -> list[dict]:
        return SellerApplicationApprovalSerializer(
            application.approval_history.filter(cycle=application.review_cycle).select_related("reviewer"), many=True,
        ).data


class SellerApplicationSubmissionSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=180)
    business_type = serializers.CharField(max_length=80)
    business_address = serializers.CharField()
    business_phone = serializers.CharField(max_length=30)
    store_description = serializers.CharField(required=False, allow_blank=True)
    verification_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    documents = serializers.ListField(child=serializers.FileField(), required=False, write_only=True, max_length=6)

    def validate_documents(self, files):
        allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg"}
        allowed_types = {"application/pdf", "image/png", "image/jpeg"}
        for file in files:
            if Path(file.name).suffix.lower() not in allowed_extensions:
                raise serializers.ValidationError("Only PDF, PNG, and JPEG documents are accepted.")
            if file.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("Each document must be 10 MB or smaller.")
            if file.content_type and file.content_type not in allowed_types:
                raise serializers.ValidationError("The uploaded file type is not allowed.")
            signature = file.read(8)
            file.seek(0)
            if not (signature.startswith(b"%PDF-") or signature.startswith(b"\x89PNG\r\n\x1a\n") or signature.startswith(b"\xff\xd8\xff")):
                raise serializers.ValidationError("The file contents do not match an allowed document type.")
        return files

    @transaction.atomic
    def create(self, validated_data):
        documents = validated_data.pop("documents", [])
        user = self.context["request"].user
        User.objects.select_for_update().get(pk=user.pk)
        if hasattr(user, "seller_profile") and user.seller_profile.is_active:
            raise serializers.ValidationError("This account already has an active seller profile.")

        existing = SellerApplication.objects.select_for_update().filter(
            user=user, status__in=[SellerApplication.Status.PENDING, SellerApplication.Status.NEEDS_INFO],
        ).order_by("-submitted_at").first()
        if existing and existing.status == SellerApplication.Status.PENDING:
            raise serializers.ValidationError("An application is already awaiting review.")

        profile, _ = SellerProfile.objects.get_or_create(
            user=user,
            defaults={"business_name": validated_data["business_name"]},
        )
        profile.business_name = validated_data["business_name"]
        profile.business_type = validated_data["business_type"]
        profile.business_address = validated_data["business_address"]
        profile.business_phone = validated_data["business_phone"]
        profile.store_description = validated_data.get("store_description", "")
        if not profile.store_slug:
            profile.store_slug = f"{slugify(profile.business_name)[:150]}-{str(user.pk)[:8]}"
        profile.is_active = False
        profile.save()

        if existing:
            application = existing
            for field in ("business_name", "business_type", "business_address", "verification_reference"):
                setattr(application, field, validated_data.get(field, ""))
            application.status = SellerApplication.Status.PENDING
            application.review_reason = ""
            application.review_cycle += 1
            application.submitted_at = timezone.now()
            application.reviewed_by = None
            application.reviewed_at = None
            application.save()
        else:
            application_fields = {
                field: validated_data[field]
                for field in ("business_name", "business_type", "business_address", "verification_reference")
                if field in validated_data
            }
            application = SellerApplication.objects.create(user=user, **application_fields)

        for file in documents:
            SellerDocument.objects.create(
                application=application,
                file=file,
                original_name=Path(file.name).name[:255],
                content_type=file.content_type or "application/octet-stream",
            )

        self._notify_reviewers(application)
        return application

    def _notify_reviewers(self, application):
        from apps.platform.models import Notification

        reviewer_ids = UserRole.objects.filter(
            role__key__in=[Role.Key.ADMIN, Role.Key.OWNER], user__is_active=True, user__status="active",
        ).values_list("user_id", flat=True).distinct()
        Notification.objects.bulk_create([
            Notification(
                user_id=user_id,
                category="seller_application",
                title="Seller application needs review",
                body=f"{application.business_name} submitted a seller application.",
                payload={"application_id": str(application.pk)},
            ) for user_id in reviewer_ids
        ])


class SellerApplicationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=SellerApplicationApproval.Decision.choices)
    reason = serializers.CharField(required=False, allow_blank=True)


class SellerProfilePublicSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = SellerProfile
        fields = ["store_slug", "business_name", "store_description", "display_name"]

    def get_display_name(self, profile) -> str:
        return profile.business_name
