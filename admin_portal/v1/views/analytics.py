from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import AIConversation, Client, Content, Meeting, Ticket
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Analytics & Reporting"],
    summary="Get comprehensive analytics overview",
    description="Retrieve comprehensive analytics including portal usage, content performance, ticket metrics, AI chat analytics, and meeting statistics across different time periods.",
)
class AnalyticsOverviewView(APIView):
    """Analytics overview with key metrics"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()

        # Date ranges
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)
        last_90_days = now - timedelta(days=90)
        
        user_role = request.user.admin_profile.role
        
        client_qs = Client.objects.all()
        ticket_qs = Ticket.objects.all()
        meeting_qs = Meeting.objects.all()
        
        if user_role.name != "super_admin" and not user_role.can_view_all_clients:
            client_qs = client_qs.filter(assigned_admin=request.user)
            ticket_qs = ticket_qs.filter(client__assigned_admin=request.user)
            meeting_qs = meeting_qs.filter(client__assigned_admin=request.user)

        # Client portal usage
        portal_usage = {
            "total_clients": client_qs.count(),
            "active_clients_7d": client_qs.filter(
                user__last_login__gte=last_7_days
            ).count(),
            "active_clients_30d": client_qs.filter(
                user__last_login__gte=last_30_days
            ).count(),
            "new_clients_30d": client_qs.filter(
                created_at__gte=last_30_days
            ).count(),
        }

        # Content analytics
        content_analytics = {
            "total_content": Content.objects.filter(status="published").count(),
            "most_viewed": list(
                Content.objects.filter(status="published")
                .order_by("-view_count")[:5]
                .values("id", "title", "view_count", "content_type")
            ),
            "most_downloaded": list(
                Content.objects.filter(status="published", attachment__isnull=False)
                .order_by("-download_count")[:5]
                .values("id", "title", "download_count", "content_type")
            ),
            "content_by_stage": dict(
                Content.objects.filter(status="published")
                .values("stage")
                .annotate(count=Count("id"))
                .values_list("stage", "count")
            ),
            "content_by_pillar": self._get_content_by_pillar(),
        }

        # Ticket analytics
        ticket_analytics = {
            "total_tickets": ticket_qs.count(),
            "tickets_7d": ticket_qs.filter(created_at__gte=last_7_days).count(),
            "tickets_30d": ticket_qs.filter(created_at__gte=last_30_days).count(),
            "avg_resolution_time": self._calculate_avg_resolution_time(),
            "tickets_by_status": dict(
                ticket_qs.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "tickets_by_priority": dict(
                ticket_qs.values("priority")
                .annotate(count=Count("id"))
                .values_list("priority", "count")
            ),
        }

        # AI chat analytics
        ai_analytics = {
            "total_conversations": AIConversation.objects.count(),
            "conversations_7d": AIConversation.objects.filter(
                created_at__gte=last_7_days
            ).count(),
            "escalation_rate": self._calculate_escalation_rate(),
            "conversations_needing_improvement": AIConversation.objects.filter(
                needs_improvement=True
            ).count(),
        }

        # Meeting analytics
        meeting_analytics = {
            "total_meetings": meeting_qs.count(),
            "meetings_requested_30d": meeting_qs.filter(
                created_at__gte=last_30_days
            ).count(),
            "meetings_completed_30d": meeting_qs.filter(
                status="completed", updated_at__gte=last_30_days
            ).count(),
            "avg_confirmation_time": self._calculate_avg_confirmation_time(),
            "meetings_by_type": dict(
                meeting_qs.values("meeting_type")
                .annotate(count=Count("id"))
                .values_list("meeting_type", "count")
            ),
        }

        return Response(
            {
                "portal_usage": portal_usage,
                "content_analytics": content_analytics,
                "ticket_analytics": ticket_analytics,
                "ai_analytics": ai_analytics,
                "meeting_analytics": meeting_analytics,
            }
        )

    def _get_content_by_pillar(self):
        """Get content count by pillar"""
        pillar_counts = {}
        for pillar_code, pillar_name in Content.PILLAR_CHOICES:
            count = Content.objects.filter(
                status="published", pillars__contains=[pillar_code]
            ).count()
            pillar_counts[pillar_code] = count
        return pillar_counts

    def _calculate_avg_resolution_time(self):
        """Calculate average ticket resolution time in hours"""
        from admin_portal.services import AnalyticsService

        return AnalyticsService.calculate_ticket_resolution_time()

    def _calculate_escalation_rate(self):
        """Calculate AI conversation escalation rate"""
        total_conversations = AIConversation.objects.count()
        escalated_conversations = AIConversation.objects.filter(
            escalated_to_ticket=True
        ).count()

        if total_conversations > 0:
            return round((escalated_conversations / total_conversations) * 100, 2)
        return 0

    def _calculate_avg_confirmation_time(self):
        """Calculate average meeting confirmation time in hours"""
        from admin_portal.services import AnalyticsService

        return AnalyticsService.calculate_meeting_confirmation_time()


@extend_schema(
    tags=["Analytics & Reporting"],
    summary="Get detailed client analytics",
    description="Retrieve detailed client analytics including daily login patterns, distribution by stage/pillar, and most active clients over the last 30 days.",
)
class ClientAnalyticsView(APIView):
    """Detailed client analytics"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        # Client engagement over time
        now = timezone.now()
        last_30_days = now - timedelta(days=30)

        # Daily login counts for last 30 days
        daily_logins = []
        for i in range(30):
            date = (now - timedelta(days=i)).date()
            count = Client.objects.filter(user__last_login__date=date).count()
            daily_logins.append({"date": date.isoformat(), "count": count})

        # Client distribution by stage
        stage_distribution = dict(
            Client.objects.values("stage")
            .annotate(count=Count("id"))
            .values_list("stage", "count")
        )

        # Client distribution by pillar
        pillar_distribution = dict(
            Client.objects.values("primary_pillar")
            .annotate(count=Count("id"))
            .values_list("primary_pillar", "count")
        )

        # Most active clients
        most_active_clients = list(
            Client.objects.select_related("user")
            .filter(user__last_login__gte=last_30_days)
            .order_by("-user__last_login")[:10]
            .values(
                "id",
                "user__first_name",
                "user__last_name",
                "company",
                "user__last_login",
            )
        )

        return Response(
            {
                "daily_logins": daily_logins,
                "stage_distribution": stage_distribution,
                "pillar_distribution": pillar_distribution,
                "most_active_clients": most_active_clients,
            }
        )


@extend_schema(
    tags=["Analytics & Reporting"],
    summary="Get detailed content analytics",
    description="Retrieve detailed content performance metrics, creation trends over 6 months, and content gaps analysis by stage and pillar.",
)
class ContentAnalyticsView(APIView):
    """Detailed content analytics"""

    permission_classes = [IsAdminUser]

    def get(self, request):
        # Content performance metrics
        content_performance = list(
            Content.objects.filter(status="published")
            .order_by("-view_count")[:20]
            .values(
                "id",
                "title",
                "content_type",
                "stage",
                "view_count",
                "download_count",
                "published_at",
            )
        )

        # Content creation over time (last 6 months)
        now = timezone.now()
        monthly_content = []
        for i in range(6):
            month_start = (now - timedelta(days=30 * i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(
                days=1
            )

            count = Content.objects.filter(
                created_at__gte=month_start, created_at__lte=month_end
            ).count()

            monthly_content.append(
                {"month": month_start.strftime("%Y-%m"), "count": count}
            )

        # Content gaps analysis
        content_gaps = self._analyze_content_gaps()

        return Response(
            {
                "content_performance": content_performance,
                "monthly_content_creation": monthly_content,
                "content_gaps": content_gaps,
            }
        )

    def _analyze_content_gaps(self):
        """Analyze content gaps by stage and pillar"""
        gaps = {}

        for stage_code, stage_name in Content.STAGE_CHOICES:
            for pillar_code, pillar_name in Content.PILLAR_CHOICES:
                count = Content.objects.filter(
                    status="published",
                    stage=stage_code,
                    pillars__contains=[pillar_code],
                ).count()

                if stage_code not in gaps:
                    gaps[stage_code] = {}
                gaps[stage_code][pillar_code] = count

        return gaps


@extend_schema(
    tags=["Analytics & Reporting"],
    summary="Export analytics data",
    description="Request export of analytics data in various formats (CSV/PDF) for specified date ranges and data types.",
)
class ExportAnalyticsView(APIView):
    """Export analytics data"""

    permission_classes = [IsAdminUser]

    def post(self, request):
        export_type = request.data.get("type")
        date_from = request.data.get("date_from")
        date_to = request.data.get("date_to")

        # Here you would implement actual export functionality
        # For now, return a placeholder response

        return Response(
            {
                "message": f"Export {export_type} requested",
                "export_id": "EXP-001",
                "status": "processing",
                "estimated_completion": timezone.now() + timedelta(minutes=5),
            }
        )
