from datetime import datetime, timezone
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone as django_timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema_field

from apps.authorization.models import Role, UserRole
from apps.platform.audit import record_audit
from apps.accounts.models import UserProfile
from apps.platform.models import AuthSession

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "status", "email_verified_at", "roles"]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_roles(self, user):
        return list(user.role_assignments.select_related("role").values_list("role__key", flat=True))


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name", allow_blank=True, required=False)
    phone_number = serializers.CharField(source="user.phone_number", allow_blank=True, required=False)

    class Meta:
        model = UserProfile
        fields = ["email", "first_name", "last_name", "phone_number", "avatar_url", "locale", "timezone"]

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        user = instance.user
        for field in ("first_name", "last_name", "phone_number"):
            if field in user_data:
                setattr(user, field, user_data[field])
        if user_data:
            user.save(update_fields=[*user_data.keys(), "updated_at"])
        return super().update(instance, validated_data)


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "phone_number", "password"]

    def validate_password(self, value):
        validate_password(value, user=User(email=self.initial_data.get("email", ""), first_name=self.initial_data.get("first_name", "")))
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, status=User.Status.PENDING, **validated_data)
        UserProfile.objects.create(user=user)
        customer_role, _ = Role.objects.get_or_create(key=Role.Key.CUSTOMER, defaults={"name": "Customer"})
        UserRole.objects.create(user=user, role=customer_role)
        token = signing.dumps(str(user.pk), salt="shoplex.email-verification")
        send_mail(
            "Verify your SHOPLEX email",
            f"Use this verification token with POST /api/v1/auth/verify-email/: {token}",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        request = self.context.get("request")
        if request:
            record_audit(request, "account.registered", resource_type="user", resource_id=user.pk)
        return user


class SessionTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.status != User.Status.ACTIVE:
            raise AuthenticationFailed("Verify your email address before signing in.")
        refresh = RefreshToken(data["refresh"])
        session_id = str(uuid.uuid4())
        refresh["sid"] = session_id
        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        request = self.context.get("request")
        lifetime = refresh["exp"]
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:512] if request else ""
        ip_address = request.META.get("REMOTE_ADDR") if request else None
        is_owner = self.user.role_assignments.filter(role__key=Role.Key.OWNER).exists()
        previous_sessions = AuthSession.objects.filter(user=self.user)
        suspicious = bool(
            is_owner
            and previous_sessions.exists()
            and not previous_sessions.filter(ip_address=ip_address, user_agent=user_agent).exists()
        )
        AuthSession.objects.create(
            id=session_id,
            user=self.user,
            refresh_jti=refresh["jti"],
            expires_at=datetime.fromtimestamp(lifetime, tz=timezone.utc),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        if is_owner:
            from apps.platform.models import Notification
            Notification.objects.create(
                user=self.user,
                category="security_alert",
                title="Suspicious login detected" if suspicious else "Owner console sign-in alert",
                body=f"Sign-in from IP {ip_address or 'unknown'} ({user_agent or 'unknown device'}).",
                payload={"session_id": session_id, "suspicious": suspicious, "ip_address": ip_address},
            )
        if request:
            record_audit(
                request,
                "auth.login.suspicious" if suspicious else "auth.login",
                resource_type="user",
                resource_id=self.user.pk,
                metadata={"suspicious": suspicious},
            )
        data["user"] = UserSerializer(self.user).data
        return data


class SessionTokenRefreshSerializer(TokenRefreshSerializer):
    @transaction.atomic
    def validate(self, attrs):
        presented = RefreshToken(attrs["refresh"])
        session_id = presented.get("sid")
        if not session_id:
            raise AuthenticationFailed("Refresh token is not tied to an active session.")
        try:
            session = AuthSession.objects.select_for_update().get(pk=session_id, revoked_at__isnull=True)
        except (AuthSession.DoesNotExist, ValueError):
            raise AuthenticationFailed("Session has been revoked.")
        if session.refresh_jti != presented.get("jti") or session.expires_at <= django_timezone.now():
            raise AuthenticationFailed("Refresh token is no longer current.")
        if not session.user.is_active or session.user.status != User.Status.ACTIVE:
            raise AuthenticationFailed("This account is not active.")
        data = super().validate(attrs)
        rotated = RefreshToken(data["refresh"])
        session.refresh_jti = rotated["jti"]
        session.expires_at = datetime.fromtimestamp(rotated["exp"], tz=timezone.utc)
        session.save(update_fields=["refresh_jti", "expires_at", "last_used_at"])
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self):
        user = User.objects.filter(email__iexact=self.validated_data["email"], is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_mail(
                "Reset your SHOPLEX password",
                f"Reset token for account {uid}: {token}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            self.user = User.objects.get(pk=user_id, is_active=True)
        except (ValueError, TypeError, User.DoesNotExist):
            raise serializers.ValidationError({"uid": "Invalid password reset request."})
        if not default_token_generator.check_token(self.user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired password reset token."})
        validate_password(attrs["new_password"], user=self.user)
        return attrs

    @transaction.atomic
    def save(self):
        self.user.set_password(self.validated_data["new_password"])
        self.user.save(update_fields=["password"])
        AuthSession.objects.filter(user=self.user, revoked_at__isnull=True).update(revoked_at=django_timezone.now())
