from django.urls import path, include
from .views import PublicHomepageView, CurrentUserRoleView, RedisTestView
from .auth_views import LoginView, GoogleLoginView
from client.v1.views.account import PasswordResetRequestView, PasswordResetConfirmView

urlpatterns = [
    path("auth/me/", CurrentUserRoleView.as_view(), name="current-user-role"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/google-login/", GoogleLoginView.as_view(), name="google-login"),
    path(
        "auth/forget-password/",
        PasswordResetRequestView.as_view(),
        name="forget-password",
    ),
    path(
        "auth/verify-reset-password/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="verify-reset-password",
    ),
    path("cms/homepage/", PublicHomepageView.as_view(), name="public-homepage"),
    path("system/redis-test/", RedisTestView.as_view(), name="redis-test"),
    path("auth/mfa/", include("common.mfa.urls")),
]
