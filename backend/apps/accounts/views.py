from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema

from apps.accounts.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RegistrationSerializer,
    SessionTokenObtainPairSerializer,
    SessionTokenRefreshSerializer,
    UserSerializer,
)
from apps.platform.audit import record_audit
from apps.platform.models import AuthSession

User = get_user_model()


class TokenRequestSerializer(serializers.Serializer):
    token = serializers.CharField()


class LogoutRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, allow_blank=True)


class LoginView(TokenObtainPairView):
    serializer_class = SessionTokenObtainPairSerializer
    throttle_scope = "auth"


class RefreshView(TokenRefreshView):
    serializer_class = SessionTokenRefreshSerializer
    throttle_scope = "auth"


@extend_schema(operation_id="health_check", responses={200: dict})
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok", "service": "shoplex-api", "api_version": "v1"})


class RegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth"


class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "auth"

    @extend_schema(request=TokenRequestSerializer, responses={200: dict, 400: dict})
    def post(self, request):
        token = request.data.get("token", "")
        try:
            user_id = signing.loads(token, salt="shoplex.email-verification", max_age=86400)
            user = User.objects.get(pk=user_id, is_active=True)
        except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist, ValueError):
            return Response({"detail": "Verification token is invalid or expired."}, status=status.HTTP_400_BAD_REQUEST)
        if user.email_verified_at is None:
            user.email_verified_at = timezone.now()
            user.status = User.Status.ACTIVE
            user.save(update_fields=["email_verified_at", "status", "updated_at"])
            record_audit(request, "account.email_verified", resource_type="user", resource_id=user.pk)
        return Response({"detail": "Email verified. You can now sign in."})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutRequestSerializer, responses={204: None})
    def post(self, request):
        session_id = request.auth.get("sid")
        session = AuthSession.objects.filter(pk=session_id, user=request.user, revoked_at__isnull=True).first()
        if session:
            session.revoked_at = timezone.now()
            session.save(update_fields=["revoked_at"])
            refresh_value = request.data.get("refresh")
            if refresh_value:
                try:
                    refresh = RefreshToken(refresh_value)
                    if refresh.get("sid") == str(session.pk) and refresh.get("jti") == session.refresh_jti:
                        refresh.blacklist()
                except TokenError:
                    pass
            record_audit(request, "auth.logout", resource_type="session", resource_id=session.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ProfileSerializer)
    def get(self, request):
        from apps.accounts.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return Response(ProfileSerializer(profile).data)

    @extend_schema(request=ProfileSerializer, responses=ProfileSerializer)
    def patch(self, request):
        from apps.accounts.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record_audit(request, "account.profile_updated", resource_type="user", resource_id=request.user.pk)
        return Response(serializer.data)


class SessionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    class SessionSerializer(serializers.Serializer):
        id = serializers.UUIDField()
        user_agent = serializers.CharField(allow_blank=True)
        ip_address = serializers.IPAddressField(allow_null=True)
        created_at = serializers.DateTimeField()
        last_used_at = serializers.DateTimeField()
        expires_at = serializers.DateTimeField()
        revoked = serializers.BooleanField()
        current = serializers.BooleanField()

    serializer_class = SessionSerializer

    def list(self, request, *args, **kwargs):
        sessions = AuthSession.objects.filter(user=request.user).order_by("-created_at")
        results = [{
            "id": str(session.id),
            "user_agent": session.user_agent,
            "ip_address": session.ip_address,
            "created_at": session.created_at,
            "last_used_at": session.last_used_at,
            "expires_at": session.expires_at,
            "revoked": session.revoked_at is not None,
            "current": str(session.id) == str(request.auth.get("sid")),
        } for session in sessions]
        return Response(results)


class SessionRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None, 404: None})
    def delete(self, request, session_id):
        session = AuthSession.objects.filter(user=request.user, pk=session_id, revoked_at__isnull=True).first()
        if not session:
            return Response(status=status.HTTP_404_NOT_FOUND)
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])
        record_audit(request, "auth.session_revoked", resource_type="session", resource_id=session.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "auth"

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: dict})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "If the account exists, password reset instructions have been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "auth"

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: dict})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password has been reset. Sign in with your new password."})
