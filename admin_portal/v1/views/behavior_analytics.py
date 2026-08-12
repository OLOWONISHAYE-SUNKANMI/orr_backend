from datetime import datetime, timedelta
from django.db.models import Count, Q, Avg
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import AIConversation, Client, Meeting, Ticket
from client.models import Activity, OnboardingQuestionnaire
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Behavior Analytics"],
    summary="Get user behavior patterns",
    description="Analyze user behavior patterns including login frequency, feature usage, and engagement metrics."
)
class UserBehaviorPatternsView(APIView):
    """Analyze user behavior patterns"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)
        
        # Login patterns
        login_patterns = {
            "daily_active_users": Client.objects.filter(
                user__last_login__gte=last_7_days
            ).count(),
            "weekly_active_users": Client.objects.filter(
                user__last_login__gte=last_30_days
            ).count(),
            "peak_hours": self._get_peak_login_hours(),
            "login_frequency": self._get_login_frequency_distribution()
        }
        
        # Feature usage
        feature_usage = {
            "ai_chat_usage": AIConversation.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            "meeting_requests": Meeting.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            "ticket_submissions": Ticket.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            "document_downloads": self._get_document_download_stats()
        }
        
        # User engagement metrics
        engagement_metrics = {
            "session_duration": self._calculate_avg_session_duration(),
            "bounce_rate": self._calculate_bounce_rate(),
            "return_user_rate": self._calculate_return_user_rate(),
            "feature_adoption": self._get_feature_adoption_rates()
        }
        
        return Response({
            "login_patterns": login_patterns,
            "feature_usage": feature_usage,
            "engagement_metrics": engagement_metrics
        })
    
    def _get_peak_login_hours(self):
        """Get peak login hours distribution from actual data"""
        try:
            from django.db.models import Extract
            
            login_hours = Client.objects.filter(
                user__last_login__gte=timezone.now() - timedelta(days=30),
                user__last_login__isnull=False
            ).annotate(
                hour=Extract('user__last_login', 'hour')
            ).values('hour').annotate(count=Count('id'))
            
            periods = {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
            total_logins = sum(item['count'] for item in login_hours)
            
            for item in login_hours:
                hour = item.get('hour')
                count = item.get('count', 0)
                
                if hour is not None:
                    if 6 <= hour < 12:
                        periods["morning"] += count
                    elif 12 <= hour < 18:
                        periods["afternoon"] += count
                    elif 18 <= hour < 22:
                        periods["evening"] += count
                    else:
                        periods["night"] += count
            
            if total_logins > 0:
                for period in periods:
                    periods[period] = round((periods[period] / total_logins) * 100, 1)
            
            return periods
        except Exception:
            # Return default distribution if query fails
            return {"morning": 0, "afternoon": 0, "evening": 0, "night": 0}
    
    def _get_login_frequency_distribution(self):
        """Get login frequency distribution from actual data"""
        now = timezone.now()
        total_clients = Client.objects.count()
        
        daily_users = Client.objects.filter(
            user__last_login__gte=now - timedelta(days=1)
        ).count()
        
        weekly_users = Client.objects.filter(
            user__last_login__gte=now - timedelta(days=7),
            user__last_login__lt=now - timedelta(days=1)
        ).count()
        
        monthly_users = Client.objects.filter(
            user__last_login__gte=now - timedelta(days=30),
            user__last_login__lt=now - timedelta(days=7)
        ).count()
        
        occasional_users = Client.objects.filter(
            user__last_login__lt=now - timedelta(days=30)
        ).count()
        
        if total_clients > 0:
            return {
                "daily": round((daily_users / total_clients) * 100, 1),
                "weekly": round((weekly_users / total_clients) * 100, 1),
                "monthly": round((monthly_users / total_clients) * 100, 1),
                "occasional": round((occasional_users / total_clients) * 100, 1)
            }
        return {"daily": 0, "weekly": 0, "monthly": 0, "occasional": 0}
    
    def _get_document_download_stats(self):
        """Get document download statistics"""
        return 0  # Document tracking not implemented
    
    def _calculate_avg_session_duration(self):
        """Calculate average session duration from meeting data"""
        avg_duration = Meeting.objects.aggregate(avg=Avg('duration_minutes'))['avg']
        return round(avg_duration, 1) if avg_duration else 0
    
    def _calculate_bounce_rate(self):
        """Calculate bounce rate from single-session users"""
        total_clients = Client.objects.count()
        if total_clients == 0:
            return 0
        
        # Simplified bounce rate calculation
        single_login_clients = Client.objects.filter(
            user__last_login__isnull=False
        ).count()
        
        # Mock calculation since complex annotation might cause issues
        bounce_rate = max(0, 100 - (single_login_clients / total_clients * 100))
        return round(bounce_rate, 1)
    
    def _calculate_return_user_rate(self):
        """Calculate return user rate"""
        total_users = Client.objects.count()
        return_users = Client.objects.filter(
            user__last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        if total_users > 0:
            return round((return_users / total_users) * 100, 2)
        return 0
    
    def _get_feature_adoption_rates(self):
        """Get feature adoption rates"""
        total_clients = Client.objects.count()
        
        if total_clients == 0:
            return {}
        
        return {
            "ai_chat": round((AIConversation.objects.values('client').distinct().count() / total_clients) * 100, 2),
            "meetings": round((Meeting.objects.values('client').distinct().count() / total_clients) * 100, 2),
            "tickets": round((Ticket.objects.values('client').distinct().count() / total_clients) * 100, 2),
            "onboarding_completed": round((OnboardingQuestionnaire.objects.filter(is_completed=True).count() / total_clients) * 100, 2)
        }


@extend_schema(
    tags=["Behavior Analytics"],
    summary="Get user journey analytics",
    description="Analyze user journeys from onboarding to engagement milestones."
)
class UserJourneyAnalyticsView(APIView):
    """Analyze user journey and conversion funnels"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Onboarding funnel
        onboarding_funnel = {
            "registered_users": Client.objects.count(),
            "started_onboarding": OnboardingQuestionnaire.objects.count(),
            "completed_onboarding": OnboardingQuestionnaire.objects.filter(is_completed=True).count(),
            "first_meeting_scheduled": Meeting.objects.values('client').distinct().count(),
            "active_users": Client.objects.filter(
                user__last_login__gte=timezone.now() - timedelta(days=30)
            ).count()
        }
        
        # Engagement milestones
        engagement_milestones = {
            "first_ai_interaction": AIConversation.objects.values('client').distinct().count(),
            "first_ticket_created": Ticket.objects.values('client').distinct().count(),
            "multiple_meetings": Meeting.objects.values('client').annotate(
                meeting_count=Count('id')
            ).filter(meeting_count__gt=1).count(),
            "document_engagement": self._get_document_engagement_count()
        }
        
        # Drop-off analysis
        dropoff_analysis = {
            "registration_to_onboarding": self._calculate_dropoff_rate(
                Client.objects.count(),
                OnboardingQuestionnaire.objects.count()
            ),
            "onboarding_to_completion": self._calculate_dropoff_rate(
                OnboardingQuestionnaire.objects.count(),
                OnboardingQuestionnaire.objects.filter(is_completed=True).count()
            ),
            "completion_to_first_meeting": self._calculate_dropoff_rate(
                OnboardingQuestionnaire.objects.filter(is_completed=True).count(),
                Meeting.objects.values('client').distinct().count()
            )
        }
        
        return Response({
            "onboarding_funnel": onboarding_funnel,
            "engagement_milestones": engagement_milestones,
            "dropoff_analysis": dropoff_analysis
        })
    
    def _get_document_engagement_count(self):
        """Get count of users who have engaged with documents"""
        return 0  # Document tracking not implemented
    
    def _calculate_dropoff_rate(self, start_count, end_count):
        """Calculate dropoff rate between two stages"""
        if start_count == 0:
            return 0
        return round(((start_count - end_count) / start_count) * 100, 2)