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

        send_email_task.delay(subject, recipient_email, template_name, context)
        logger.info(f"[EmailService] Queued → {recipient_email}")

        return True
