from apps.platform.models import AuditLog


def record_audit(request, action, *, resource_type="", resource_id="", metadata=None):
    actor = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    address = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR")
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        ip_address=address or None,
        metadata=metadata or {},
    )
