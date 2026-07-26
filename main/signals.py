import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from admin_portal.models import AdminProfile

from .models import ContactMessage
from .tasks import send_contact_notification_email

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ContactMessage)
def notify_admin_on_new_contact_message(sender, instance, created, **kwargs):
    """
    When a new ContactMessage is created → send email to all admins
    """
    if not created:
        logger.debug("ContactMessage updated, not created — no admin notification.")
        return

    logger.info(
        f"New ContactMessage created (ID={instance.id}). Preparing admin notifications..."
    )
    print( f"New ContactMessage created (ID={instance.id}). Preparing admin notifications...")

    admin_profiles = AdminProfile.objects.exclude(role__name="content_editor")

    admin_emails = [
        profile.user.email for profile in admin_profiles if profile.user.email
    ]

    if not admin_emails:
        logger.warning(
            "No admin emails found (excluding content editors) — skipping notifications."
        )
        return

    logger.info(f"Resolved admin emails (excluding content editors): {admin_emails}")

    subject = f"New Contact Form Submission: {instance.subject}"

    context = {
        "message": {
            "first_name": instance.first_name,
            "email": instance.email,
            "subject": instance.subject,
            "message": instance.message,
            "phone": instance.phone,
            "created_at": instance.created_at.isoformat(),
        },
        "site_name": "ORR",
    }

    for admin_email in admin_emails:
        logger.info(f"Queueing Celery task for {admin_email}")
        try:
            send_contact_notification_email.delay(subject, admin_email, context)
        except Exception as e:
            logger.warning(f"Celery/Redis failed for contact notification to {admin_email}. Falling back to synchronous. Error: {e}")
            try:
                # Call task synchronously as fallback
                send_contact_notification_email(subject, admin_email, context)
            except Exception as inner_e:
                logger.error(f"Synchronous fallback failed for {admin_email}. Error: {inner_e}")
