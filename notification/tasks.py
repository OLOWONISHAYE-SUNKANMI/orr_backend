import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(max_retries=3, default_retry_delay=10)
def send_email_task(subject, recipient_email, template_name, context):
    """
    Send email using Django SMTP.
    """
    html_content = render_to_string(template_name, context)

    try:
        send_via_smtp(subject, recipient_email, html_content)
        logger.info(f"[SMTP] Email sent → {recipient_email}")
        return True

    except Exception as smtp_error:
        logger.error(f"[SMTP] Failed → {smtp_error}")
        raise smtp_error  


# -------------------------------------------------------------------------
# System Alert Tasks
# -------------------------------------------------------------------------

@shared_task
def send_system_error_alert_task(error_code, error_message, admin_email="admin@orr.solutions"):
    from admin_portal.orr_email_service import ORREmailService
    try:
        ORREmailService.send_system_error(
            recipient_email=admin_email,
            error_code=error_code,
            error_message=error_message,
            system_status_url="https://orr.solutions/admin/system"
        )
    except Exception as e:
        logger.error(f"Failed to send system error alert: {e}")

@shared_task
def send_security_alert_task(user_email, activity_type, location, ip_address):
    from admin_portal.orr_email_service import ORREmailService
    try:
        ORREmailService.send_security_alert(
            recipient_email=user_email,
            activity_type=activity_type,
            location=location,
            ip_address=ip_address,
            secure_account_url="https://orr.solutions/security"
        )
    except Exception as e:
        logger.error(f"Failed to send security alert: {e}")

# -------------------------------------------------------------------------
# Marketing and Newsletter Tasks
# -------------------------------------------------------------------------

@shared_task
def send_marketing_newsletter_task(user_email, month_year, highlights):
    from admin_portal.orr_email_service import ORREmailService
    try:
        ORREmailService.send_newsletter(
            recipient_email=user_email,
            month_year=month_year,
            highlights=highlights,
            newsletter_url="https://orr.solutions/newsletter"
        )
    except Exception as e:
        logger.error(f"Failed to send newsletter: {e}")

@shared_task
def send_reengagement_emails():
    """Periodic task to send re-engagement emails to users inactive for > 30 days"""
    from datetime import timedelta
    from django.utils import timezone
    from django.contrib.auth.models import User
    from admin_portal.orr_email_service import ORREmailService
    
    # Find users who haven't logged in for exactly 30 days
    # (Using exactly 30 days so they don't get spammed every day after day 30)
    target_date_start = timezone.now() - timedelta(days=31)
    target_date_end = timezone.now() - timedelta(days=30)
    
    inactive_users = User.objects.filter(
        is_active=True,
        last_login__gte=target_date_start,
        last_login__lte=target_date_end
    ).exclude(email="")
    
    for user in inactive_users:
        try:
            ORREmailService.send_reengagement(
                recipient_email=user.email,
                user_name=user.get_full_name() or user.username,
                recent_updates="We've launched new features and performance improvements.",
                login_url="https://orr.solutions/login"
            )
        except Exception as e:
            logger.error(f"Failed to send re-engagement email to {user.email}: {e}")


def send_via_smtp(subject, recipient_email, html_content):
    """SMTP sending using Django EmailBackend"""
    msg = EmailMultiAlternatives(
        subject=subject,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
    return True


class EmailService:
    """Public interface"""
    def __init__(self, default_sender=None):
        self.default_sender = default_sender or settings.DEFAULT_FROM_EMAIL

    def send_email(self, subject, recipient_email, template_name, context):
        context["from_email"] = self.default_sender

        try:
            send_email_task.delay(subject, recipient_email, template_name, context)
            logger.info(f"[EmailService] Queued → {recipient_email}")
        except Exception as e:
            logger.warning(f"[EmailService] Celery/Redis failed, falling back to synchronous email for {recipient_email}. Error: {e}")
            try:
                # Call task synchronously as fallback
                send_email_task(subject, recipient_email, template_name, context)
                logger.info(f"[EmailService] Sent synchronously → {recipient_email}")
            except Exception as inner_e:
                logger.error(f"[EmailService] Synchronous fallback failed for {recipient_email}. Error: {inner_e}")

        return True
