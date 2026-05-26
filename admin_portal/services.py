"""
Admin Portal Services
Provides business logic and external integrations for the admin portal
"""

import logging
import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from googleapiclient.discovery import build
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


class NotificationService:
    """Handle email and in-app notifications"""

    @staticmethod
    def send_ticket_notification(
        ticket, notification_type: str, recipient: User
    ):
        """Send ticket-related notifications"""
        from .models import SystemNotification
        try:
            notif_type = "ticket_created"
            if notification_type == "assigned":
                notif_type = "ticket_assigned"
            elif notification_type == "replied":
                notif_type = "ticket_replied"
                
            # Create in-app notification
            SystemNotification.objects.create(
                notification_type=notif_type,
                title=f"Ticket {ticket.ticket_id} {notification_type}",
                message=f"Ticket: {ticket.subject}",
                recipient=recipient,
                related_ticket=ticket,
            )

            # Send email if enabled
            if (
                hasattr(settings, "EMAIL_NOTIFICATIONS_ENABLED")
                and settings.EMAIL_NOTIFICATIONS_ENABLED
            ):
                subject = (
                    f"ORR Admin - Ticket {ticket.ticket_id} {notification_type.title()}"
                )
                message = render_to_string(
                    "admin_portal/emails/ticket_notification.html",
                    {
                        "ticket": ticket,
                        "recipient": recipient,
                        "notification_type": notification_type,
                    },
                )

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    html_message=message,
                )

        except Exception as e:
            logger.error(f"Failed to send ticket notification: {e}")

    @staticmethod
    def send_meeting_notification(
        meeting, notification_type: str, recipient: User
    ):
        """Send meeting-related notifications"""
        from .models import SystemNotification
        try:
            # Create in-app notification
            SystemNotification.objects.create(
                notification_type="meeting_updated",
                title=f"Meeting {notification_type}",
                message=f"Meeting with {meeting.client.user.get_full_name()}",
                recipient=recipient,
                related_meeting=meeting,
            )

            # Send email if enabled
            if (
                hasattr(settings, "EMAIL_NOTIFICATIONS_ENABLED")
                and settings.EMAIL_NOTIFICATIONS_ENABLED
            ):
                subject = f"ORR Admin - Meeting {notification_type.title()}"
                message = render_to_string(
                    "admin_portal/emails/meeting_notification.html",
                    {
                        "meeting": meeting,
                        "recipient": recipient,
                        "notification_type": notification_type,
                    },
                )

                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient.email],
                    html_message=message,
                )

        except Exception as e:
            logger.error(f"Failed to send meeting notification: {e}")


class AnalyticsService:
    """Advanced analytics calculations"""

    @staticmethod
    def calculate_ticket_resolution_time() -> float:
        """Calculate average ticket resolution time in hours"""
        from django.db.models import Avg, F
        from .models import Ticket

        resolved_tickets = Ticket.objects.filter(
            status="resolved", updated_at__isnull=False
        ).annotate(resolution_time=F("updated_at") - F("created_at"))

        if resolved_tickets.exists():
            avg_seconds = resolved_tickets.aggregate(avg_time=Avg("resolution_time"))[
                "avg_time"
            ].total_seconds()
            return round(avg_seconds / 3600, 2)  # Convert to hours

        return 0.0

    @staticmethod
    def calculate_meeting_confirmation_time() -> float:
        """Calculate average meeting confirmation time in hours"""
        from django.db.models import Avg, F
        from .models import Meeting

        confirmed_meetings = Meeting.objects.filter(
            status__in=["confirmed", "completed"], confirmed_datetime__isnull=False
        ).annotate(confirmation_time=F("updated_at") - F("created_at"))

        if confirmed_meetings.exists():
            avg_seconds = confirmed_meetings.aggregate(
                avg_time=Avg("confirmation_time")
            )["avg_time"].total_seconds()
            return round(avg_seconds / 3600, 2)  # Convert to hours

        return 0.0

    @staticmethod
    def get_client_activity_trends(days: int = 30) -> Dict:
        """Get client activity trends over specified days"""
        from .models import Client, AuditLog
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Daily login counts
        daily_logins = []
        for i in range(days):
            date = (end_date - timedelta(days=i)).date()
            count = Client.objects.filter(user__last_login__date=date).count()
            daily_logins.append({"date": date.isoformat(), "count": count})

        # Stage progression
        stage_changes = AuditLog.objects.filter(
            model_name="Client",
            action="update",
            description__icontains="stage",
            timestamp__gte=start_date,
        ).count()

        return {
            "daily_logins": daily_logins,
            "stage_changes": stage_changes,
            "period_days": days,
        }


class CalendarService:
    """Calendar integration service using Google Meet API"""

    @staticmethod
    def _get_calendar_service():
        """Initialize Google Calendar API service from file path or JSON string with cascades"""
        
        # 1. Try to get credentials from direct JSON string (useful for Cloud Run/Heroku)
        json_info = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if json_info:
            try:
                info = json.loads(json_info)
                creds = service_account.Credentials.from_service_account_info(
                    info, scopes=['https://www.googleapis.com/auth/calendar']
                )
                return build('calendar', 'v3', credentials=creds)
            except Exception as e:
                logger.error(f"Failed to initialize Calendar service from GOOGLE_CREDENTIALS_JSON: {e}")

        # 2. Try to get credentials from file path
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        
        # 3. Fallback to local file if no environment variables are set
        if not json_info and not creds_path:
            local_path = os.path.join(settings.BASE_DIR, 'google_credentials', 'google-calendar-credentials.json')
            if not os.path.exists(local_path):
                local_path = os.path.join(settings.BASE_DIR, "google-meet-credentials.json")
            if os.path.exists(local_path):
                creds_path = local_path

        # Helper helper to build calendar service
        def try_build_cal(c):
            try:
                return build('calendar', 'v3', credentials=c)
            except Exception as build_err:
                logger.error(f"Failed to build Calendar client from credentials: {build_err}")
                return None

        if creds_path and os.path.exists(creds_path):
            try:
                creds = service_account.Credentials.from_service_account_file(
                    creds_path, scopes=['https://www.googleapis.com/auth/calendar']
                )
                service = try_build_cal(creds)
                if service:
                    return service
            except Exception as e:
                logger.error(f"Failed to initialize Calendar service from file {creds_path}: {e}")

        # 4. Fallback to uncorrupted key files in google_credentials directory
        base_credentials_path = os.path.join(settings.BASE_DIR, 'google_credentials')
        fallback_files = [
            'google-docs-credentials.json',
            'google-meet-credentials.json',
            'google-email-credentials.json'
        ]
        for fname in fallback_files:
            fallback_path = os.path.join(base_credentials_path, fname)
            if os.path.exists(fallback_path):
                try:
                    creds = service_account.Credentials.from_service_account_file(
                        fallback_path, scopes=['https://www.googleapis.com/auth/calendar']
                    )
                    service = try_build_cal(creds)
                    if service:
                        logger.info(f"CalendarService self-healed using fallback key: {fname}")
                        return service
                except Exception as fallback_err:
                    logger.error(f"Failed loading fallback calendar credentials from {fname}: {fallback_err}")

        # 5. Final fallback: Use Application Default Credentials (ADC)
        try:
            import google.auth
            creds, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/calendar'])
            service = try_build_cal(creds)
            if service:
                return service
        except Exception as adc_err:
            logger.error(f"ADC fallback failed for Calendar: {adc_err}")

        return None

    @staticmethod
    def create_calendar_event(meeting) -> Optional[str]:
        """Create calendar event for meeting and generate Google Meet link"""
        import uuid
        uid = uuid.uuid4().hex
        fallback_link = f"https://meet.google.com/orr-{uid[:3]}-{uid[3:7]}-{uid[7:10]}"
        
        service = CalendarService._get_calendar_service()
        if not service:
            # Fallback to mock ID and fallback link if integration is disabled
            meeting.meeting_link = fallback_link
            meeting.save()
            return f"mock_meeting_{meeting.id}_{int(timezone.now().timestamp())}"
            
        try:
            conference_data = {
                'createRequest': {
                    'requestId': str(uuid.uuid4()),
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
            
            # Use requested_datetime as start time
            start_time = meeting.requested_datetime
            if meeting.status == 'confirmed' and meeting.confirmed_datetime:
                start_time = meeting.confirmed_datetime
                
            end_time = start_time + timedelta(minutes=meeting.duration_minutes)
            
            event = {
                'summary': f"ORR Consultation: {meeting.client.user.get_full_name()}",
                'description': f"Agenda: {meeting.agenda}\n\nMeeting requested via ORR Solutions Portal.",
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'conferenceData': conference_data,
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 30},
                    ],
                },
            }

            # Determine which calendar to insert the event into
            admin_email = os.environ.get("GOOGLE_CALENDAR_ID")
            if not admin_email:
                admin_email = getattr(settings, "DEFAULT_FROM_EMAIL", "admin@orr.solutions")
            
            if "localhost" in admin_email or not admin_email:
                admin_email = "primary"

            created_event = service.events().insert(
                calendarId=admin_email, 
                body=event, 
                conferenceDataVersion=1
            ).execute()
            
            # Save meeting link and ID
            meeting.meeting_link = created_event.get('hangoutLink') or fallback_link
            meeting.calendar_event_id = created_event.get('id')
            meeting.save()
            
            logger.info(f"Google Meet event created for meeting {meeting.id}: {meeting.calendar_event_id}")
            return meeting.calendar_event_id

        except Exception as e:
            logger.error(f"Google Calendar integration error: {e}")
            meeting.meeting_link = fallback_link
            meeting.calendar_event_id = f"fallback_meeting_{meeting.id}_{int(timezone.now().timestamp())}"
            meeting.save()
            return meeting.calendar_event_id

    @staticmethod
    def update_calendar_event(meeting, event_id: str) -> bool:
        """Update existing calendar event"""
        service = CalendarService._get_calendar_service()
        if not service or not event_id or event_id.startswith("mock_"):
            return False
            
        try:
            start_time = meeting.confirmed_datetime or meeting.requested_datetime
            end_time = start_time + timedelta(minutes=meeting.duration_minutes)
            
            event = service.events().get(calendarId='primary', eventId=event_id).execute()
            
            event['start']['dateTime'] = start_time.isoformat()
            event['end']['dateTime'] = end_time.isoformat()
            event['description'] = f"Agenda: {meeting.agenda}\n\nStatus: {meeting.status}"
            
            service.events().update(
                calendarId='primary', 
                eventId=event_id, 
                body=event,
                sendUpdates='all'
            ).execute()
            
            return True

        except Exception as e:
            logger.error(f"Failed to update Google Calendar event: {e}")
            return False

    @staticmethod
    def delete_calendar_event(event_id: str) -> bool:
        """Delete calendar event"""
        service = CalendarService._get_calendar_service()
        if not service or not event_id or event_id.startswith("mock_"):
            return False
            
        try:
            service.events().delete(calendarId='primary', eventId=event_id, sendUpdates='all').execute()
            return True

        except Exception as e:
            logger.error(f"Failed to delete Google Calendar event: {e}")
            return False


class SystemHealthService:
    """Monitor system health and performance"""

    @staticmethod
    def get_system_health() -> Dict:
        """Get current system health metrics"""
        try:
            # Database health
            db_health = SystemHealthService._check_database_health()

            # Recent errors
            recent_errors = SystemHealthService._get_recent_errors()

            # Performance metrics
            performance = SystemHealthService._get_performance_metrics()

            return {
                "status": "healthy" if db_health["status"] == "ok" else "warning",
                "database": db_health,
                "recent_errors": recent_errors,
                "performance": performance,
                "last_check": timezone.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "last_check": timezone.now().isoformat(),
            }

    @staticmethod
    def _check_database_health() -> Dict:
        """Check database connectivity and basic metrics"""
        from .models import Client, Ticket
        try:
            # Test database connection
            total_clients = Client.objects.count()
            total_tickets = Ticket.objects.count()

            return {
                "status": "ok",
                "total_clients": total_clients,
                "total_tickets": total_tickets,
                "connection": "healthy",
            }

        except Exception as e:
            return {"status": "error", "error": str(e), "connection": "failed"}

    @staticmethod
    def _get_recent_errors(hours: int = 24) -> List[Dict]:
        """Get recent system errors from logs"""
        # In a real implementation, this would read from log files or error tracking service
        return []

    @staticmethod
    def _get_performance_metrics() -> Dict:
        """Get basic performance metrics"""
        # Placeholder for performance monitoring
        return {
            "response_time_avg": 150,  # ms
            "memory_usage": 65,  # percentage
            "cpu_usage": 45,  # percentage
        }


class ContentService:
    """Content management business logic"""

    @staticmethod
    def publish_content(content, user: User) -> bool:
        """Publish content with proper validation and logging"""
        from .models import AuditLog
        try:
            if content.status == "published":
                return False

            content.status = "published"
            content.published_at = timezone.now()
            content.save()

            # Create audit log
            AuditLog.objects.create(
                user=user,
                action="publish",
                model_name="Content",
                object_id=str(content.id),
                description=f"Published content: {content.title}",
            )

            return True

        except Exception as e:
            logger.error(f"Failed to publish content {content.id}: {e}")
            return False

    @staticmethod
    def archive_content(content, user: User) -> bool:
        """Archive content with proper logging"""
        from .models import AuditLog
        try:
            content.status = "archived"
            content.save()

            # Create audit log
            AuditLog.objects.create(
                user=user,
                action="archive",
                model_name="Content",
                object_id=str(content.id),
                description=f"Archived content: {content.title}",
            )

            return True

        except Exception as e:
            logger.error(f"Failed to archive content {content.id}: {e}")
            return False
