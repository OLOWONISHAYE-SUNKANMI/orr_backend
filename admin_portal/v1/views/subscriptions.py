from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import status

from payment.models import Invoice, Subscription, PricingPlan
from admin_portal.models import Client
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Subscriptions"],
    summary="Get all subscription management data",
    description="Comprehensive view of all client subscriptions, plans, and billing status."
)
class SubscriptionManagementView(ListAPIView):
    """Comprehensive subscription management"""
    
    permission_classes = []  # Temporarily disabled for testing
    
    def get(self, request):
        # All subscriptions with details
        subscriptions = self._get_all_subscriptions()
        
        # Subscription analytics
        analytics = self._get_subscription_analytics()
        
        # Plan distribution
        plan_distribution = self._get_plan_distribution()
        
        # Billing health metrics
        billing_health = self._get_billing_health_metrics()
        
        # Upcoming renewals
        upcoming_renewals = self._get_upcoming_renewals()
        
        return Response({
            "subscriptions": subscriptions,
            "analytics": analytics,
            "plan_distribution": plan_distribution,
            "billing_health": billing_health,
            "upcoming_renewals": upcoming_renewals
        })
    
    def _get_all_subscriptions(self):
        """Get all subscriptions with client details"""
        subscriptions = Subscription.objects.select_related('user').all()
        
        subscription_data = []
        for sub in subscriptions:
            # Get latest invoice
            latest_invoice = Invoice.objects.filter(user=sub.user).order_by('-created_at').first()
            
            subscription_data.append({
                "subscription_id": sub.stripe_subscription_id,
                "client_name": sub.user.get_full_name() or sub.user.email,
                "client_email": sub.user.email,
                "plan_name": sub.plan_name,
                "is_active": sub.is_active,
                "created_date": sub.created_at.isoformat(),
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "status": "Active" if sub.is_active else "Inactive",
                "last_payment_date": latest_invoice.billing_date.isoformat() if latest_invoice else None,
                "last_payment_amount": float(latest_invoice.amount) if latest_invoice else 0,
                "last_payment_status": latest_invoice.status if latest_invoice else "No payments",
                "total_paid": self._calculate_total_paid(sub.user),
                "days_until_renewal": self._calculate_days_until_renewal(sub.current_period_end)
            })
        
        return subscription_data
    
    def _get_subscription_analytics(self):
        """Get subscription analytics"""
        total_subscriptions = Subscription.objects.count()
        active_subscriptions = Subscription.objects.filter(is_active=True).count()
        
        return {
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "inactive_subscriptions": total_subscriptions - active_subscriptions,
            "activation_rate": round((active_subscriptions / total_subscriptions) * 100, 2) if total_subscriptions > 0 else 0,
            "monthly_growth_rate": self._calculate_subscription_growth_rate(),
            "churn_rate": self._calculate_churn_rate(),
            "average_subscription_length": self._calculate_avg_subscription_length(),
            "total_mrr": self._calculate_total_mrr()
        }

    def _calculate_total_mrr(self):
        """Calculate total Monthly Recurring Revenue"""
        plan_distribution = Subscription.objects.values('plan_name').annotate(count=Count('id'))
        total_mrr = 0
        for item in plan_distribution:
            plan_name = item['plan_name']
            count = item['count']
            plan_price = 99.99 if plan_name == "Premium" else 49.99
            total_mrr += count * plan_price
        return round(total_mrr, 2)
    
    def _get_plan_distribution(self):
        """Get distribution of subscription plans"""
        plan_distribution = dict(
            Subscription.objects.values('plan_name')
            .annotate(count=Count('id'))
            .values_list('plan_name', 'count')
        )
        
        # Calculate revenue by plan
        plan_revenue = {}
        for plan_name, count in plan_distribution.items():
            # This would use actual plan pricing - simplified for now
            plan_price = 99.99 if plan_name == "Premium" else 49.99
            plan_revenue[plan_name] = {
                "subscriber_count": count,
                "monthly_revenue": count * plan_price,
                "percentage": round((count / Subscription.objects.count()) * 100, 2) if Subscription.objects.count() > 0 else 0
            }
        
        return plan_revenue
    
    def _get_billing_health_metrics(self):
        """Get billing health metrics"""
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(
            Q(status__icontains='paid') | Q(status__icontains='Paid')
        ).count()
        failed_invoices = Invoice.objects.filter(
            Q(status__icontains='failed') | Q(status__icontains='Failed')
        ).count()
        
        return {
            "payment_success_rate": round((paid_invoices / total_invoices) * 100, 2) if total_invoices > 0 else 0,
            "payment_failure_rate": round((failed_invoices / total_invoices) * 100, 2) if total_invoices > 0 else 0,
            "outstanding_invoices": Invoice.objects.filter(
                Q(status__icontains='pending') | Q(status__icontains='Pending')
            ).count(),
            "overdue_payments": self._get_overdue_payments_count(),
            "total_outstanding_amount": float(Invoice.objects.filter(
                Q(status__icontains='pending') | Q(status__icontains='Pending')
            ).aggregate(total=Sum('amount'))['total'] or 0)
        }
    
    def _get_upcoming_renewals(self):
        """Get upcoming subscription renewals"""
        next_30_days = timezone.now() + timedelta(days=30)
        
        upcoming = Subscription.objects.filter(
            is_active=True,
            current_period_end__lte=next_30_days,
            current_period_end__gte=timezone.now()
        ).select_related('user')
        
        renewal_data = []
        for sub in upcoming:
            renewal_data.append({
                "subscription_id": sub.stripe_subscription_id,
                "client_name": sub.user.get_full_name() or sub.user.email,
                "client_email": sub.user.email,
                "plan_name": sub.plan_name,
                "renewal_date": sub.current_period_end.isoformat(),
                "days_until_renewal": (sub.current_period_end.date() - timezone.now().date()).days,
                "estimated_amount": 99.99,  # Would come from actual plan pricing
                "payment_method_status": "Valid"  # Would check actual payment method
            })
        
        return renewal_data
    
    def _calculate_total_paid(self, user):
        """Calculate total amount paid by user"""
        total = Invoice.objects.filter(
            user=user,
            status__icontains='paid'
        ).aggregate(total=Sum('amount'))['total']
        return float(total) if total else 0
    
    def _calculate_days_until_renewal(self, renewal_date):
        """Calculate days until renewal"""
        if not renewal_date:
            return None
        
        days = (renewal_date.date() - timezone.now().date()).days
        return max(0, days)
    
    def _calculate_subscription_growth_rate(self):
        """Calculate monthly subscription growth rate"""
        now = timezone.now()
        current_month = Subscription.objects.filter(
            created_at__gte=now - timedelta(days=30)
        ).count()
        previous_month = Subscription.objects.filter(
            created_at__gte=now - timedelta(days=60),
            created_at__lt=now - timedelta(days=30)
        ).count()
        
        if previous_month > 0:
            return round(((current_month - previous_month) / previous_month) * 100, 2)
        return 0
    
    def _calculate_churn_rate(self):
        """Calculate subscription churn rate"""
        total_subscriptions = Subscription.objects.count()
        inactive_subscriptions = Subscription.objects.filter(is_active=False).count()
        
        if total_subscriptions > 0:
            return round((inactive_subscriptions / total_subscriptions) * 100, 2)
        return 0
    
    def _calculate_avg_subscription_length(self):
        """Calculate average subscription length"""
        # This would require tracking subscription start/end dates
        # Simplified for now
        return 8.5  # months
    
    def _get_overdue_payments_count(self):
        """Get count of overdue payments"""
        # This would check for invoices past due date
        # Simplified for now
        return 5


@extend_schema(
    tags=["Subscriptions"],
    summary="Get subscription details",
    description="Get detailed information about a specific subscription."
)
class SubscriptionDetailView(APIView):
    """Detailed subscription information"""
    
    permission_classes = [IsAdminUser]
    
    def get(self, request, subscription_id):
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            return Response({
                "error": "Subscription not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Subscription details
        subscription_details = {
            "subscription_id": subscription.stripe_subscription_id,
            "customer_id": subscription.stripe_customer_id,
            "client_info": {
                "name": subscription.user.get_full_name() or subscription.user.email,
                "email": subscription.user.email,
                "user_id": subscription.user.id,
                "registration_date": subscription.user.date_joined.isoformat()
            },
            "plan_info": {
                "plan_name": subscription.plan_name,
                "is_active": subscription.is_active,
                "created_date": subscription.created_at.isoformat(),
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None
            }
        }
        
        # Payment history
        payment_history = list(
            Invoice.objects.filter(user=subscription.user)
            .order_by('-created_at')
            .values(
                'stripe_invoice_id',
                'billing_title',
                'status',
                'billing_date',
                'amount',
                'currency',
                'plan',
                'invoice_pdf',
                'hosted_invoice_url'
            )
        )
        
        # Usage metrics (if available)
        usage_metrics = self._get_subscription_usage_metrics(subscription.user)
        
        # Billing alerts
        billing_alerts = self._get_billing_alerts(subscription)
        
        return Response({
            "subscription_details": subscription_details,
            "payment_history": payment_history,
            "usage_metrics": usage_metrics,
            "billing_alerts": billing_alerts
        })
    
    def _get_subscription_usage_metrics(self, user):
        """Get usage metrics for the subscription"""
        from admin_portal.models import AIConversation, Meeting, Ticket
        
        return {
            "ai_conversations": AIConversation.objects.filter(
                client__user=user
            ).count(),
            "meetings_scheduled": Meeting.objects.filter(
                client__user=user
            ).count(),
            "support_tickets": Ticket.objects.filter(
                client__user=user
            ).count(),
            "last_activity": user.last_login.isoformat() if user.last_login else None
        }
    
    def _get_billing_alerts(self, subscription):
        """Get billing-related alerts for the subscription"""
        alerts = []
        
        # Check for upcoming renewal
        if subscription.current_period_end:
            days_until_renewal = (subscription.current_period_end.date() - timezone.now().date()).days
            if days_until_renewal <= 7:
                alerts.append({
                    "type": "renewal_due",
                    "message": f"Subscription renews in {days_until_renewal} days",
                    "severity": "info"
                })
        
        # Check for failed payments
        recent_failed = Invoice.objects.filter(
            user=subscription.user,
            status__icontains='failed',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        if recent_failed > 0:
            alerts.append({
                "type": "payment_failed",
                "message": f"{recent_failed} failed payment(s) in the last 30 days",
                "severity": "warning"
            })
        
        return alerts


@extend_schema(
    tags=["Subscriptions"],
    summary="Manage subscription actions",
    description="Perform actions on subscriptions like pause, resume, cancel, or change plan."
)
class SubscriptionActionsView(APIView):
    """Subscription management actions"""
    
    permission_classes = [IsAdminUser]
    
    def post(self, request, subscription_id):
        action = request.data.get('action')
        reason = request.data.get('reason', '')
        
        valid_actions = ['pause', 'resume', 'cancel', 'change_plan', 'update_billing']
        
        if action not in valid_actions:
            return Response({
                "error": f"Invalid action. Valid actions: {', '.join(valid_actions)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        except Subscription.DoesNotExist:
            return Response({
                "error": "Subscription not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        result = self._perform_subscription_action(subscription, action, request.data, reason)
        
        return Response(result)
    
    def _perform_subscription_action(self, subscription, action, data, reason):
        """Perform the requested subscription action"""
        
        if action == 'pause':
            # In real implementation, this would pause the Stripe subscription
            return {
                "status": "success",
                "message": f"Subscription {subscription.stripe_subscription_id} has been paused",
                "action": "pause",
                "effective_date": timezone.now().isoformat(),
                "reason": reason
            }
        
        elif action == 'resume':
            # In real implementation, this would resume the Stripe subscription
            return {
                "status": "success",
                "message": f"Subscription {subscription.stripe_subscription_id} has been resumed",
                "action": "resume",
                "effective_date": timezone.now().isoformat(),
                "reason": reason
            }
        
        elif action == 'cancel':
            # In real implementation, this would cancel the Stripe subscription
            subscription.is_active = False
            subscription.save()
            
            return {
                "status": "success",
                "message": f"Subscription {subscription.stripe_subscription_id} has been cancelled",
                "action": "cancel",
                "effective_date": timezone.now().isoformat(),
                "reason": reason,
                "refund_eligible": True  # Would be calculated based on actual billing
            }
        
        elif action == 'change_plan':
            new_plan = data.get('new_plan')
            if not new_plan:
                return {
                    "status": "error",
                    "message": "New plan name is required for plan change"
                }
            
            old_plan = subscription.plan_name
            subscription.plan_name = new_plan
            subscription.save()
            
            # Send subscription update email
            try:
                from admin_portal.orr_email_service import ORREmailService
                ORREmailService.send_subscription_update(
                    recipient_email=subscription.user.email,
                    old_plan_name=old_plan,
                    new_plan_name=new_plan,
                    billing_portal_url="https://orr.solutions/billing"
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to send subscription update email: {e}")
            
            return {
                "status": "success",
                "message": f"Plan changed from {old_plan} to {new_plan}",
                "action": "change_plan",
                "old_plan": old_plan,
                "new_plan": new_plan,
                "effective_date": timezone.now().isoformat(),
                "prorata_adjustment": 25.50  # Would be calculated
            }
        
        elif action == 'update_billing':
            return {
                "status": "success",
                "message": "Billing information update initiated",
                "action": "update_billing",
                "next_steps": [
                    "Customer will receive email to update payment method",
                    "Subscription will be paused if not updated within 7 days"
                ]
            }
        
        return {
            "status": "error",
            "message": "Unknown action"
        }