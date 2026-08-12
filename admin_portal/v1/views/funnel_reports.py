from datetime import datetime, timedelta
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import Client, Meeting, Ticket, AIConversation, Content
from client.models import OnboardingQuestionnaire, Activity
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Funnel Reports"],
    summary="Get conversion funnel analytics",
    description="Analyze conversion funnels from initial contact to client engagement and success milestones."
)
class ConversionFunnelAnalyticsView(APIView):
    """Conversion funnel analytics from contact to engagement"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Main conversion funnel
        main_funnel = self._get_main_conversion_funnel()
        
        # Engagement funnel
        engagement_funnel = self._get_engagement_funnel()
        
        # Success milestone funnel
        success_funnel = self._get_success_milestone_funnel()
        
        # Drop-off analysis
        dropoff_analysis = self._get_dropoff_analysis()
        

        
        return Response({
            "main_funnel": main_funnel,
            "engagement_funnel": engagement_funnel,
            "success_funnel": success_funnel,
            "dropoff_analysis": dropoff_analysis
        })
    
    def _get_main_conversion_funnel(self):
        """Get main conversion funnel from contact to client"""
        # Contact form submissions
        contact_submissions = Ticket.objects.count()
        
        # User registrations
        user_registrations = Client.objects.count()
        
        # Onboarding started
        onboarding_started = OnboardingQuestionnaire.objects.count()
        
        # Onboarding completed
        onboarding_completed = OnboardingQuestionnaire.objects.filter(
            is_completed=True
        ).count()
        
        # First engagement (any feature use)
        first_engagement = Client.objects.filter(
            Q(ai_conversations__isnull=False) |
            Q(meetings__isnull=False) |
            Q(tickets__isnull=False)
        ).distinct().count()
        
        # Active clients (used platform in last 30 days)
        active_clients = Client.objects.filter(
            user__last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return {
            "stages": [
                {
                    "stage": "Contact Form",
                    "count": contact_submissions,
                    "conversion_rate": 100.0
                },
                {
                    "stage": "Registration",
                    "count": user_registrations,
                    "conversion_rate": round((user_registrations / contact_submissions) * 100, 2) if contact_submissions > 0 else 0
                },
                {
                    "stage": "Onboarding Started",
                    "count": onboarding_started,
                    "conversion_rate": round((onboarding_started / user_registrations) * 100, 2) if user_registrations > 0 else 0
                },
                {
                    "stage": "Onboarding Completed",
                    "count": onboarding_completed,
                    "conversion_rate": round((onboarding_completed / onboarding_started) * 100, 2) if onboarding_started > 0 else 0
                },
                {
                    "stage": "First Engagement",
                    "count": first_engagement,
                    "conversion_rate": round((first_engagement / onboarding_completed) * 100, 2) if onboarding_completed > 0 else 0
                },
                {
                    "stage": "Active Client",
                    "count": active_clients,
                    "conversion_rate": round((active_clients / first_engagement) * 100, 2) if first_engagement > 0 else 0
                }
            ],
            "overall_conversion_rate": round((active_clients / contact_submissions) * 100, 2) if contact_submissions > 0 else 0
        }
    
    def _get_engagement_funnel(self):
        """Get engagement funnel for different features"""
        total_clients = Client.objects.count()
        
        # AI Chat engagement
        ai_chat_users = AIConversation.objects.values('client').distinct().count()
        ai_multiple_sessions = AIConversation.objects.values('client').annotate(
            session_count=Count('id')
        ).filter(session_count__gt=1).count()
        
        # Meeting engagement
        meeting_requesters = Meeting.objects.values('client').distinct().count()
        meeting_completers = Meeting.objects.filter(
            status='completed'
        ).values('client').distinct().count()
        
        # Support engagement
        ticket_creators = Ticket.objects.values('client').distinct().count()
        ticket_resolvers = Ticket.objects.filter(
            status='resolved'
        ).values('client').distinct().count()
        
        return {
            "ai_chat_funnel": {
                "total_clients": total_clients,
                "tried_ai_chat": ai_chat_users,
                "multiple_ai_sessions": ai_multiple_sessions,
                "conversion_rates": {
                    "trial_rate": round((ai_chat_users / total_clients) * 100, 2) if total_clients > 0 else 0,
                    "retention_rate": round((ai_multiple_sessions / ai_chat_users) * 100, 2) if ai_chat_users > 0 else 0
                }
            },
            "meeting_funnel": {
                "total_clients": total_clients,
                "requested_meeting": meeting_requesters,
                "completed_meeting": meeting_completers,
                "conversion_rates": {
                    "request_rate": round((meeting_requesters / total_clients) * 100, 2) if total_clients > 0 else 0,
                    "completion_rate": round((meeting_completers / meeting_requesters) * 100, 2) if meeting_requesters > 0 else 0
                }
            },
            "support_funnel": {
                "total_clients": total_clients,
                "created_ticket": ticket_creators,
                "resolved_ticket": ticket_resolvers,
                "conversion_rates": {
                    "creation_rate": round((ticket_creators / total_clients) * 100, 2) if total_clients > 0 else 0,
                    "resolution_rate": round((ticket_resolvers / ticket_creators) * 100, 2) if ticket_creators > 0 else 0
                }
            }
        }
    
    def _get_success_milestone_funnel(self):
        """Get success milestone funnel"""
        # Define success milestones
        onboarding_completed = OnboardingQuestionnaire.objects.filter(
            is_completed=True
        ).count()
        
        first_meeting_completed = Meeting.objects.filter(
            status='completed'
        ).values('client').distinct().count()
        
        multiple_engagements = Client.objects.filter(
            Q(ai_conversations__isnull=False) &
            Q(meetings__isnull=False)
        ).distinct().count()
        
        ongoing_relationship = Client.objects.filter(
            user__last_login__gte=timezone.now() - timedelta(days=7)
        ).filter(
            Q(meetings__status='completed') |
            Q(tickets__status='resolved')
        ).distinct().count()
        
        return {
            "milestones": [
                {
                    "milestone": "Onboarding Completed",
                    "count": onboarding_completed,
                    "percentage": 100.0
                },
                {
                    "milestone": "First Meeting Completed",
                    "count": first_meeting_completed,
                    "percentage": round((first_meeting_completed / onboarding_completed) * 100, 2) if onboarding_completed > 0 else 0
                },
                {
                    "milestone": "Multiple Engagements",
                    "count": multiple_engagements,
                    "percentage": round((multiple_engagements / first_meeting_completed) * 100, 2) if first_meeting_completed > 0 else 0
                },
                {
                    "milestone": "Ongoing Relationship",
                    "count": ongoing_relationship,
                    "percentage": round((ongoing_relationship / multiple_engagements) * 100, 2) if multiple_engagements > 0 else 0
                }
            ]
        }
    
    def _get_dropoff_analysis(self):
        """Analyze where users drop off in the funnel"""
        total_contacts = Ticket.objects.count()
        registrations = Client.objects.count()
        onboarding_starts = OnboardingQuestionnaire.objects.count()
        onboarding_completions = OnboardingQuestionnaire.objects.filter(is_completed=True).count()
        first_engagements = Client.objects.filter(
            Q(ai_conversations__isnull=False) |
            Q(meetings__isnull=False) |
            Q(tickets__isnull=False)
        ).distinct().count()
        
        return {
            "dropoff_points": [
                {
                    "stage": "Contact to Registration",
                    "dropoff_count": total_contacts - registrations,
                    "dropoff_rate": round(((total_contacts - registrations) / total_contacts) * 100, 2) if total_contacts > 0 else 0,
                    "potential_reasons": ["Complex registration process", "Unclear value proposition", "Technical issues"]
                },
                {
                    "stage": "Registration to Onboarding",
                    "dropoff_count": registrations - onboarding_starts,
                    "dropoff_rate": round(((registrations - onboarding_starts) / registrations) * 100, 2) if registrations > 0 else 0,
                    "potential_reasons": ["Onboarding not initiated", "Email verification issues", "Lost interest"]
                },
                {
                    "stage": "Onboarding Started to Completed",
                    "dropoff_count": onboarding_starts - onboarding_completions,
                    "dropoff_rate": round(((onboarding_starts - onboarding_completions) / onboarding_starts) * 100, 2) if onboarding_starts > 0 else 0,
                    "potential_reasons": ["Long questionnaire", "Unclear questions", "Time constraints"]
                },
                {
                    "stage": "Onboarding to First Engagement",
                    "dropoff_count": onboarding_completions - first_engagements,
                    "dropoff_rate": round(((onboarding_completions - first_engagements) / onboarding_completions) * 100, 2) if onboarding_completions > 0 else 0,
                    "potential_reasons": ["Unclear next steps", "Feature discovery issues", "Lack of immediate value"]
                }
            ]
        }
    



@extend_schema(
    tags=["Funnel Reports"],
    summary="Get time-based funnel analysis",
    description="Analyze conversion funnels over different time periods and identify trends."
)
class TimeBasedFunnelAnalysisView(APIView):
    """Time-based funnel analysis and trends"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Monthly funnel performance
        monthly_funnel = self._get_monthly_funnel_performance()
        
        # Cohort analysis
        cohort_analysis = self._get_cohort_analysis()
        
        # Seasonal trends
        seasonal_trends = self._get_seasonal_trends()
        
        return Response({
            "monthly_funnel": monthly_funnel,
            "cohort_analysis": cohort_analysis,
            "seasonal_trends": seasonal_trends
        })
    
    def _get_monthly_funnel_performance(self):
        """Get funnel performance by month"""
        now = timezone.now()
        monthly_data = []
        
        for i in range(6):  # Last 6 months
            month_start = (now - timedelta(days=30 * i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            contacts = Ticket.objects.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            ).count()
            
            registrations = Client.objects.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            ).count()
            
            onboarding_completed = OnboardingQuestionnaire.objects.filter(
                created_at__gte=month_start,
                created_at__lte=month_end,
                is_completed=True
            ).count()
            
            first_engagements = Client.objects.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            ).filter(
                Q(ai_conversations__isnull=False) |
                Q(meetings__isnull=False) |
                Q(tickets__isnull=False)
            ).distinct().count()
            
            monthly_data.append({
                "month": month_start.strftime("%Y-%m"),
                "contacts": contacts,
                "registrations": registrations,
                "onboarding_completed": onboarding_completed,
                "first_engagements": first_engagements,
                "contact_to_registration_rate": round((registrations / contacts) * 100, 2) if contacts > 0 else 0,
                "registration_to_engagement_rate": round((first_engagements / registrations) * 100, 2) if registrations > 0 else 0
            })
        
        return monthly_data
    
    def _get_cohort_analysis(self):
        """Get cohort analysis for user retention"""
        # Simplified cohort analysis - would need more sophisticated tracking
        cohorts = []
        
        for i in range(6):  # Last 6 months
            cohort_month = (timezone.now() - timedelta(days=30 * i)).replace(day=1)
            cohort_users = Client.objects.filter(
                created_at__gte=cohort_month,
                created_at__lt=cohort_month + timedelta(days=32)
            )
            
            total_users = cohort_users.count()
            if total_users == 0:
                continue
            
            # Calculate retention for subsequent months
            retention_data = []
            for j in range(6 - i):  # Remaining months
                retention_month = cohort_month + timedelta(days=30 * (j + 1))
                retained_users = cohort_users.filter(
                    user__last_login__gte=retention_month,
                    user__last_login__lt=retention_month + timedelta(days=30)
                ).count()
                
                retention_rate = round((retained_users / total_users) * 100, 2)
                retention_data.append({
                    "month": j + 1,
                    "retention_rate": retention_rate
                })
            
            cohorts.append({
                "cohort_month": cohort_month.strftime("%Y-%m"),
                "total_users": total_users,
                "retention_data": retention_data
            })
        
        return cohorts
    
    def _get_seasonal_trends(self):
        """Get seasonal trends in conversion"""
        # Analyze quarterly performance
        now = timezone.now()
        quarterly_data = []
        
        for i in range(4):  # Last 4 quarters
            quarter_start = now - timedelta(days=90 * (i + 1))
            quarter_end = now - timedelta(days=90 * i)
            
            contacts = Ticket.objects.filter(
                created_at__gte=quarter_start,
                created_at__lt=quarter_end
            ).count()
            
            conversions = Client.objects.filter(
                created_at__gte=quarter_start,
                created_at__lt=quarter_end
            ).filter(
                Q(ai_conversations__isnull=False) |
                Q(meetings__isnull=False)
            ).distinct().count()
            
            quarterly_data.append({
                "quarter": f"Q{4-i} {quarter_start.year}",
                "contacts": contacts,
                "conversions": conversions,
                "conversion_rate": round((conversions / contacts) * 100, 2) if contacts > 0 else 0
            })
        
        return quarterly_data
    
