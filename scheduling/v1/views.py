import logging
from calendar import monthrange
from datetime import date, datetime, timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
import requests
from client.models import Activity
from services.meetings.calendly import CalendlyAPI
from common.permissions import HasActivePaidSubscription

from .serializers import (
    MeetingCalendarSerializer,
    MeetingPrepSerializer,
    MeetingRequestSerializer,
    MeetingSerializer,
    MeetingStatusChangeSerializer,
    CalendlyWebhookSerializer,
)

logger = logging.getLogger(__name__)
from admin_portal.models import Client, Meeting






@extend_schema(tags=["scheduling"])
class UpdateMeetingPrepView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingPrepSerializer

    def patch(self, request, pk):
        user = request.user
        client = Client.objects.get(user=user)
        meeting_request = get_object_or_404(Meeting, pk=pk, client=client)

        serializer = MeetingPrepSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        meeting_request.basic_context = data["basic_context"]
        meeting_request.goals = data["goals"]
        meeting_request.pain_points = data["pain_points"]
        meeting_request.save()

        Activity.objects.create(
            user=request.user,
            activity_type="Meeting Activity",
            title="Completed first meeting preparation",
            message="User submitted their meeting preparation details.",
            metadata={"meeting_request_id": meeting_request.id},
        )

        return Response({"message": "Meeting preparation updated successfully."})


@extend_schema(tags=["scheduling"])
class EventTypesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            calendly = CalendlyAPI()
            event_types = calendly.get_event_types()
            if not event_types or "collection" not in event_types:
                return Response([])
                
            data = [
                {"name": et["name"], "uri": et["uri"]} for et in event_types["collection"]
            ]
            return Response({"data": data})
        except Exception as e:
            logger.warning(f"Calendly event types fetch failed: {e}")
            # Return a dummy event type to allow the Google Meet flow to proceed
            return Response({"data": [{"name": "Google Meet Consultation", "uri": "https://meet.google.com/google-meet"}]})


@extend_schema(
    tags=["scheduling"],
    parameters=[
        OpenApiParameter(
            name="event_type_uri",
            type=str,
            required=True,
            description="Full Calendly event_type URL (e.g., https://api.calendly.com/event_types/XXXX)",
        ),
        OpenApiParameter(
            name="start_date",
            type=str,
            required=False,
            description="Filter slots starting from this date (format: YYYY-MM-DD)",
        ),
    ],
)
class AvailableSlotsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        meeting_type_uri = request.query_params.get("event_type_uri")
        if not meeting_type_uri:
            return Response({"message": "Missing event_type_uri"}, status=400)
        now = datetime.now()
        start = datetime.now() + timedelta(hours=1)
        end = start + timedelta(days=7)

        date_str = request.query_params.get("start_date")
        if date_str:
            try:
                selected_date = datetime.strptime(date_str, "%Y-%m-%d")


                if selected_date.date() < now.date():
                    return Response({"message": "Date cannot be in the past"}, status=400)

                start = selected_date
                if start.date() == now.date():
                    min_start = now + timedelta(hours=1)
                    if start < min_start:
                        start = min_start

                end = start + timedelta(days=1)
            except ValueError:
                return Response(
                    {"message": "Invalid date format, use YYYY-MM-DD"}, status=400
                )
            else:
                start = start
                end = end
        
        # Manual slot generation (9 AM to 5 PM) instead of Calendly
        slots = []
        base_date = start.replace(minute=0, second=0, microsecond=0)
        
        for hour in range(9, 18):  # 9 AM to 6 PM
            slot_time = base_date.replace(hour=hour)
            if slot_time > now:
                slots.append({
                    "start_time": slot_time.isoformat(),
                    "status": "available"
                })
        
        return Response({"data": {"collection": slots}})


@extend_schema(tags=["scheduling"])
class CreateMeetingView(APIView):
    permission_classes = [IsAuthenticated,  HasActivePaidSubscription,]
    serializer_class = MeetingRequestSerializer

    def post(self, request):
        from admin_portal.services import CalendarService
        user = request.user
        client = Client.objects.get(user=user)

        serializer = MeetingRequestSerializer(
            data=request.data, context={"client": client}
        )
        serializer.is_valid(raise_exception=True)
        meeting = serializer.save()

        # Generate a REAL Google Meet link immediately
        try:
            event_id = CalendarService.create_calendar_event(meeting)
            if event_id:
                # Refresh meeting from DB to get the newly generated link
                meeting.refresh_from_db()
                logger.info(f"Generated live Google Meet link for meeting {meeting.id}: {meeting.meeting_link}")
            else:
                meeting.meeting_link = "pending-google-workspace"
                meeting.save()
        except Exception as e:
            logger.error(f"Failed to generate instant Google Meet link: {e}")
            meeting.meeting_link = "pending-google-workspace"
            meeting.save()

        # Send confirmation notification to client & admins/host
        try:
            from admin_portal.services import NotificationService
            NotificationService.send_meeting_notification(meeting, "confirmed", meeting.client.user)
        except Exception as e:
            logger.warning(f"Failed to send meeting confirmation notification: {e}")

        return Response(
            {
                "success": True,
                "message": "Meeting created and Google Meet link generated.",
                "meeting_id": meeting.id,
                "redirect_url": meeting.meeting_link,
            }
        )


@extend_schema(
    tags=["scheduling"],
)
class MeetingChangeStatusView(APIView):
    """
    Endpoint to change the status of a meeting.
    POST /api/meetings/<pk>/change-status/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = MeetingStatusChangeSerializer

    def post(self, request, pk):
        meeting = get_object_or_404(Meeting, pk=pk)
        new_status = request.data.get("status")
        user = request.user
        client = Client.objects.get(user=user)
        if meeting.client != client:
            raise PermissionDenied("You are not allowed to modify this meeting.")
        if new_status not in dict(Meeting.STATUS_CHOICES):
            return Response(
                {"error": "Invalid status", "allowed": dict(Meeting.STATUS_CHOICES)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = meeting.status
        meeting.status = new_status

        calendly = CalendlyAPI()

        try:
            if new_status == "cancelled" and meeting.calendar_event_id:
                calendly.cancel_event(
                    meeting.calendar_event_id,
                    reason=f"Status changed to {new_status} via portal",
                )

            elif new_status == "rescheduled" and meeting.calendar_event_id:
                pass
            elif new_status == "confirmed" and old_status == "requested":
                if not meeting.calendar_event_id:
                    calendly_data = calendly.schedule_event(meeting)
                    meeting.calendar_event_id = calendly_data["event_uuid"]
                    meeting.meeting_link = calendly_data["invite_link"]
                    meeting.confirmed_datetime = meeting.requested_datetime

        except Exception as e:
            meeting.internal_notes += (
                f"\n[Auto] Calendly sync warning ({new_status}): {str(e)}"
            )
            logger.warning(f"Calendly sync failed for meeting {meeting.id}: {e}")

        meeting.save()
        valid_statuses = dict(Meeting.STATUS_CHOICES)

        old_status_display = valid_statuses[old_status]
        new_status_display = valid_statuses[new_status]
        return Response(
            {
                "id": meeting.id,
                "status": new_status,
                "status_display": new_status_display,
                "message": f"Status changed from {old_status_display} → {new_status_display}",
            },
        )


@extend_schema(
    tags=["scheduling"],
)
class MeetingHostJoinedView(APIView):
    """
    Endpoint for when the host joins a meeting.
    POST /api/scheduling/meetings/<pk>/host-joined/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        meeting = get_object_or_404(Meeting, pk=pk)
        
        # Only allow hosts or superadmins to trigger this
        if request.user != meeting.host and not request.user.is_superuser:
            raise PermissionDenied("Only the meeting host or admin can trigger this.")
            
        try:
            from admin_portal.orr_email_service import ORREmailService
            if meeting.client and meeting.client.user.email:
                ORREmailService.send_host_joined(
                    recipient_email=meeting.client.user.email,
                    meeting_subject=f"{meeting.get_meeting_type_display()} with ORR Solutions",
                    meeting_link=meeting.meeting_link or "Link will be provided",
                )
                logger.info(f"Host joined notification sent for meeting {meeting.id}")
                
            return Response({"success": True, "message": "Client notified that host joined."})
        except Exception as e:
            logger.error(f"Failed to send host joined notification: {e}")
            return Response({"error": "Failed to send notification"}, status=500)

@extend_schema(
    tags=["scheduling"],
    description="Get all meetings created by the authenticated client.",
    responses=MeetingSerializer(many=True),
)
class MyMeetingsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingSerializer
    def get(self, request):
        user = request.user
        client = Client.objects.get(user=user)
        meetings = Meeting.objects.filter(client=client).order_by("-id")
        serializer = MeetingSerializer(meetings, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=["scheduling"],
    description="Get details for a specific meeting.",
    responses=MeetingSerializer(),
)
class MeetingDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingSerializer

    def get(self, request, pk):
        from admin_portal.services import CalendarService
        user = request.user
        client = Client.objects.get(user=user)
        meeting = get_object_or_404(Meeting, pk=pk, client=client)

        # AUTO-FIX: Generate a real link if it's currently dummy or missing
        is_dummy = meeting.meeting_link and "google-meet" in meeting.meeting_link
        if not meeting.calendar_event_id or is_dummy or meeting.meeting_link in ["", None]:
            try:
                CalendarService.create_calendar_event(meeting)
                meeting.refresh_from_db()
            except Exception as e:
                logger.error(f"Failed to auto-generate link for meeting {pk}: {e}")

        serializer = MeetingSerializer(meeting)
        return Response(serializer.data)


@extend_schema(
    tags=["scheduling"],
    parameters=[
        OpenApiParameter(
            name="month",
            type=int,
            required=True,
            location=OpenApiParameter.QUERY,
            description="Month number (1-12)",
        ),
        OpenApiParameter(
            name="year",
            type=int,
            required=True,
            location=OpenApiParameter.QUERY,
            description="4-digit year, e.g. 2025",
        ),
    ],
    summary="Get monthly calendar overview",
    description="Returns all meetings for the selected month formatted for a calendar UI",
)
class CalendarView(APIView):
    def get(self, request):
        month = int(request.query_params.get("month"))
        year = int(request.query_params.get("year"))

        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        meetings = Meeting.objects.filter(
            confirmed_datetime__date__gte=start_date,
            confirmed_datetime__date__lte=end_date,
        )

        sidebar_events = MeetingCalendarSerializer(meetings, many=True).data

        calendar_days = []
        for day in range(1, last_day + 1):
            d = date(year, month, day)
            day_meetings = meetings.filter(confirmed_datetime__date=d)

            calendar_days.append(
                {
                    "date": str(d),
                    "events": [
                        {"id": m.id, "title": m.title, "color": m.color}
                        for m in day_meetings
                    ],
                }
            )

        return Response(
            {
                "month": start_date.strftime("%B %Y"),
                "sidebar_events": sidebar_events,
                "calendar_days": calendar_days,
            }
        )


@extend_schema(tags=["scheduling"])
class CalendlyWebhookView(APIView):
    """
    Webhook to handle Calendly events: booking confirmed, canceled, rescheduled.
    Automatically updates local Meeting instances.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Expected payload from Calendly:
        {
            "event": "invitee.created" | "invitee.canceled" | "invitee.rescheduled",
            "payload": {...}
        }
        """
        data = request.data
        if data.get("event") == "ping" or data == {}:
            return Response({"status": "ok"}, status=200)

        event_type = request.data.get("event")
        payload = request.data.get("payload")

        if not event_type or not payload:
            return Response({"message": "Invalid webhook payload"}, status=400)

        try:
            if event_type == "invitee.created":
                self.handle_created(payload)
            elif event_type == "invitee.canceled":
                self.handle_canceled(payload)
            elif event_type == "invitee.rescheduled":
                self.handle_rescheduled(payload)
            else:
                return Response(
                    {"message": f"Unhandled event type: {event_type}"}, status=200
                )
        except Exception as e:
            return Response(
                {"message": f"Error processing webhook: {str(e)}"}, status=500
            )

        return Response({"success": True})

    def handle_created(self, payload):
        """
        Booking confirmed in Calendly.
        Update local meeting to confirmed.
        """
        calendly_event_id = payload.get("event", {}).get("uri")
        meeting_link = payload.get("event", {}).get("location", {}).get("join_url")
        start_time_str = payload.get("event", {}).get("start_time")
        end_str = payload.get("event", {}).get("end_time")
        start_time = parse_datetime(start_time_str) if start_time_str else None
        end_time = parse_datetime(end_str) if end_str else None

        meeting = Meeting.objects.filter(meeting_link=meeting_link).first()

        if meeting:
            meeting.status = "confirmed"
            meeting.end_datetime = end_time
            meeting.confirmed_datetime = start_time
            meeting.calendar_event_id = calendly_event_id
            meeting.save()
            from ..tasks import charge_for_meeting
            charge_for_meeting.delay(meeting.id)

    def handle_canceled(self, payload):
        """
        Meeting canceled in Calendly.
        """
        calendly_event_id = payload.get("event", {}).get("uri")
        meeting = Meeting.objects.filter(calendar_event_id=calendly_event_id).first()
        if meeting:
            meeting.status = "cancelled"
            meeting.save()

    def handle_rescheduled(self, payload):
        """
        Meeting rescheduled in Calendly.
        """
        calendly_event_id = payload.get("event", {}).get("uri")
        start_time_str = payload.get("event", {}).get("start_time")
        start_time = parse_datetime(start_time_str) if start_time_str else None

        meeting = Meeting.objects.filter(calendar_event_id=calendly_event_id).first()
        if meeting and start_time:
            meeting.status = "rescheduled"
            meeting.confirmed_datetime = start_time
            meeting.save()










class CreateCalendlyWebhook(APIView):
    serializer_class = CalendlyWebhookSerializer

    def post(self, request):
        serializer = CalendlyWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data


        webhook_url = data["webhook_url"]
        events = data["events"]
        scope = data["scope"]

        try:
            org_response = requests.get(
                "https://api.calendly.com/users/me",
                headers={"Authorization": f"Bearer {settings.CALENDLY_API_KEY}"},
                timeout=10
            )
            org_response.raise_for_status()
            organization_uri = org_response.json()["resource"]["current_organization"]
            
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch organization URI: {str(e)}"},
                status=400
            )
        try:
            user_response = requests.get(
                "https://api.calendly.com/users/me",
                headers={"Authorization": f"Bearer {settings.CALENDLY_API_KEY}"},
                timeout=10
            )
            user_response.raise_for_status()
            user_data = user_response.json()["resource"]
            user_role = user_data.get("role")

            user_uri = user_data["uri"]

        except Exception as e:
            return Response(
                {"error": f"Failed to fetch user: {str(e)}"},
                status=400
            )

      
        payload = {
            "url": webhook_url,
            "events": events,
            "scope": scope,
            "organization": organization_uri,
            "user": user_uri
        }

      
        try:
            response = requests.post(
                "https://api.calendly.com/webhook_subscriptions",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.CALENDLY_API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return Response(
                {"error": f"Failed to create webhook: {str(e)}"},
                status=400
            )
            
        return Response({"webhook": response.json()}, status=201)