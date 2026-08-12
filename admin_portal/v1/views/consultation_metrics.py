from datetime import datetime, timedelta
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import Client, Meeting, Ticket, AIConversation
from client.models import OnboardingQuestionnaire
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Consultation Metrics"],
    summary="Get consultation performance metrics",
    description="Analyze consultation performance including meeting statistics, conversion rates, and client satisfaction."
)
class ConsultationPerformanceView(APIView):
    """Consultation performance metrics and analytics"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_90_days = now - timedelta(days=90)
        
        # Meeting statistics
        meeting_stats = {
            "total_meetings": Meeting.objects.count(),
            "meetings_this_month": Meeting.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            "completed_meetings": Meeting.objects.filter(
                status='completed'
            ).count(),
            "meeting_types_distribution": dict(
                Meeting.objects.values('meeting_type')
                .annotate(count=Count('id'))
                .values_list('meeting_type', 'count')
            ),
            "avg_meeting_duration": self._calculate_avg_meeting_duration(),
            "meeting_completion_rate": self._calculate_meeting_completion_rate()
        }
        
        # Consultation conversion metrics
        conversion_metrics = {
            "inquiry_to_meeting_rate": self._calculate_inquiry_to_meeting_rate(),
            "meeting_to_engagement_rate": self._calculate_meeting_to_engagement_rate(),
            "repeat_consultation_rate": self._calculate_repeat_consultation_rate(),
            "escalation_to_consultation_rate": self._calculate_escalation_rate()
        }
        
        # Client satisfaction indicators
        satisfaction_indicators = {
            "meeting_feedback_score": self._get_meeting_feedback_score(),
            "follow_up_meeting_requests": Meeting.objects.filter(
                meeting_type='follow_up',
                created_at__gte=last_30_days
            ).count(),
            "client_retention_post_meeting": self._calculate_client_retention_post_meeting(),
            "no_show_rate": self._calculate_no_show_rate()
        }
        
        # Consultant performance
        consultant_performance = self._get_consultant_performance_metrics()
        
        return Response({
            "meeting_statistics": meeting_stats,
            "conversion_metrics": conversion_metrics,
            "satisfaction_indicators": satisfaction_indicators,
            "consultant_performance": consultant_performance
        })
    
    def _calculate_avg_meeting_duration(self):
        """Calculate average meeting duration"""
        # Using the duration_minutes field from Meeting model
        avg_duration = Meeting.objects.aggregate(
            avg_duration=Avg('duration_minutes')
        )['avg_duration']
        return round(avg_duration, 2) if avg_duration else 60
    
    def _calculate_meeting_completion_rate(self):
        """Calculate meeting completion rate"""
        total_meetings = Meeting.objects.count()
        completed_meetings = Meeting.objects.filter(status='completed').count()
        
        if total_meetings > 0:
            return round((completed_meetings / total_meetings) * 100, 2)
        return 0
    
    def _calculate_inquiry_to_meeting_rate(self):
        """Calculate rate from initial inquiry to scheduled meeting"""
        total_clients = Client.objects.count()
        clients_with_meetings = Meeting.objects.values('client').distinct().count()
        
        if total_clients > 0:
            return round((clients_with_meetings / total_clients) * 100, 2)
        return 0
    
    def _calculate_meeting_to_engagement_rate(self):
        """Calculate rate from meeting to ongoing engagement"""
        clients_with_meetings = Meeting.objects.values('client').distinct().count()
        clients_with_multiple_touchpoints = Client.objects.filter(
            Q(meetings__isnull=False) & 
            (Q(tickets__isnull=False) | Q(ai_conversations__isnull=False))
        ).distinct().count()
        
        if clients_with_meetings > 0:
            return round((clients_with_multiple_touchpoints / clients_with_meetings) * 100, 2)
        return 0
    
    def _calculate_repeat_consultation_rate(self):
        """Calculate rate of clients who schedule multiple meetings"""
        clients_with_meetings = Meeting.objects.values('client').distinct().count()
        clients_with_multiple_meetings = Meeting.objects.values('client').annotate(
            meeting_count=Count('id')
        ).filter(meeting_count__gt=1).count()
        
        if clients_with_meetings > 0:
            return round((clients_with_multiple_meetings / clients_with_meetings) * 100, 2)
        return 0
    
    def _calculate_escalation_rate(self):
        """Calculate rate of AI conversations escalated to meetings"""
        total_conversations = AIConversation.objects.count()
        escalated_to_meetings = AIConversation.objects.filter(
            client__meetings__isnull=False
        ).distinct().count()
        
        if total_conversations > 0:
            return round((escalated_to_meetings / total_conversations) * 100, 2)
        return 0
    
    def _get_meeting_feedback_score(self):
        """Get average meeting feedback score"""
        # No feedback system implemented yet
        return 0
    
    def _calculate_client_retention_post_meeting(self):
        """Calculate client retention rate after meetings"""
        clients_with_meetings = Meeting.objects.filter(
            status='completed',
            confirmed_datetime__lte=timezone.now() - timedelta(days=30)
        ).values('client').distinct()
        
        retained_clients = Client.objects.filter(
            id__in=clients_with_meetings,
            user__last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        total_clients_with_meetings = clients_with_meetings.count()
        
        if total_clients_with_meetings > 0:
            return round((retained_clients / total_clients_with_meetings) * 100, 2)
        return 0
    
    def _calculate_no_show_rate(self):
        """Calculate no-show rate for meetings"""
        total_confirmed_meetings = Meeting.objects.filter(status='confirmed').count()
        cancelled_meetings = Meeting.objects.filter(status='cancelled').count()
        
        if total_confirmed_meetings > 0:
            return round((cancelled_meetings / total_confirmed_meetings) * 100, 2)
        return 0
    
    def _get_consultant_performance_metrics(self):
        """Get performance metrics by consultant"""
        try:
            from django.contrib.auth.models import User
            
            consultants = User.objects.filter(
                hosted_meetings__isnull=False
            ).distinct()
            
            performance_data = []
            
            for consultant in consultants:
                try:
                    meetings_hosted = Meeting.objects.filter(host=consultant).count()
                    completed_meetings = Meeting.objects.filter(
                        host=consultant, status='completed'
                    ).count()
                    
                    performance_data.append({
                        "consultant_name": consultant.get_full_name() or consultant.username,
                        "meetings_hosted": meetings_hosted,
                        "completion_rate": round((completed_meetings / meetings_hosted) * 100, 2) if meetings_hosted > 0 else 0,
                        "avg_rating": 0,  # No rating system implemented
                        "client_satisfaction": 0  # No satisfaction tracking implemented
                    })
                except Exception:
                    continue
            
            return performance_data
        except Exception:
            return []


@extend_schema(
    tags=["Consultation Metrics"],
    summary="Get consultation scheduling analytics",
    description="Analyze consultation scheduling patterns, availability, and optimization opportunities."
)
class ConsultationSchedulingAnalyticsView(APIView):
    """Consultation scheduling analytics and optimization"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Scheduling patterns
        scheduling_patterns = {
            "peak_request_hours": self._get_peak_request_hours(),
            "peak_request_days": self._get_peak_request_days(),
            "avg_lead_time": self._calculate_avg_lead_time(),
            "rescheduling_rate": self._calculate_rescheduling_rate()
        }
        
        # Availability analysis
        availability_analysis = {
            "consultant_utilization": self._get_consultant_utilization(),
            "time_slot_popularity": self._get_time_slot_popularity(),
            "capacity_vs_demand": self._analyze_capacity_vs_demand()
        }
        
        # Optimization opportunities
        optimization_opportunities = {
            "underutilized_slots": self._identify_underutilized_slots(),
            "high_demand_periods": self._identify_high_demand_periods(),
            "suggested_capacity_adjustments": self._suggest_capacity_adjustments()
        }
        
        return Response({
            "scheduling_patterns": scheduling_patterns,
            "availability_analysis": availability_analysis,
            "optimization_opportunities": optimization_opportunities
        })
    
    def _get_peak_request_hours(self):
        """Get peak hours for meeting requests from actual data"""
        try:
            from django.db.models import Extract
            
            meeting_hours = Meeting.objects.filter(
                created_at__isnull=False
            ).annotate(
                hour=Extract('created_at', 'hour')
            ).values('hour').annotate(count=Count('id'))
            
            hourly_data = {}
            for item in meeting_hours:
                hour = item.get('hour')
                count = item.get('count', 0)
                if hour is not None:
                    hour_range = f"{hour}-{hour+1}"
                    hourly_data[hour_range] = count
            
            return hourly_data
        except Exception:
            return {}
    
    def _get_peak_request_days(self):
        """Get peak days for meeting requests from actual data"""
        try:
            from django.db.models import Extract
            
            meeting_days = Meeting.objects.filter(
                created_at__isnull=False
            ).annotate(
                weekday=Extract('created_at', 'week_day')
            ).values('weekday').annotate(count=Count('id'))
            
            day_names = {1: 'sunday', 2: 'monday', 3: 'tuesday', 4: 'wednesday', 5: 'thursday', 6: 'friday', 7: 'saturday'}
            daily_data = {}
            
            for item in meeting_days:
                weekday = item.get('weekday')
                count = item.get('count', 0)
                if weekday is not None:
                    day_name = day_names.get(weekday, 'unknown')
                    daily_data[day_name] = count
            
            return daily_data
        except Exception:
            return {}
    
    def _calculate_avg_lead_time(self):
        """Calculate average lead time from request to meeting"""
        try:
            meetings_with_lead_time = Meeting.objects.filter(
                requested_datetime__isnull=False,
                confirmed_datetime__isnull=False
            )
            
            if meetings_with_lead_time.exists():
                total_days = 0
                valid_meetings = 0
                
                for meeting in meetings_with_lead_time:
                    try:
                        if meeting.confirmed_datetime and meeting.requested_datetime:
                            days_diff = (meeting.confirmed_datetime.date() - meeting.requested_datetime.date()).days
                            if days_diff >= 0:  # Only count positive lead times
                                total_days += days_diff
                                valid_meetings += 1
                    except Exception:
                        continue
                
                return round(total_days / valid_meetings, 1) if valid_meetings > 0 else 0
            return 0
        except Exception:
            return 0
    
    def _calculate_rescheduling_rate(self):
        """Calculate meeting rescheduling rate"""
        total_meetings = Meeting.objects.count()
        rescheduled_meetings = Meeting.objects.filter(status='rescheduled').count()
        
        if total_meetings > 0:
            return round((rescheduled_meetings / total_meetings) * 100, 2)
        return 0
    
    def _get_consultant_utilization(self):
        """Get consultant utilization rates"""
        try:
            from django.contrib.auth.models import User
            
            consultants = User.objects.filter(hosted_meetings__isnull=False).distinct()
            utilization_data = []
            
            for consultant in consultants:
                try:
                    meetings_this_month = Meeting.objects.filter(
                        host=consultant,
                        created_at__gte=timezone.now() - timedelta(days=30)
                    ).count()
                    
                    # Assuming 20 working days per month, 8 hours per day, 1-hour meetings
                    max_capacity = 20 * 8  # 160 meetings per month max
                    utilization_rate = round((meetings_this_month / max_capacity) * 100, 2) if max_capacity > 0 else 0
                    
                    utilization_data.append({
                        "consultant": consultant.get_full_name() or consultant.username,
                        "meetings_this_month": meetings_this_month,
                        "utilization_rate": min(utilization_rate, 100)  # Cap at 100%
                    })
                except Exception:
                    continue
            
            return utilization_data
        except Exception:
            return []
    
    def _get_time_slot_popularity(self):
        """Get popularity of different time slots from actual data"""
        try:
            from django.db.models import Extract
            
            meeting_hours = Meeting.objects.filter(
                confirmed_datetime__isnull=False
            ).annotate(
                hour=Extract('confirmed_datetime', 'hour')
            ).values('hour').annotate(count=Count('id'))
            
            periods = {"morning": 0, "afternoon": 0, "evening": 0}
            total_meetings = sum(item['count'] for item in meeting_hours)
            
            for item in meeting_hours:
                hour = item.get('hour')
                count = item.get('count', 0)
                
                if hour is not None:
                    if 6 <= hour < 12:
                        periods["morning"] += count
                    elif 12 <= hour < 18:
                        periods["afternoon"] += count
                    else:
                        periods["evening"] += count
            
            if total_meetings > 0:
                for period in periods:
                    periods[period] = round((periods[period] / total_meetings) * 100, 1)
            
            return periods
        except Exception:
            return {"morning": 0, "afternoon": 0, "evening": 0}
    
    def _analyze_capacity_vs_demand(self):
        """Analyze capacity vs demand patterns from actual data"""
        try:
            last_30_days = timezone.now() - timedelta(days=30)
            
            current_demand = Meeting.objects.filter(
                created_at__gte=last_30_days
            ).count()
            
            # Estimate capacity based on available consultants
            from django.contrib.auth.models import User
            consultants_count = User.objects.filter(hosted_meetings__isnull=False).distinct().count()
            estimated_capacity = max(1, consultants_count * 20 * 8)  # 20 days * 8 hours per consultant, minimum 1
            
            utilization_rate = round((current_demand / estimated_capacity) * 100, 1) if estimated_capacity > 0 else 0
            capacity_gap = max(0, estimated_capacity - current_demand)
            
            return {
                "current_capacity": estimated_capacity,
                "current_demand": current_demand,
                "utilization_rate": utilization_rate,
                "capacity_gap": capacity_gap
            }
        except Exception:
            return {
                "current_capacity": 160,
                "current_demand": 0,
                "utilization_rate": 0,
                "capacity_gap": 160
            }
    
    def _identify_underutilized_slots(self):
        """Identify underutilized time slots from actual data"""
        try:
            from django.db.models import Extract
            
            # Get meeting distribution by hour
            meeting_hours = Meeting.objects.filter(
                confirmed_datetime__isnull=False
            ).annotate(
                hour=Extract('confirmed_datetime', 'hour')
            ).values('hour').annotate(count=Count('id'))
            
            total_meetings = sum(item['count'] for item in meeting_hours)
            underutilized = []
            
            for item in meeting_hours:
                hour = item.get('hour')
                count = item.get('count', 0)
                
                if hour is not None and total_meetings > 0:
                    utilization = round((count / total_meetings) * 100, 1)
                    if utilization < 5:  # Less than 5% utilization
                        underutilized.append({
                            "time": f"{hour:02d}:00-{hour+1:02d}:00",
                            "utilization": utilization
                        })
            
            return underutilized[:5]  # Return top 5
        except Exception:
            return []
    
    def _identify_high_demand_periods(self):
        """Identify high demand periods from actual data"""
        try:
            from django.db.models import Extract
            
            # Get meeting distribution by day and hour
            meeting_patterns = Meeting.objects.filter(
                confirmed_datetime__isnull=False
            ).annotate(
                weekday=Extract('confirmed_datetime', 'week_day'),
                hour=Extract('confirmed_datetime', 'hour')
            ).values('weekday', 'hour').annotate(count=Count('id')).order_by('-count')
            
            day_names = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday', 5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
            high_demand = []
            
            total_meetings = Meeting.objects.count()
            
            for pattern in meeting_patterns[:5]:  # Top 5 high demand periods
                weekday = pattern.get('weekday')
                hour = pattern.get('hour')
                count = pattern.get('count', 0)
                
                if weekday is not None and hour is not None and total_meetings > 0:
                    day_name = day_names.get(weekday, 'Unknown')
                    demand_score = round((count / total_meetings) * 100, 1)
                    
                    high_demand.append({
                        "period": f"{day_name} {hour:02d}:00-{hour+1:02d}:00",
                        "demand_score": demand_score
                    })
            
            return high_demand
        except Exception:
            return []
    
    def _suggest_capacity_adjustments(self):
        """Suggest capacity adjustments based on actual data"""
        suggestions = []
        
        # Analyze current utilization
        capacity_data = self._analyze_capacity_vs_demand()
        
        if capacity_data['utilization_rate'] > 80:
            suggestions.append({
                "suggestion": "Consider adding more consultant availability",
                "impact": f"Current utilization at {capacity_data['utilization_rate']}%"
            })
        
        if capacity_data['utilization_rate'] < 50:
            suggestions.append({
                "suggestion": "Optimize consultant schedules",
                "impact": f"Current utilization only {capacity_data['utilization_rate']}%"
            })
        
        # Check for underutilized periods
        underutilized = self._identify_underutilized_slots()
        if underutilized:
            suggestions.append({
                "suggestion": "Promote availability during low-demand hours",
                "impact": f"Could better utilize {len(underutilized)} time slots"
            })
        
        return suggestions if suggestions else [{
            "suggestion": "Current capacity appears well-balanced",
            "impact": "No immediate adjustments needed"
        }]