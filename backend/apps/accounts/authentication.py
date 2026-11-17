from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.platform.models import AuthSession


class SessionJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        session_id = token.get("sid")
        if not session_id:
            raise AuthenticationFailed("Session is invalid or has been revoked.")
        try:
            session = AuthSession.objects.get(pk=session_id, user=user, revoked_at__isnull=True)
        except (AuthSession.DoesNotExist, ValueError):
            raise AuthenticationFailed("Session is invalid or has been revoked.")
        if session.expires_at <= timezone.now():
            raise AuthenticationFailed("Session has expired.")
        if not user.is_active or user.status != user.Status.ACTIVE:
            raise AuthenticationFailed("This account is not active.")
        return user, token
