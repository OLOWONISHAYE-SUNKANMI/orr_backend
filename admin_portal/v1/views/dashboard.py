from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import (
    AIConversation,
    Client,
    Content,
    Meeting,
    SystemNotification,
    Ticket,
)
from admin_portal.permissions import IsAdminUser
from admin_portal.services import AnalyticsService, SystemHealthService

from ..serializers.dashboard import (
    DashboardStatsSerializer,
    QuickClientSerializer,
    QuickMeetingSerializer,
    QuickTicketSerializer,
)


@extend_schema(
    tags=["Admin Dashboard"],
    summary="Get dashboard overview metrics",
    description="Retrieve key metrics for the admin dashboard including active clients, pending tickets, upcoming meetings, system notifications, portal logins, AI chat sessions, and escalation rates.",
)
class DashboardOverviewView(APIView):
    """Admin dashboard overview with key metrics"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        # Calculate date ranges
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        
        user_role = request.user.admin_profile.role
        
        # Base querysets with visibility boundaries
        client_qs = Client.objects.all()
        ticket_qs = Ticket.objects.all()
        meeting_qs = Meeting.objects.all()
        
        if user_role.name != "super_admin" and not user_role.can_view_all_clients:
            client_qs = client_qs.filter(assigned_admin=request.user)
            ticket_qs = ticket_qs.filter(client__assigned_admin=request.user)
            meeting_qs = meeting_qs.filter(client__assigned_admin=request.user)

        # Active clients (logged in within last 30 days)
        active_clients = client_qs.filter(
            user__last_login__gte=now - timedelta(days=30)
        ).count()

        # Pending tickets by status
        pending_tickets = {
            "new": ticket_qs.filter(status="new").count(),
            "in_progress": ticket_qs.filter(status="in_progress").count(),
            "waiting_client": ticket_qs.filter(status="waiting_client").count(),
        }

        # Upcoming meetings (next 7 days)
        upcoming_meetings = meeting_qs.filter(
            confirmed_datetime__gte=now,
            confirmed_datetime__lte=now + timedelta(days=7),
            status="confirmed",
        ).count()

        # System notifications (unread)
        system_notifications = 0  # SystemNotification.objects.filter(
        # recipient=request.user, is_read=False
        # ).count()

        # Portal logins in last 7 days
        portal_logins_7days = Client.objects.filter(
            user__last_login__gte=seven_days_ago
        ).count()

        # AI chat sessions and escalation rate
        ai_sessions = 0  # AIConversation.objects.filter(
        # created_at__gte=seven_days_ago
        # ).count()

        escalated_sessions = 0  # AIConversation.objects.filter(
        # created_at__gte=seven_days_ago, escalated_to_ticket=True
        # ).count()

        escalation_rate = (
            (escalated_sessions / ai_sessions * 100) if ai_sessions > 0 else 0
        )

        # Most-used resources (top 5 by view count)
        most_used_resources = list(
            Content.objects.filter(status="published")
            .order_by("-view_count")[:5]
            .values("id", "title", "content_type", "view_count")
        )

        # System health status
        system_health = SystemHealthService.get_system_health()

        from admin_portal.models import TechnicalFeedback
        
        # Pending technical feedback
        pending_feedback = TechnicalFeedback.objects.filter(status__in=['open', 'in_progress']).count()

        stats_data = {
            "active_clients": active_clients,
            "active_clients_link": "/admin-portal/v1/clients/?activity=active",
            "pending_tickets": pending_tickets,
            "upcoming_meetings": upcoming_meetings,
            "system_notifications": system_notifications,
            "portal_logins_7days": portal_logins_7days,
            "ai_chat_sessions": ai_sessions,
            "escalation_rate": round(escalation_rate, 2),
            "most_used_resources": most_used_resources,
            "system_health": system_health,
            "pending_technical_feedback": pending_feedback,
        }

        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data)


@extend_schema(
    tags=["Admin Dashboard"],
    summary="Get recent activity feed",
    description="Retrieve recent activity including the latest clients, tickets, and meetings for the dashboard feed.",
)
class RecentActivityView(APIView):
    """Recent activity feed for dashboard"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        # Role-based client filtering
        user_role = request.user.admin_profile.role
        client_queryset = Client.objects.select_related("user", "assigned_admin")

        if user_role.name == "admin" and not user_role.can_view_all_clients:
            # Admin can only see clients assigned to them
            client_queryset = client_queryset.filter(assigned_admin=request.user)

        # Recent clients (last 10)
        recent_clients = client_queryset.order_by("-created_at")[:10]

        # Recent tickets (last 10)
        recent_tickets = Ticket.objects.select_related("client__user").order_by(
            "-created_at"
        )[:10]

        # Recent meetings (last 10)
        recent_meetings = Meeting.objects.select_related("client__user").order_by(
            "-created_at"
        )[:10]

        return Response(
            {
                "recent_clients": QuickClientSerializer(recent_clients, many=True).data,
                "recent_tickets": QuickTicketSerializer(recent_tickets, many=True).data,
                "recent_meetings": QuickMeetingSerializer(
                    recent_meetings, many=True
                ).data,
            }
        )


@extend_schema(
    tags=["Admin Dashboard"],
    summary="Get quick statistics",
    description="Retrieve quick statistics for dashboard widgets including today's metrics and weekly summaries.",
)
class QuickStatsView(APIView):
    """Quick statistics for dashboard widgets"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()

        # Today's stats
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        return Response(
            {
                "today": {
                    "new_tickets": Ticket.objects.filter(
                        created_at__gte=today_start
                    ).count(),
                    "meetings_scheduled": Meeting.objects.filter(
                        confirmed_datetime__date=now.date(), status="confirmed"
                    ).count(),
                    "ai_conversations": 0,  # AIConversation.objects.filter(
                    # created_at__gte=today_start
                    # ).count(),
                },
                "this_week": {
                    "tickets_resolved": Ticket.objects.filter(
                        status="resolved", updated_at__gte=now - timedelta(days=7)
                    ).count(),
                    "meetings_completed": Meeting.objects.filter(
                        status="completed", updated_at__gte=now - timedelta(days=7)
                    ).count(),
                    "new_clients": Client.objects.filter(
                        created_at__gte=now - timedelta(days=7)
                    ).count(),
                },
            }
        )


@extend_schema(
    tags=["Admin Dashboard"],
    summary="Get client management dashboard widgets",
    description="Retrieve client-specific dashboard widgets including client distribution by stage/pillar, recent client activity, and quick access links.",
)
class ClientDashboardWidgetsView(APIView):
    """Client management dashboard widgets"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Role-based client access
        user_role = request.user.admin_profile.role
        client_queryset = Client.objects.all()

        if user_role.name == "admin" and not user_role.can_view_all_clients:
            client_queryset = client_queryset.filter(assigned_admin=request.user)

        # Client distribution by stage
        clients_by_stage = dict(
            client_queryset.values("stage")
            .annotate(count=Count("id"))
            .values_list("stage", "count")
        )

        # Client distribution by pillar
        clients_by_pillar = dict(
            client_queryset.values("primary_pillar")
            .annotate(count=Count("id"))
            .values_list("primary_pillar", "count")
        )

        # Recent client activity (last 7 days)
        now = timezone.now()
        recent_activity = {
            "new_clients": client_queryset.filter(
                created_at__gte=now - timedelta(days=7)
            ).count(),
            "active_clients": client_queryset.filter(
                user__last_login__gte=now - timedelta(days=7)
            ).count(),
            "dormant_clients": client_queryset.filter(
                Q(user__last_login__lt=now - timedelta(days=30))
                | Q(user__last_login__isnull=True)
            ).count(),
        }

        # Quick access links
        quick_links = {
            "all_clients": "/admin-portal/v1/clients/",
            "active_clients": "/admin-portal/v1/clients/?activity=active",
            "dormant_clients": "/admin-portal/v1/clients/?activity=dormant",
            "new_clients": f"/admin-portal/v1/clients/?created_after={now - timedelta(days=7)}",
        }

        return Response(
            {
                "clients_by_stage": clients_by_stage,
                "clients_by_pillar": clients_by_pillar,
                "recent_activity": recent_activity,
                "quick_links": quick_links,
                "total_clients": client_queryset.count(),
            }
        )
