from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import Meeting
from admin_portal.permissions import CanManageMeetings
# Import services with error handling
try:
    from admin_portal.services import CalendarService, NotificationService
except ImportError:
    # Create dummy services if not available
    class CalendarService:
        @staticmethod
        def create_calendar_event(meeting):
            return None
    
    class NotificationService:
        @staticmethod
        def send_meeting_notification(meeting, action, user):
            pass

from ..serializers.meeting import (
    MeetingActionSerializer,
    MeetingCreateSerializer,
    MeetingDetailSerializer,
    MeetingListSerializer,
    MeetingStatsSerializer,
    MeetingUpdateSerializer,
)


@extend_schema(
    tags=["Meeting Management"],
    summary="List or create meeting requests",
    description="Retrieve a filtered list of meeting requests with options to filter by status, type, host, date range, and upcoming meetings. Also supports creating new meeting requests.",
)
class MeetingListView(generics.ListCreateAPIView):
    """List and create meeting requests"""

    permission_classes = [CanManageMeetings]
    
    def get_serializer_class(self):
        if self.request.method == "POST":
            return MeetingCreateSerializer
        return MeetingListSerializer

    def get_queryset(self):
        queryset = Meeting.objects.select_related("client__user", "host").all()
        
        try:
            user_role = self.request.user.admin_profile.role
            if user_role and user_role.name != "super_admin" and not user_role.can_view_all_clients:
                queryset = queryset.filter(client__assigned_admin=self.request.user)
        except AttributeError:
            pass
        
        # Debug: Log total meetings count
        print(f"Total meetings in database: {queryset.count()}")

        # Search functionality
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(client__user__first_name__icontains=search)
                | Q(client__user__last_name__icontains=search)
                | Q(client__company__icontains=search)
                | Q(agenda__icontains=search)
            )

        # Filters
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            print(f"Filtering by status: {status_filter}")
            queryset = queryset.filter(status=status_filter)
            print(f"Meetings after status filter: {queryset.count()}")

        meeting_type = self.request.query_params.get("type", None)
        if meeting_type:
            queryset = queryset.filter(meeting_type=meeting_type)

        host = self.request.query_params.get("host", None)
        host_id = self.request.query_params.get("host_id", None)
        if host:
            if host == "unassigned":
                queryset = queryset.filter(host__isnull=True)
            else:
                queryset = queryset.filter(host_id=host)
        elif host_id:
            queryset = queryset.filter(host_id=host_id)

        # Date range filters
        date_from = self.request.query_params.get("date_from", None)
        date_to = self.request.query_params.get("date_to", None)
        if date_from:
            queryset = queryset.filter(requested_datetime__gte=date_from)
        if date_to:
            queryset = queryset.filter(requested_datetime__lte=date_to)

        # Upcoming meetings filter
        upcoming = self.request.query_params.get("upcoming", None)
        if upcoming == "true":
            queryset = queryset.filter(
                confirmed_datetime__gte=timezone.now(), status="confirmed"
            )

        final_queryset = queryset.order_by("-created_at")
        print(f"Final queryset count: {final_queryset.count()}")
        return final_queryset
        
    def perform_create(self, serializer):
        """Create a new meeting request"""
        from admin_portal.models import Client
        
        # Find client by ID
        client_id = serializer.validated_data.get('client_id')
        try:
            client = Client.objects.get(id=client_id)
            
            # Save meeting with all provided data
            meeting = serializer.save(
                client=client, 
                status='requested',
                host=self.request.user if hasattr(self.request, 'user') else None
            )
            
        except Client.DoesNotExist:
            raise serializers.ValidationError({"client_id": "Client with this ID not found"})
            
        # Send notification to client
        try:
            from admin_portal.services import NotificationService
            NotificationService.send_meeting_notification(meeting, "requested", client.user)
        except Exception as e:
            # Don't fail the meeting creation if notification fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to send meeting notification: {e}")


@extend_schema(
    tags=["Meeting Management"],
    summary="Get or update meeting details",
    description="Retrieve detailed information about a specific meeting or update meeting properties including scheduling, notes, and host assignment.",
)
class MeetingDetailView(generics.RetrieveUpdateAPIView):
    """Get and update meeting details"""

    permission_classes = [CanManageMeetings]

    def get_queryset(self):
        queryset = Meeting.objects.select_related("client__user", "host").all()
        try:
            user_role = self.request.user.admin_profile.role
            if user_role and user_role.name != "super_admin" and not user_role.can_view_all_clients:
                queryset = queryset.filter(client__assigned_admin=self.request.user)
        except AttributeError:
            pass
        return queryset

    def get_serializer_class(self):
        if self.request.method == "GET":
            return MeetingDetailSerializer
        return MeetingUpdateSerializer


@extend_schema(
    tags=["Meeting Management"],
    summary="Perform meeting actions",
    description="Execute meeting management actions including confirm, reschedule, decline, complete, or cancel meetings with automatic client notifications.",
)
class MeetingActionsView(APIView):
    """Meeting management actions"""

    permission_classes = [CanManageMeetings]

    def post(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk)
            serializer = MeetingActionSerializer(data=request.data)

            if serializer.is_valid():
                action = serializer.validated_data["action"]

                if action == "confirm":
                    confirmed_datetime = serializer.validated_data.get(
                        "confirmed_datetime"
                    )
                    if confirmed_datetime:
                        meeting.confirmed_datetime = confirmed_datetime
                    else:
                        meeting.confirmed_datetime = meeting.requested_datetime

                    meeting.status = "confirmed"

                    # Create calendar event
                    event_id = CalendarService.create_calendar_event(meeting)
                    if event_id:
                        meeting.calendar_event_id = event_id

                    meeting.save()

                    # Send notification
                    NotificationService.send_meeting_notification(
                        meeting, "confirmed", meeting.client.user
                    )

                    return Response({"message": "Meeting confirmed successfully"})

                elif action == "reschedule":
                    confirmed_datetime = serializer.validated_data.get(
                        "confirmed_datetime"
                    )
                    if not confirmed_datetime:
                        return Response(
                            {"error": "New datetime required for rescheduling"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    meeting.confirmed_datetime = confirmed_datetime
                    meeting.status = "rescheduled"
                    meeting.save()

                    # Create notification for client
                    from admin_portal.models import SystemNotification

                    SystemNotification.objects.create(
                        notification_type="meeting_updated",
                        title="Meeting Rescheduled",
                        message=f"Your meeting has been rescheduled to {meeting.confirmed_datetime}",
                        recipient=meeting.client.user,
                        related_meeting=meeting,
                    )

                    return Response({"message": "Meeting rescheduled successfully"})

                elif action == "decline":
                    notes = serializer.validated_data.get("notes", "")
                    meeting.status = "declined"
                    if notes:
                        meeting.internal_notes = notes
                    meeting.save()

                    from admin_portal.models import SystemNotification

                    SystemNotification.objects.create(
                        notification_type="meeting_updated",
                        title="Meeting Declined",
                        message="Your meeting request has been declined. Please contact us for alternative arrangements.",
                        recipient=meeting.client.user,
                        related_meeting=meeting,
                    )

                    return Response({"message": "Meeting declined"})

                elif action == "complete":
                    meeting.status = "completed"
                    notes = serializer.validated_data.get("notes", "")
                    if notes:
                        meeting.meeting_notes = notes
                    meeting.save()

                    return Response({"message": "Meeting marked as completed"})

                elif action == "cancel":
                    meeting.status = "cancelled"
                    notes = serializer.validated_data.get("notes", "")
                    if notes:
                        meeting.internal_notes = notes
                    meeting.save()

                    # Create notification for client
                    from admin_portal.models import SystemNotification

                    SystemNotification.objects.create(
                        notification_type="meeting_updated",
                        title="Meeting Cancelled",
                        message="Your meeting has been cancelled. We will contact you to reschedule.",
                        recipient=meeting.client.user,
                        related_meeting=meeting,
                    )

                    return Response({"message": "Meeting cancelled"})

                else:
                    return Response(
                        {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                    )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Meeting.DoesNotExist:
            return Response(
                {"error": "Meeting not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Meeting Management"],
    summary="Assign meeting host",
    description="Assign or unassign a host to a meeting request with automatic notifications to the assigned host.",
)
class MeetingAssignView(APIView):
    """Assign meeting to host"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            meeting = Meeting.objects.get(pk=pk)
            host_id = request.data.get("host_id")

            if host_id:
                from django.contrib.auth.models import User

                try:
                    host = User.objects.get(pk=host_id)
                    meeting.host = host
                    meeting.save()

                    # Create notification for host
                    from admin_portal.models import SystemNotification

                    SystemNotification.objects.create(
                        notification_type="meeting_updated",
                        title="Meeting Assigned",
                        message=f"You have been assigned to host a meeting with {meeting.client.user.get_full_name()}",
                        recipient=host,
                        related_meeting=meeting,
                    )

                    return Response({"message": "Meeting assigned successfully"})
                except User.DoesNotExist:
                    return Response(
                        {"error": "Host not found"}, status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Unassign meeting
                meeting.host = None
                meeting.save()
                return Response({"message": "Meeting unassigned"})

        except Meeting.DoesNotExist:
            return Response(
                {"error": "Meeting not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Meeting Management"],
    summary="Get meeting statistics",
    description="Retrieve comprehensive meeting analytics including counts by status/type, average confirmation times, and upcoming meetings list.",
)
class MeetingStatsView(APIView):
    """Meeting statistics and analytics"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Basic meeting counts
        total_meetings = Meeting.objects.count()
        requested_meetings = Meeting.objects.filter(status="requested").count()
        confirmed_meetings = Meeting.objects.filter(status="confirmed").count()
        completed_meetings = Meeting.objects.filter(status="completed").count()
        cancelled_meetings = Meeting.objects.filter(status="cancelled").count()

        # Average confirmation time (placeholder - would need actual calculation)
        avg_confirmation_time = 4.5  # hours

        # Meetings by type
        meetings_by_type = dict(
            Meeting.objects.values("meeting_type")
            .annotate(count=Count("id"))
            .values_list("meeting_type", "count")
        )

        # Upcoming meetings (next 7 days)
        from datetime import timedelta

        upcoming_meetings_qs = Meeting.objects.filter(
            confirmed_datetime__gte=timezone.now(),
            confirmed_datetime__lte=timezone.now() + timedelta(days=7),
            status="confirmed",
        ).select_related("client__user")[:10]

        upcoming_meetings = [
            {
                "id": m.id,
                "client_name": m.client.user.get_full_name(),
                "datetime": m.confirmed_datetime,
                "type": m.get_meeting_type_display(),
            }
            for m in upcoming_meetings_qs
        ]

        stats_data = {
            "total_meetings": total_meetings,
            "requested_meetings": requested_meetings,
            "confirmed_meetings": confirmed_meetings,
            "completed_meetings": completed_meetings,
            "cancelled_meetings": cancelled_meetings,
            "avg_confirmation_time": avg_confirmation_time,
            "meetings_by_type": meetings_by_type,
            "upcoming_meetings": upcoming_meetings,
        }

        serializer = MeetingStatsSerializer(stats_data)
        return Response(serializer.data)


@extend_schema(
    tags=["Meeting Management"],
    summary="Get my assigned meetings",
    description="Retrieve all meetings assigned to the current authenticated user as host, ordered by confirmed datetime.",
)
class MyMeetingsView(generics.ListAPIView):
    """Get meetings assigned to current user"""

    serializer_class = MeetingListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Meeting.objects.filter(host=self.request.user)
            .select_related("client__user")
            .order_by("-created_at")
        )


@extend_schema(
    tags=["Meeting Management"],
    summary="Get confirmed meetings",
    description="Retrieve all confirmed meetings, optionally filtered by assigned host.",
)
class ConfirmedMeetingsView(generics.ListAPIView):
    """Get confirmed meetings"""

    serializer_class = MeetingListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Meeting.objects.filter(status="confirmed")
            .select_related("client__user", "host")
            .order_by("confirmed_datetime")
        )
        
        # Filter by assigned host if requested
        host_id = self.request.query_params.get('host_id')
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        
        return queryset


@extend_schema(
    tags=["Meeting Management"],
    summary="Get requested meetings",
    description="Retrieve all requested meetings, optionally filtered by assigned host.",
)
class RequestedMeetingsView(generics.ListAPIView):
    """Get requested meetings"""

    serializer_class = MeetingListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            Meeting.objects.filter(status="requested")
            .select_related("client__user", "host")
            .order_by("-created_at")
        )
        
        # Filter by assigned host if requested
        host_id = self.request.query_params.get('host_id')
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        
        return queryset


@extend_schema(
    tags=["Meeting Management"],
    summary="Get upcoming meetings",
    description="Retrieve confirmed meetings scheduled for the next 7 days, useful for dashboard widgets and planning.",
)
class UpcomingMeetingsView(generics.ListAPIView):
    """Get upcoming meetings for dashboard"""

    serializer_class = MeetingListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from datetime import timedelta

        return (
            Meeting.objects.filter(
                confirmed_datetime__gte=timezone.now(),
                confirmed_datetime__lte=timezone.now() + timedelta(days=7),
                status="confirmed",
            )
            .select_related("client__user", "host")
            .order_by("confirmed_datetime")
        )
