import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_contact_notification_email(self, subject, recipient, context):
    """
    Task to send admin notification emails asynchronously.
    Uses branded ORR templates: 08-admin-notification + 07-form-confirmation
    """
    try:
        from admin_portal.orr_email_service import ORREmailService

        logger.info(f"[ContactTask] Sending contact notification to {recipient}")

        # Send notification to admin (template 08)
        ORREmailService.send_admin_notification(
            recipient_emails=[recipient],
            submitter_name=context.get('name', 'Unknown'),
            submitter_email=context.get('email', ''),
            form_name='Contact Form',
            reference_id=f"CONTACT-{self.request.id[:8] if self.request.id else 'N/A'}",
            admin_link='https://admin.orr.solutions/messages',
        )

        # Send confirmation to the contact form submitter (template 07)
        sender_email = context.get('email')
        if sender_email:
            ORREmailService.send_form_confirmation(
                recipient_email=sender_email,
                form_name='Contact Form',
                reference_id=f"CONTACT-{self.request.id[:8] if self.request.id else 'N/A'}",
                submission_date=context.get('date', ''),
                summary_text=context.get('message', ''),
                tracking_link='https://orr.solutions',
            )

        return True

    except Exception as e:
        logger.error(f"[ContactTask] FAILED for {recipient}: {e}")
        return False

