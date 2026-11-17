from django.urls import path

from apps.accounts.views import (
    CurrentUserView,
    EmailVerificationView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileView,
    RegistrationView,
    RefreshView,
    SessionListView,
    SessionRevokeView,
    health,
)

urlpatterns = [
    path("health/", health, name="health"),
    path("auth/register/", RegistrationView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/verify-email/", EmailVerificationView.as_view(), name="auth-verify-email"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("auth/me/", CurrentUserView.as_view(), name="auth-me"),
    path("profile/", ProfileView.as_view(), name="account-profile"),
    path("auth/sessions/", SessionListView.as_view(), name="auth-sessions"),
    path("auth/sessions/<uuid:session_id>/", SessionRevokeView.as_view(), name="auth-session-revoke"),
]
