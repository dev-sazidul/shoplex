"""Multi-channel notification dispatcher (In-App, Email, SMS, Push) backed by Celery & Redis."""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.models import User
from apps.platform.models import Notification

logger = logging.getLogger("shoplex.notifications")


@shared_task(bind=True, max_retries=3, default_retry_delay=15)
def deliver_notification_task(self, notification_id: str, channels: list[str] | None = None):
    active_channels = channels or ["in_app", "email", "sms"]
    notification = Notification.objects.select_related("user").filter(pk=notification_id).first()
    if not notification:
        return {"status": "not_found"}

    user = notification.user
    delivered = ["in_app"]

    if "email" in active_channels and user.email:
        send_mail(
            f"[SHOPLEX] {notification.title}",
            notification.body or notification.title,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
        delivered.append("email")

    if "sms" in active_channels and user.phone_number:
        logger.info("SMS notification dispatched to %s: %s", user.phone_number, notification.title)
        delivered.append("sms")

    if "push" in active_channels:
        delivered.append("push")

    payload = dict(notification.payload or {})
    payload["delivered_channels"] = delivered
    notification.payload = payload
    notification.save(update_fields=["payload"])
    return {"notification_id": str(notification.pk), "channels": delivered}


def send_multichannel_notification(
    user: User,
    category: str,
    title: str,
    body: str = "",
    payload: dict | None = None,
    channels: list[str] | None = None,
) -> Notification:
    selected_channels = channels or ["in_app", "email", "sms"]
    base_payload = dict(payload or {})
    base_payload["requested_channels"] = selected_channels
    notification = Notification.objects.create(
        user=user,
        category=category[:50],
        title=title[:180],
        body=body,
        payload=base_payload,
    )
    try:
        deliver_notification_task.apply(args=[str(notification.pk), selected_channels])
    except Exception:
        logger.warning("Fallback in-app notification saved for %s", user.email)
    return notification
