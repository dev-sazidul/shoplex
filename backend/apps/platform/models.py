import uuid

from django.conf import settings
from django.db import models

from apps.platform.storage import PrivateDocumentStorage


class AuthSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="auth_sessions")
    refresh_jti = models.CharField(max_length=255, unique=True)
    user_agent = models.CharField(max_length=512, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["user", "revoked_at", "expires_at"])]


class MFADevice(models.Model):
    class Method(models.TextChoices):
        TOTP = "totp", "Authenticator app"
        EMAIL = "email", "Email code"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mfa_devices")
    method = models.CharField(max_length=12, choices=Method.choices)
    name = models.CharField(max_length=100, blank=True)
    secret_encrypted = models.CharField(max_length=512, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "method", "name"], name="uniq_user_mfa_device")]


class SellerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_profile")
    business_name = models.CharField(max_length=180)
    store_slug = models.SlugField(max_length=180, unique=True, null=True, blank=True)
    store_description = models.TextField(blank=True)
    business_type = models.CharField(max_length=80, blank=True)
    business_address = models.TextField(blank=True)
    business_phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SellerApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        NEEDS_INFO = "needs_info", "More information required"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_applications")
    business_name = models.CharField(max_length=180)
    business_type = models.CharField(max_length=80, blank=True)
    business_address = models.TextField()
    verification_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    review_cycle = models.PositiveIntegerField(default=1)
    review_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="seller_applications_reviewed")
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "submitted_at"])]
        constraints = [models.UniqueConstraint(fields=["user"], condition=models.Q(status__in=["pending", "needs_info"]), name="uniq_active_seller_application")]


def seller_document_upload_path(instance, filename):
    return f"private/seller-applications/{instance.application_id}/{uuid.uuid4().hex}"


class SellerDocument(models.Model):
    application = models.ForeignKey(SellerApplication, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to=seller_document_upload_path, storage=PrivateDocumentStorage())
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)


class SellerApplicationApproval(models.Model):
    class ReviewerRole(models.TextChoices):
        ADMIN = "admin", "Admin"
        OWNER = "owner", "Owner"

    class Decision(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        NEEDS_INFO = "needs_info", "More information required"

    application = models.ForeignKey(SellerApplication, on_delete=models.CASCADE, related_name="approval_history")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="seller_application_decisions")
    reviewer_role = models.CharField(max_length=10, choices=ReviewerRole.choices)
    decision = models.CharField(max_length=12, choices=Decision.choices)
    cycle = models.PositiveIntegerField(default=1)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["application", "reviewer_role", "created_at"])]


class ManagerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="manager_profile")
    title = models.CharField(max_length=120, blank=True)
    business_unit = models.CharField(max_length=120, blank=True)
    responsibilities = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managers_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ManagerInvitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(db_index=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="manager_invitations_sent")
    token_digest = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    category = models.CharField(max_length=50, db_index=True)
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "read_at", "created_at"])]


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events")
    action = models.CharField(max_length=120, db_index=True)
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["actor", "created_at"])]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("Audit log records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log records are append-only.")


class PlatformSetting(models.Model):
    key = models.SlugField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    description = models.CharField(max_length=255, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="platform_settings_updated")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key



class AdminAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manager = models.ForeignKey(ManagerProfile, on_delete=models.CASCADE, related_name="admin_assignments")
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="manager_assignments")
    responsibilities = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="admin_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["manager", "admin"],
                condition=models.Q(is_active=True),
                name="uniq_active_manager_admin_assignment",
            )
        ]
        indexes = [models.Index(fields=["manager", "is_active"]), models.Index(fields=["admin", "is_active"])]


class AdminAssignmentHistory(models.Model):
    class Action(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        REASSIGNED = "reassigned", "Reassigned"
        REMOVED = "removed", "Removed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assignment_history")
    manager = models.ForeignKey(
        ManagerProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assignment_history",
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    note = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="admin_assignment_actions",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class BusinessSharePlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    code = models.SlugField(max_length=80, unique=True)
    total_authorized_shares = models.PositiveIntegerField(default=100000)
    max_allocated_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    company_valuation = models.DecimalField(max_digits=16, decimal_places=2)
    currency = models.CharField(max_length=3, default="BDT")
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="share_plans_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_allocated_percentage__gt=0) & models.Q(max_allocated_percentage__lte=100),
                name="share_plan_max_percentage_range",
            ),
            models.CheckConstraint(
                condition=models.Q(company_valuation__gt=0),
                name="share_plan_positive_valuation",
            ),
        ]


class BusinessShare(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BusinessSharePlan, on_delete=models.CASCADE, related_name="share_classes")
    class_name = models.CharField(max_length=120)
    share_count = models.PositiveIntegerField()
    percentage_represented = models.DecimalField(max_digits=5, decimal_places=2)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["class_name"]


class ShareOffer(models.Model):
    class Status(models.TextChoices):
        OFFERED = "offered", "Offered"
        ACCEPTED = "accepted", "Accepted"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BusinessSharePlan, on_delete=models.CASCADE, related_name="offers")
    partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="share_offers")
    offered_shares = models.PositiveIntegerField()
    offered_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    valuation_at_offer = models.DecimalField(max_digits=16, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OFFERED, db_index=True)
    terms_note = models.TextField(blank=True)
    offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="share_offers_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ShareAllocation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TRANSFERRED = "transferred", "Transferred"
        REVOKED = "revoked", "Revoked"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BusinessSharePlan, on_delete=models.CASCADE, related_name="allocations")
    holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="share_allocations")
    allocated_shares = models.PositiveIntegerField()
    ownership_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="share_allocations_made",
    )
    allocated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ownership_percentage", "-allocated_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ownership_percentage__gt=0) & models.Q(ownership_percentage__lte=100),
                name="share_allocation_percentage_range",
            )
        ]


class ShareTransaction(models.Model):
    class TransactionType(models.TextChoices):
        ALLOCATION = "allocation", "Initial allocation"
        TRANSFER = "transfer", "Permitted share transfer"
        REVOCATION = "revocation", "Allocation revocation"
        VALUATION_UPDATE = "valuation_update", "Valuation update"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BusinessSharePlan, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, db_index=True)
    from_holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="share_transactions_out",
    )
    to_holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="share_transactions_in",
    )
    shares_count = models.PositiveIntegerField(default=0)
    percentage_delta = models.DecimalField(max_digits=5, decimal_places=2)
    valuation_snapshot = models.DecimalField(max_digits=16, decimal_places=2)
    legal_reference = models.CharField(max_length=160, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="share_transactions_recorded",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("Share transaction records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Share transaction records are append-only.")


class OwnershipHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BusinessSharePlan, on_delete=models.PROTECT, related_name="ownership_history")
    holder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ownership_snapshots")
    previous_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    new_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=255)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ownership_history_recorded",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError("Ownership history records are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Ownership history records are append-only.")


class ShareDocument(models.Model):
    class DocumentType(models.TextChoices):
        AGREEMENT = "agreement", "Shareholder agreement"
        CERTIFICATE = "certificate", "Share certificate"
        TRANSFER_DEED = "transfer_deed", "Transfer deed"
        VALUATION_REPORT = "valuation_report", "Valuation report"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BusinessSharePlan, on_delete=models.CASCADE, related_name="documents")
    holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="share_documents",
    )
    title = models.CharField(max_length=180)
    document_type = models.CharField(max_length=24, choices=DocumentType.choices, default=DocumentType.CERTIFICATE)
    reference_number = models.CharField(max_length=120)
    summary = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="share_documents_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
