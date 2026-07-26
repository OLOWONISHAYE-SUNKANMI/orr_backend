import logging

from ..tasks import send_email_task
from .base_channel import BaseChannel

logger = logging.getLogger(__name__)


class EmailChannel(BaseChannel):
    """Email channel that delegates to the existing EmailService."""

    def send(self, user, title, message, metadata=None):
        if not user.email:
            logger.warning(f"Skipping email: user {user.id} has no email.")
            return

        metadata = metadata or {}

        template_name = metadata.get("template")
        if not template_name:
            logger.error(
                f"Email sending failed: No template provided for user={user.id}, title='{title}'"
            )
            return

        try:
            context = metadata.get("context", {"user": user, "message": message})
        except Exception as e:
            logger.error(f"Failed to extract context for email to user={user.id}: {e}")
            return

        try:
            send_email_task.delay(
                subject=title,
                recipient_email=user.email,
                template_name=template_name,
                context=context,
            )
            logger.info(
                f"Email queued successfully to {user.email} using template '{template_name}'"
            )
        except Exception as e:
            logger.warning(
                f"Celery/Redis failed for {user.email}, falling back to synchronous email sending. Error: {e}"
            )
            try:
                # Call task synchronously as fallback
                send_email_task(
                    subject=title,
                    recipient_email=user.email,
                    template_name=template_name,
                    context=context,
                )
                logger.info(
                    f"Email sent successfully (fallback) to {user.email} using template '{template_name}'"
                )
            except Exception as inner_e:
                logger.exception(
                    f"Email sending failed for user={user.id}, email={user.email}. Error: {inner_e}"
                )
