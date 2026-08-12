from datetime import datetime, timedelta
from django.db.models import Count, Q, Avg
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import Client, Content, Meeting, Ticket, AIConversation
from client.models import OnboardingQuestionnaire
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Sector Insights"],
    summary="Get sector-based analytics",
    description="Analyze client distribution and engagement patterns across different business sectors and stages."
)
class SectorAnalyticsView(APIView):
    """Analyze sector-based client distribution and engagement"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Client distribution by user type (sector)
        sector_data = OnboardingQuestionnaire.objects.values('user_type').annotate(count=Count('id'))
        sector_distribution = dict(sector_data.values_list('user_type', 'count'))
        
        # Project stage distribution
        stage_data = OnboardingQuestionnaire.objects.values('project_stage').annotate(count=Count('id'))
        stage_distribution = dict(stage_data.values_list('project_stage', 'count'))
        
        # ORR pillar preferences by sector
        pillar_by_sector = self._get_pillar_preferences_by_sector()
        
        # Engagement metrics by sector
        engagement_by_sector = self._get_engagement_by_sector()
        
        # Success metrics by sector
        success_metrics = self._get_success_metrics_by_sector()
        
        return Response({
            "sector_distribution": sector_distribution,
            "stage_distribution": stage_distribution,
            "pillar_preferences": pillar_by_sector,
            "engagement_metrics": engagement_by_sector,
            "success_metrics": success_metrics
        })
    
    def _get_pillar_preferences_by_sector(self):
        """Get ORR pillar preferences by business sector"""
        pillar_data = {}
        
        # Get all questionnaires with user type and pillar data
        questionnaires = OnboardingQuestionnaire.objects.filter(
            orr_pillars__isnull=False
        ).values('user_type', 'orr_pillars')
        
        for q in questionnaires:
            sector = q['user_type']
            pillars = q['orr_pillars']
            
            if sector not in pillar_data:
                pillar_data[sector] = {}
            
            for pillar in pillars:
                if pillar not in pillar_data[sector]:
                    pillar_data[sector][pillar] = 0
                pillar_data[sector][pillar] += 1
        
        return pillar_data
    
    def _get_engagement_by_sector(self):
        """Get engagement metrics by business sector"""
        engagement_data = {}
        
        # Get all user types
        user_types = OnboardingQuestionnaire.objects.values_list('user_type', flat=True).distinct()
        
        for user_type in user_types:
            # Get clients for this user type
            client_ids = OnboardingQuestionnaire.objects.filter(
                user_type=user_type
            ).values_list('user__client_profile__id', flat=True)
            
            engagement_data[user_type] = {
                "avg_meetings": Meeting.objects.filter(
                    client_id__in=client_ids
                ).count() / len(client_ids) if client_ids else 0,
                "avg_tickets": Ticket.objects.filter(
                    client_id__in=client_ids
                ).count() / len(client_ids) if client_ids else 0,
                "completion_rate": OnboardingQuestionnaire.objects.filter(
                    user_type=user_type, is_completed=True
                ).count() / OnboardingQuestionnaire.objects.filter(
                    user_type=user_type
                ).count() * 100 if OnboardingQuestionnaire.objects.filter(user_type=user_type).exists() else 0
            }
        
        return engagement_data
    
    def _get_success_metrics_by_sector(self):
        """Get success metrics by business sector"""
        success_data = {}
        
        user_types = OnboardingQuestionnaire.objects.values_list('user_type', flat=True).distinct()
        
        for user_type in user_types:
            client_ids = OnboardingQuestionnaire.objects.filter(
                user_type=user_type
            ).values_list('user__client_profile__id', flat=True)
            
            success_data[user_type] = {
                "meeting_completion_rate": self._calculate_meeting_completion_rate(client_ids),
                "ticket_resolution_rate": self._calculate_ticket_resolution_rate(client_ids),
                "retention_rate": self._calculate_retention_rate(client_ids)
            }
        
        return success_data
    
    def _calculate_meeting_completion_rate(self, client_ids):
        """Calculate meeting completion rate for given clients"""
        total_meetings = Meeting.objects.filter(client_id__in=client_ids).count()
        completed_meetings = Meeting.objects.filter(
            client_id__in=client_ids, status='completed'
        ).count()
        
        if total_meetings > 0:
            return round((completed_meetings / total_meetings) * 100, 2)
        return 0
    
    def _calculate_ticket_resolution_rate(self, client_ids):
        """Calculate ticket resolution rate for given clients"""
        total_tickets = Ticket.objects.filter(client_id__in=client_ids).count()
        resolved_tickets = Ticket.objects.filter(
            client_id__in=client_ids, status='resolved'
        ).count()
        
        if total_tickets > 0:
            return round((resolved_tickets / total_tickets) * 100, 2)
        return 0
    
    def _calculate_retention_rate(self, client_ids):
        """Calculate retention rate for given clients"""
        total_clients = len(client_ids)
        active_clients = Client.objects.filter(
            id__in=client_ids,
            user__last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        if total_clients > 0:
            return round((active_clients / total_clients) * 100, 2)
        return 0


@extend_schema(
    tags=["Sector Insights"],
    summary="Get industry benchmarks",
    description="Get industry benchmarks and comparative analysis across different business sectors."
)
class IndustryBenchmarksView(APIView):
    """Industry benchmarks and comparative analysis"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Industry averages
        industry_averages = {
            "avg_onboarding_time": self._calculate_avg_onboarding_time(),
            "avg_first_meeting_time": self._calculate_avg_first_meeting_time(),
            "avg_ticket_resolution": self._calculate_avg_ticket_resolution(),
            "avg_engagement_score": self._calculate_avg_engagement_score()
        }
        
        # Sector performance comparison
        sector_performance = self._get_sector_performance_comparison()
        
        # Growth trends by sector
        growth_trends = self._get_growth_trends_by_sector()
        
        return Response({
            "industry_averages": industry_averages,
            "sector_performance": sector_performance,
            "growth_trends": growth_trends
        })
    
    def _calculate_avg_onboarding_time(self):
        """Calculate average onboarding completion time from actual data"""
        completed_onboarding = OnboardingQuestionnaire.objects.filter(
            is_completed=True,
            updated_at__isnull=False
        )
        
        if completed_onboarding.exists():
            total_days = sum([(q.updated_at - q.created_at).days for q in completed_onboarding])
            return round(total_days / completed_onboarding.count(), 1)
        return 0
    
    def _calculate_avg_first_meeting_time(self):
        """Calculate average time from registration to first meeting"""
        clients_with_meetings = Client.objects.filter(meetings__isnull=False).distinct()
        
        if clients_with_meetings.exists():
            total_days = 0
            count = 0
            
            for client in clients_with_meetings:
                first_meeting = client.meetings.order_by('created_at').first()
                if first_meeting:
                    days_diff = (first_meeting.created_at.date() - client.created_at.date()).days
                    total_days += days_diff
                    count += 1
            
            return round(total_days / count, 1) if count > 0 else 0
        return 0
    
    def _calculate_avg_ticket_resolution(self):
        """Calculate average ticket resolution time from actual data"""
        resolved_tickets = Ticket.objects.filter(
            status='resolved',
            updated_at__isnull=False
        )
        
        if resolved_tickets.exists():
            total_days = sum([(ticket.updated_at.date() - ticket.created_at.date()).days for ticket in resolved_tickets])
            return round(total_days / resolved_tickets.count(), 1)
        return 0
    
    def _calculate_avg_engagement_score(self):
        """Calculate average engagement score based on user activity"""
        total_clients = Client.objects.count()
        if total_clients == 0:
            return 0
        
        # Score based on feature usage (out of 10)
        ai_users = AIConversation.objects.values('client').distinct().count()
        meeting_users = Meeting.objects.values('client').distinct().count()
        ticket_users = Ticket.objects.values('client').distinct().count()
        active_users = Client.objects.filter(
            user__last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        ai_score = (ai_users / total_clients) * 2.5
        meeting_score = (meeting_users / total_clients) * 2.5
        ticket_score = (ticket_users / total_clients) * 2.5
        activity_score = (active_users / total_clients) * 2.5
        
        return round(ai_score + meeting_score + ticket_score + activity_score, 1)
    
    def _get_sector_performance_comparison(self):
        """Get performance comparison across sectors from actual data"""
        sectors = OnboardingQuestionnaire.objects.values_list('user_type', flat=True).distinct()
        
        performance_data = {}
        for sector in sectors:
            # Get clients for this sector
            sector_clients = Client.objects.filter(
                user__onboarding__user_type=sector
            ).distinct()
            
            total_sector_clients = sector_clients.count()
            if total_sector_clients == 0:
                continue
            
            # Calculate engagement score
            active_clients = sector_clients.filter(
                user__last_login__gte=timezone.now() - timedelta(days=30)
            ).count()
            engagement_score = round((active_clients / total_sector_clients) * 10, 1)
            
            # Calculate satisfaction score based on meeting completion
            sector_meetings = Meeting.objects.filter(client__in=sector_clients)
            completed_meetings = sector_meetings.filter(status='completed').count()
            total_meetings = sector_meetings.count()
            satisfaction_score = round((completed_meetings / total_meetings) * 10, 1) if total_meetings > 0 else 0
            
            # Calculate retention rate
            retention_rate = round((active_clients / total_sector_clients) * 100, 1)
            
            performance_data[sector] = {
                "engagement_score": engagement_score,
                "satisfaction_score": satisfaction_score,
                "retention_rate": retention_rate
            }
        
        return performance_data
    
    def _get_growth_trends_by_sector(self):
        """Get growth trends by sector over time"""
        now = timezone.now()
        trends = {}
        
        sectors = OnboardingQuestionnaire.objects.values_list('user_type', flat=True).distinct()
        
        for sector in sectors:
            monthly_data = []
            for i in range(6):  # Last 6 months
                month_start = (now - timedelta(days=30 * i)).replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                
                count = OnboardingQuestionnaire.objects.filter(
                    user_type=sector,
                    created_at__gte=month_start,
                    created_at__lte=month_end
                ).count()
                
                monthly_data.append({
                    "month": month_start.strftime("%Y-%m"),
                    "count": count
                })
            
            trends[sector] = monthly_data
        
        return trends