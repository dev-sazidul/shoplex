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
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="managers_created")
    created_at = models.DateTimeField(auto_now_add=True)


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
