import logging
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class MessageEmailService:
    @staticmethod
    def send_admin_new_message_email(ticket, message):
        """
        Notify admin/support staff when a client sends a new message.
        Uses template 08-admin-notification.html
        """
        try:
            from .orr_email_service import ORREmailService

            # Determine recipients
            if ticket.assigned_to:
                recipients = [ticket.assigned_to.email]
            else:
                # Fallback to all admins if unassigned
                recipients = list(User.objects.filter(is_staff=True, is_active=True).values_list('email', flat=True))

            if not recipients:
                logger.warning(f"No recipients found for ticket {ticket.ticket_id}")
                return False

            client_name = ticket.client.user.get_full_name() if ticket.client else 'Unknown Client'
            client_email = ticket.client.user.email if ticket.client else ''
            admin_url = f"https://admin.orr.solutions/tickets/{ticket.id}"

            ORREmailService.send_admin_notification(
                recipient_emails=recipients,
                submitter_name=client_name,
                submitter_email=client_email,
                form_name=f"Support Ticket: {ticket.subject}",
                reference_id=ticket.ticket_id,
                admin_link=admin_url,
            )

            logger.info(f"Admin notification email sent for ticket {ticket.ticket_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send admin notification email: {e}")
            return False

    @staticmethod
    def send_client_admin_response_email(ticket, message):
        """
        Notify client when an admin responds to their ticket.
        Uses template 09-status-update.html
        """
        try:
            from .orr_email_service import ORREmailService

            client = ticket.client
            recipient = client.user.email

            if not recipient:
                logger.warning(f"No email for client {client.id}")
                return False

            ORREmailService.send_status_update(
                recipient_email=recipient,
                form_name=f"Support Ticket: {ticket.subject}",
                reference_id=ticket.ticket_id,
                current_status=ticket.get_status_display() if hasattr(ticket, 'get_status_display') else ticket.status,
                progress_percentage='—',
                tracking_link='https://orr.solutions/messages',
            )

            logger.info(f"Client notification email sent for ticket {ticket.ticket_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send client notification email: {e}")
            return False

    @staticmethod
    def send_escalation_email(ticket):
        """
        Send escalation email to support management.
        Uses template 10-action-required.html
        """
        try:
            from .orr_email_service import ORREmailService

            # For escalation, we send to all staff with management permissions
            recipients = list(User.objects.filter(
                is_staff=True, 
                is_active=True,
                admin_profile__role__can_manage_tickets=True
            ).values_list('email', flat=True))

            if not recipients:
                logger.warning(f"No escalation recipients found")
                return False

            admin_url = f"https://admin.orr.solutions/tickets/{ticket.id}"

            ORREmailService.send_action_required(
                recipient_email=recipients,
                form_name=f"⚠️ ESCALATION: Ticket {ticket.ticket_id}",
                reference_id=ticket.ticket_id,
                missing_info_detail=f"Ticket '{ticket.subject}' from {ticket.client.user.get_full_name()} has remained unanswered for over 4 hours and requires immediate attention.",
                action_link=admin_url,
            )

            logger.info(f"Escalated email sent for ticket {ticket.ticket_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send escalation email: {e}")
            return False
