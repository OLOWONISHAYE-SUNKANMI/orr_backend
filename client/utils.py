from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

token_generator = PasswordResetTokenGenerator()


def build_verify_password_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)
    base = settings.FRONTEND_VERIFY_EMAIL_URL
    return f"{base}?uid={uid}&token={token}&email={user.email}"


def create_password_reset_url(user, portal="client"):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)
    
    if portal == "admin":
        base = getattr(settings, "FRONTEND_ADMIN_RESET_URL", settings.FRONTEND_RESET_PASSWORD_URL)
    elif portal == "consultant":
        base = getattr(settings, "FRONTEND_CONSULTANT_RESET_URL", settings.FRONTEND_RESET_PASSWORD_URL)
    elif portal == "pm":
        base = getattr(settings, "FRONTEND_PM_RESET_URL", settings.FRONTEND_RESET_PASSWORD_URL)
    else:
        base = settings.FRONTEND_RESET_PASSWORD_URL

    return f"{base}?uid={uid}&token={token}"
