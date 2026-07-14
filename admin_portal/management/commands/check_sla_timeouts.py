import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from admin_portal.models import Ticket

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check for tickets that have breached SLA and send reminders to admin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='SLA breach threshold in hours'
        )

    def handle(self, *args, **options):
        from admin_portal.orr_email_service import ORREmailService

        hours = options['hours']
        threshold_time = timezone.now() - timedelta(hours=hours)

        # Get tickets that are not resolved and haven't been updated recently
        breaching_tickets = Ticket.objects.filter(
            status__in=['new', 'processing', 'payment_failed', 'payment_disputed', 'refund_requested'],
            updated_at__lt=threshold_time
        ).select_related('assigned_to')

        count = breaching_tickets.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No SLA breaches found.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {count} tickets breaching {hours}h SLA.'))

        for ticket in breaching_tickets:
            admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@orr.solutions')
            if ticket.assigned_to and ticket.assigned_to.email:
                admin_email = ticket.assigned_to.email

            if not admin_email:
                continue

            assigned_name = ticket.assigned_to.get_full_name() if ticket.assigned_to else 'Unassigned'
            admin_url = f"https://admin.orr.solutions/tickets/{ticket.id}"

            try:
                ORREmailService.send_action_required(
                    recipient_email=admin_email,
                    form_name=f"SLA Breach: Ticket {ticket.ticket_id}",
                    reference_id=ticket.ticket_id,
                    missing_info_detail=(
                        f"Ticket '{ticket.subject}' has not been updated in over {hours} hours.\n"
                        f"Current Status: {ticket.status}\n"
                        f"Assigned To: {assigned_name}\n"
                        f"Please review this ticket immediately."
                    ),
                    action_link=admin_url,
                )
                self.stdout.write(self.style.SUCCESS(f'Sent alert for ticket {ticket.ticket_id} to {admin_email}'))
            except Exception as e:
                logger.error(f"Failed to send SLA alert for ticket {ticket.ticket_id}: {e}")

        self.stdout.write(self.style.SUCCESS('SLA check completed.'))
