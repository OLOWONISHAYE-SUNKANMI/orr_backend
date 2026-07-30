import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from admin_portal.models import AuditLog

logger = logging.getLogger(__name__)

def _get_ip(request):
    """Extract IP from request headers if available."""
    if not request:
        return '0.0.0.0'
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login to the AuditLog."""
    try:
        ip_address = _get_ip(request)
        AuditLog.objects.create(
            action='login',
            model_name='User',
            object_id=str(user.pk),
            description=f"User {user.email} logged in from {ip_address}",
            user=user
        )
    except Exception as e:
        logger.error(f"Failed to log user login for {user.email}: {e}")

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout to the AuditLog."""
    try:
        if user:
            ip_address = _get_ip(request)
            AuditLog.objects.create(
                action='logout',
                model_name='User',
                object_id=str(user.pk),
                description=f"User {user.email} logged out from {ip_address}",
                user=user
            )
    except Exception as e:
        logger.error(f"Failed to log user logout: {e}")
