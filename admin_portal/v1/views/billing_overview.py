from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum, Avg, F
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from payment.models import Invoice, Subscription, PricingPlan
from admin_portal.models import Client
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Billing Overview"],
    summary="Get comprehensive billing overview",
    description="Financial dashboard with revenue, subscriptions, and payment analytics."
)
class BillingOverviewView(APIView):
    """Comprehensive billing and financial overview"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        user_role = request.user.admin_profile.role
        if user_role.name != "super_admin":
            return Response({"error": "Insufficient permissions. Only Super Admins can view overall platform billing metrics."}, status=403)

        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_90_days = now - timedelta(days=90)
        
        # Revenue metrics
        revenue_metrics = {
            "total_revenue": self._get_total_revenue(),
            "monthly_revenue": self._get_monthly_revenue(),
            "revenue_growth": self._calculate_revenue_growth(),
            "average_revenue_per_user": self._calculate_arpu(),
            "monthly_recurring_revenue": self._calculate_mrr(),
            "annual_recurring_revenue": self._calculate_arr()
        }
        
        # Subscription metrics
        subscription_metrics = {
            "total_subscriptions": Subscription.objects.count(),
            "active_subscriptions": Subscription.objects.filter(is_active=True).count(),
            "inactive_subscriptions": Subscription.objects.filter(is_active=False).count(),
            "subscription_growth": self._calculate_subscription_growth(),
            "churn_rate": self._calculate_churn_rate(),
            "retention_rate": self._calculate_retention_rate()
        }
        
        # Payment metrics
        payment_metrics = {
            "total_transactions": Invoice.objects.count(),
            "successful_payments": Invoice.objects.filter(
                Q(status__icontains='paid') | Q(status__icontains='Paid')
            ).count(),
            "failed_payments": Invoice.objects.filter(
                Q(status__icontains='failed') | Q(status__icontains='Failed')
            ).count(),
            "pending_payments": Invoice.objects.filter(
                Q(status__icontains='pending') | Q(status__icontains='Pending')
            ).count(),
            "payment_success_rate": self._calculate_payment_success_rate(),
            "average_transaction_value": self._calculate_avg_transaction_value()
        }
        
        # Financial trends
        financial_trends = {
            "revenue_by_month": self._get_revenue_by_month(),
            "subscription_trends": self._get_subscription_trends(),
            "payment_volume_trends": self._get_payment_volume_trends()
        }
        
        # Top customers
        top_customers = self._get_top_customers()
        
        return Response({
            "revenue_metrics": revenue_metrics,
            "subscription_metrics": subscription_metrics,
            "payment_metrics": payment_metrics,
            "financial_trends": financial_trends,
            "top_customers": top_customers
        })
    
    def _get_total_revenue(self):
        """Calculate total revenue from paid invoices"""
        return float(Invoice.objects.filter(
            Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete')
        ).aggregate(total=Sum('amount'))['total'] or 0)
    
    def _get_monthly_revenue(self):
        """Calculate revenue for current month"""
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return float(Invoice.objects.filter(
            Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete'),
            created_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0)
    
    def _calculate_revenue_growth(self):
        """Calculate month-over-month revenue growth"""
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Previous month
        if current_month_start.month == 1:
            prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
        else:
            prev_month_start = current_month_start.replace(month=current_month_start.month - 1)
        
        current_revenue = float(Invoice.objects.filter(
            Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete'),
            created_at__gte=current_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0)
        
        prev_revenue = float(Invoice.objects.filter(
            Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete'),
            created_at__gte=prev_month_start,
            created_at__lt=current_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0)
        
        if prev_revenue > 0:
            return round(((current_revenue - prev_revenue) / prev_revenue) * 100, 2)
        return 0
    
    def _calculate_arpu(self):
        """Calculate Average Revenue Per User"""
        total_revenue = self._get_total_revenue()
        total_users = Invoice.objects.values('user').distinct().count()
        
        if total_users > 0:
            return round(total_revenue / total_users, 2)
        return 0
    
    def _calculate_mrr(self):
        """Calculate Monthly Recurring Revenue"""
        active_subscriptions = Subscription.objects.filter(is_active=True)
        
        # Get recent invoices to estimate monthly revenue
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_revenue = float(Invoice.objects.filter(
            Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete'),
            created_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0)
        
        return monthly_revenue
    
    def _calculate_arr(self):
        """Calculate Annual Recurring Revenue"""
        return self._calculate_mrr() * 12
    
    def _calculate_subscription_growth(self):
        """Calculate subscription growth rate"""
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_60_days = now - timedelta(days=60)
        
        current_period = Subscription.objects.filter(
            created_at__gte=last_30_days
        ).count()
        
        previous_period = Subscription.objects.filter(
            created_at__gte=last_60_days,
            created_at__lt=last_30_days
        ).count()
        
        if previous_period > 0:
            return round(((current_period - previous_period) / previous_period) * 100, 2)
        return 0
    
    def _calculate_churn_rate(self):
        """Calculate customer churn rate"""
        total_subscriptions = Subscription.objects.count()
        inactive_subscriptions = Subscription.objects.filter(is_active=False).count()
        
        if total_subscriptions > 0:
            return round((inactive_subscriptions / total_subscriptions) * 100, 2)
        return 0
    
    def _calculate_retention_rate(self):
        """Calculate customer retention rate"""
        return round(100 - self._calculate_churn_rate(), 2)
    
    def _calculate_payment_success_rate(self):
        """Calculate payment success rate"""
        total_payments = Invoice.objects.count()
        successful_payments = Invoice.objects.filter(
            Q(status__icontains='paid') | Q(status__icontains='Paid')
        ).count()
        
        if total_payments > 0:
            return round((successful_payments / total_payments) * 100, 2)
        return 0
    
    def _calculate_avg_transaction_value(self):
        """Calculate average transaction value"""
        avg_value = Invoice.objects.filter(
            Q(status__icontains='paid') | Q(status__icontains='Paid')
        ).aggregate(avg=Avg('amount'))['avg']
        
        return round(float(avg_value), 2) if avg_value else 0
    
    def _get_revenue_by_month(self):
        """Get revenue breakdown by month for last 12 months"""
        now = timezone.now()
        monthly_data = []
        
        for i in range(12):
            month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
            
            revenue = float(Invoice.objects.filter(
                Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete'),
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0)
            
            monthly_data.append({
                "month": month_start.strftime("%Y-%m"),
                "revenue": revenue,
                "transactions": Invoice.objects.filter(
                    created_at__gte=month_start,
                    created_at__lte=month_end
                ).count()
            })
        
        return monthly_data
    
    def _get_subscription_trends(self):
        """Get subscription trends over time"""
        now = timezone.now()
        trends = []
        
        for i in range(6):  # Last 6 months
            month_start = (now - timedelta(days=30 * i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            new_subscriptions = Subscription.objects.filter(
                created_at__gte=month_start,
                created_at__lte=month_end
            ).count()
            
            cancelled_subscriptions = Subscription.objects.filter(
                updated_at__gte=month_start,
                updated_at__lte=month_end,
                is_active=False
            ).count()
            
            trends.append({
                "month": month_start.strftime("%Y-%m"),
                "new_subscriptions": new_subscriptions,
                "cancelled_subscriptions": cancelled_subscriptions,
                "net_growth": new_subscriptions - cancelled_subscriptions
            })
        
        return trends
    
    def _get_payment_volume_trends(self):
        """Get payment volume trends"""
        now = timezone.now()
        trends = []
        
        for i in range(30):  # Last 30 days
            date = (now - timedelta(days=i)).date()
            
            daily_volume = float(Invoice.objects.filter(
                Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete'),
                created_at__date=date
            ).aggregate(total=Sum('amount'))['total'] or 0)
            
            daily_count = Invoice.objects.filter(
                created_at__date=date
            ).count()
            
            trends.append({
                "date": date.isoformat(),
                "volume": daily_volume,
                "transaction_count": daily_count
            })
        
        return trends
    
    def _get_top_customers(self):
        """Get top customers by revenue"""
        top_customers = Invoice.objects.filter(
            Q(status__icontains='paid') | Q(status__icontains='Paid')
        ).values('user__email', 'user__first_name', 'user__last_name').annotate(
            total_revenue=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-total_revenue')[:10]
        
        customers = []
        for customer in top_customers:
            # Sane name resolution for top customers
            display_name = f"{customer['user__first_name']} {customer['user__last_name']}".strip()
            if not display_name or display_name.upper() == "N/A":
                display_name = customer['user__email'].split('@')[0] if customer['user__email'] else "Client"

            customers.append({
                "email": customer['user__email'],
                "name": display_name,
                "total_revenue": float(customer['total_revenue']),
                "transaction_count": customer['transaction_count']
            })
        
        return customers


@extend_schema(
    tags=["Billing Overview"],
    summary="Get subscription analytics",
    description="Detailed subscription metrics and plan performance."
)
class SubscriptionAnalyticsView(APIView):
    """Subscription-specific analytics"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Plan distribution
        plan_distribution = dict(
            Subscription.objects.values('plan_name')
            .annotate(count=Count('id'))
            .values_list('plan_name', 'count')
        )
        
        # Plan revenue
        plan_revenue = self._get_plan_revenue()
        
        # Subscription lifecycle
        lifecycle_metrics = {
            "average_subscription_length": self._calculate_avg_subscription_length(),
            "subscription_renewal_rate": self._calculate_renewal_rate(),
            "upgrade_rate": self._calculate_upgrade_rate(),
            "downgrade_rate": self._calculate_downgrade_rate()
        }
        
        # Cohort analysis
        cohort_analysis = self._get_subscription_cohorts()
        
        return Response({
            "plan_distribution": plan_distribution,
            "plan_revenue": plan_revenue,
            "lifecycle_metrics": lifecycle_metrics,
            "cohort_analysis": cohort_analysis
        })
    
    def _get_plan_revenue(self):
        """Get revenue by subscription plan"""
        plan_revenue = {}
        
        plans = Subscription.objects.values('plan_name').distinct()
        
        for plan in plans:
            plan_name = plan['plan_name']
            revenue = float(Invoice.objects.filter(
                Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete'),
                plan=plan_name
            ).aggregate(total=Sum('amount'))['total'] or 0)
            
            plan_revenue[plan_name] = revenue
        
        return plan_revenue
    
    def _calculate_avg_subscription_length(self):
        """Calculate average subscription length in days"""
        active_subscriptions = Subscription.objects.filter(is_active=True)
        
        if active_subscriptions.exists():
            total_days = sum([
                (timezone.now().date() - sub.created_at.date()).days
                for sub in active_subscriptions
            ])
            return round(total_days / active_subscriptions.count(), 1)
        return 0
    
    def _calculate_renewal_rate(self):
        """Calculate subscription renewal rate"""
        # Simplified calculation based on active vs inactive subscriptions
        total_subscriptions = Subscription.objects.count()
        active_subscriptions = Subscription.objects.filter(is_active=True).count()
        
        if total_subscriptions > 0:
            return round((active_subscriptions / total_subscriptions) * 100, 2)
        return 0
    
    def _calculate_upgrade_rate(self):
        """Calculate plan upgrade rate"""
        # This would require tracking plan changes - simplified for now
        return 0  # Would need plan change history
    
    def _calculate_downgrade_rate(self):
        """Calculate plan downgrade rate"""
        # This would require tracking plan changes - simplified for now
        return 0  # Would need plan change history
    
    def _get_subscription_cohorts(self):
        """Get subscription cohort analysis"""
        cohorts = []
        
        for i in range(6):  # Last 6 months
            cohort_month = (timezone.now() - timedelta(days=30 * i)).replace(day=1)
            cohort_subscriptions = Subscription.objects.filter(
                created_at__gte=cohort_month,
                created_at__lt=cohort_month + timedelta(days=32)
            )
            
            total_cohort = cohort_subscriptions.count()
            if total_cohort == 0:
                continue
            
            # Calculate retention for subsequent months
            retention_data = []
            for j in range(6 - i):  # Remaining months
                retention_month = cohort_month + timedelta(days=30 * (j + 1))
                retained = cohort_subscriptions.filter(
                    Q(is_active=True) | Q(updated_at__gte=retention_month)
                ).count()
                
                retention_rate = round((retained / total_cohort) * 100, 2)
                retention_data.append({
                    "month": j + 1,
                    "retention_rate": retention_rate
                })
            
            cohorts.append({
                "cohort_month": cohort_month.strftime("%Y-%m"),
                "total_subscriptions": total_cohort,
                "retention_data": retention_data
            })
        
        return cohorts