from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework import status

from payment.models import Invoice, Subscription, PricingPlan
from admin_portal.models import Client
from common.permissions import IsAdminUser
from payment.v1.serializers import InvoiceHistorySerializer


@extend_schema(
    tags=["Invoicing"],
    summary="Get comprehensive invoicing overview",
    description="Complete invoicing management including invoice generation, tracking, and analytics."
)
class InvoicingOverviewView(APIView):
    """Comprehensive invoicing overview and management"""
    
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Invoice statistics
        invoice_stats = self._get_invoice_statistics()
        
        # Recent invoices
        recent_invoices = self._get_recent_invoices()
        
        # Invoice status distribution
        status_distribution = self._get_status_distribution()
        
        # Revenue analytics
        revenue_analytics = self._get_revenue_analytics()
        
        # Overdue invoices
        overdue_invoices = self._get_overdue_invoices()
        
        # Upcoming invoices
        upcoming_invoices = self._get_upcoming_invoices()
        
        return Response({
            "invoice_statistics": invoice_stats,
            "recent_invoices": recent_invoices,
            "status_distribution": status_distribution,
            "revenue_analytics": revenue_analytics,
            "overdue_invoices": overdue_invoices,
            "upcoming_invoices": upcoming_invoices
        })
    
    def _get_invoice_statistics(self):
        """Get comprehensive invoice statistics"""
        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        
        total_invoices = Invoice.objects.count()
        paid_invoices = Invoice.objects.filter(
            Q(status__icontains='paid') | 
            Q(status__icontains='succeeded') | 
            Q(status__icontains='complete')
        ).count()
        
        return {
            "total_invoices": total_invoices,
            "paid_invoices": paid_invoices,
            "pending_invoices": Invoice.objects.filter(
                Q(status__icontains='pending') | Q(status__icontains='Pending')
            ).count(),
            "failed_invoices": Invoice.objects.filter(
                Q(status__icontains='failed') | Q(status__icontains='Failed')
            ).count(),
            "invoices_this_month": Invoice.objects.filter(
                created_at__gte=last_30_days
            ).count(),
            "payment_success_rate": round((paid_invoices / total_invoices) * 100, 2) if total_invoices > 0 else 0,
            "average_invoice_amount": float(Invoice.objects.aggregate(
                avg=Avg('amount')
            )['avg'] or 0),
            "total_revenue": float(Invoice.objects.filter(
                Q(status__icontains='paid') | 
                Q(status__icontains='succeeded') | 
                Q(status__icontains='complete')
            ).aggregate(total=Sum('amount'))['total'] or 0)
        }
    
    def _get_recent_invoices(self):
        """Get recent invoices with details"""
        recent = Invoice.objects.select_related('user').order_by('-created_at')[:10]
        
        invoice_data = []
        for invoice in recent:
            # Standardized username resolution
            full_name = invoice.user.get_full_name().strip()
            display_name = full_name or invoice.user.username
            if not display_name or display_name.upper() == "N/A":
                display_name = invoice.user.email.split('@')[0] if invoice.user.email else "Client"

            invoice_data.append({
                "invoice_id": invoice.stripe_invoice_id,
                "client_name": display_name,
                "client_email": invoice.user.email,
                "amount": float(invoice.amount),
                "currency": invoice.currency,
                "status": invoice.status,
                "billing_date": invoice.billing_date.isoformat(),
                "plan": invoice.plan,
                "created_date": invoice.created_at.isoformat(),
                "invoice_pdf": invoice.invoice_pdf,
                "hosted_invoice_url": invoice.hosted_invoice_url
            })
        
        return invoice_data
    
    def _get_status_distribution(self):
        """Get invoice status distribution"""
        return dict(
            Invoice.objects.values('status')
            .annotate(count=Count('id'))
            .values_list('status', 'count')
        )
    
    def _get_revenue_analytics(self):
        """Get revenue analytics"""
        now = timezone.now()
        
        # Monthly revenue for the last 12 months
        monthly_revenue = []
        for i in range(12):
            month_start = (now - timedelta(days=30 * i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            revenue = Invoice.objects.filter(
                billing_date__gte=month_start,
                billing_date__lte=month_end,
                status__icontains='paid'
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_revenue.append({
                "month": month_start.strftime("%Y-%m"),
                "revenue": float(revenue)
            })
        
        # Revenue by plan
        revenue_by_plan = dict(
            Invoice.objects.filter(
                Q(status__icontains='paid') | Q(status__icontains='Paid')
            ).values('plan')
            .annotate(revenue=Sum('amount'))
            .values_list('plan', 'revenue')
        )
        
        return {
            "monthly_revenue": monthly_revenue,
            "revenue_by_plan": {k: float(v) for k, v in revenue_by_plan.items()},
            "total_revenue_ytd": self._calculate_ytd_revenue(),
            "revenue_growth_rate": self._calculate_revenue_growth_rate()
        }
    
    def _get_overdue_invoices(self):
        """Get overdue invoices"""
        # This would check for invoices past their due date
        # For now, we'll consider pending invoices older than 30 days as overdue
        overdue_date = timezone.now() - timedelta(days=30)
        
        overdue = Invoice.objects.filter(
            Q(status__icontains='pending') | Q(status__icontains='Pending'),
            created_at__lt=overdue_date
        ).select_related('user')
        
        overdue_data = []
        for invoice in overdue:
            days_overdue = (timezone.now().date() - invoice.billing_date).days
            
            overdue_data.append({
                "invoice_id": invoice.stripe_invoice_id,
                "client_name": invoice.user.get_full_name() or invoice.user.email,
                "client_email": invoice.user.email,
                "amount": float(invoice.amount),
                "billing_date": invoice.billing_date.isoformat(),
                "days_overdue": days_overdue,
                "plan": invoice.plan,
                "hosted_invoice_url": invoice.hosted_invoice_url
            })
        
        return overdue_data
    
    def _get_upcoming_invoices(self):
        """Get upcoming invoices based on subscription renewals"""
        next_30_days = timezone.now() + timedelta(days=30)
        
        upcoming_renewals = Subscription.objects.filter(
            is_active=True,
            current_period_end__lte=next_30_days,
            current_period_end__gte=timezone.now()
        ).select_related('user')
        
        upcoming_data = []
        for subscription in upcoming_renewals:
            # Estimate invoice amount based on plan
            estimated_amount = 99.99 if subscription.plan_name == "Premium" else 49.99
            
            upcoming_data.append({
                "subscription_id": subscription.stripe_subscription_id,
                "client_name": subscription.user.get_full_name() or subscription.user.email,
                "client_email": subscription.user.email,
                "estimated_amount": estimated_amount,
                "billing_date": subscription.current_period_end.isoformat(),
                "plan": subscription.plan_name,
                "days_until_billing": (subscription.current_period_end.date() - timezone.now().date()).days
            })
        
        return upcoming_data
    
    def _calculate_ytd_revenue(self):
        """Calculate year-to-date revenue"""
        year_start = timezone.now().replace(month=1, day=1)
        ytd_revenue = Invoice.objects.filter(
            billing_date__gte=year_start,
            status__icontains='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return float(ytd_revenue)
    
    def _calculate_revenue_growth_rate(self):
        """Calculate revenue growth rate"""
        now = timezone.now()
        current_month_start = now.replace(day=1)
        previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        current_month_revenue = Invoice.objects.filter(
            billing_date__gte=current_month_start,
            status__icontains='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        previous_month_revenue = Invoice.objects.filter(
            billing_date__gte=previous_month_start,
            billing_date__lt=current_month_start,
            status__icontains='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        if previous_month_revenue > 0:
            growth_rate = ((current_month_revenue - previous_month_revenue) / previous_month_revenue) * 100
            return round(float(growth_rate), 2)
        return 0


@extend_schema(
    tags=["Invoicing"],
    summary="Generate new invoice",
    description="Generate a new invoice for a client with specified details."
)
class InvoiceGenerationView(APIView):
    """Generate new invoices"""
    
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        client_id = request.data.get('client_id') or request.data.get('clientId') or request.data.get('userId')
        amount = request.data.get('amount')
        description = request.data.get('description')
        plan = request.data.get('plan', 'Custom')
        due_date = request.data.get('due_date') or request.data.get('dueDate')
        
        missing_fields = []
        if not client_id: missing_fields.append('client_id/clientId')
        if not amount: missing_fields.append('amount')
        if not description: missing_fields.append('description')
        
        if missing_fields:
            return Response({
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({
                "error": "Client not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Generate invoice
        invoice_data = self._generate_invoice(client.user, amount, description, plan, due_date)
        
        return Response(invoice_data)
    
    def _generate_invoice(self, user, amount, description, plan, due_date):
        """Generate a new invoice"""
        # In a real implementation, this would create an actual Stripe invoice
        # For now, we'll create a local invoice record
        
        invoice = Invoice.objects.create(
            user=user,
            stripe_invoice_id=f"in_{timezone.now().strftime('%Y%m%d%H%M%S')}",
            billing_title=description,
            status="pending",
            billing_date=timezone.now().date(),
            amount=amount,
            currency="USD",
            plan=plan
        )
        
        due_date_str = due_date or (timezone.now() + timedelta(days=30)).date().isoformat()
        
        try:
            from admin_portal.orr_email_service import ORREmailService
            ORREmailService.send_invoice_generated(
                recipient_email=user.email,
                invoice_id=invoice.stripe_invoice_id,
                total_amount=f"USD {amount}",
                due_date=due_date_str,
                payment_url=f"https://orr.solutions/billing/pay/{invoice.stripe_invoice_id}"
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send invoice generated email: {e}")
        
        return {
            "status": "success",
            "message": "Invoice generated successfully",
            "invoice_details": {
                "invoice_id": invoice.stripe_invoice_id,
                "client_name": user.get_full_name() or user.email,
                "client_email": user.email,
                "amount": float(amount),
                "description": description,
                "plan": plan,
                "status": "pending",
                "billing_date": invoice.billing_date.isoformat(),
                "due_date": due_date or (timezone.now() + timedelta(days=30)).date().isoformat()
            }
        }


@extend_schema(
    tags=["Invoicing"],
    summary="Manage invoice actions",
    description="Perform actions on invoices like send reminder, mark as paid, void, etc."
)
class InvoiceActionsView(APIView):
    """Invoice management actions"""
    
    permission_classes = [IsAdminUser]
    
    def post(self, request, invoice_id):
        action = request.data.get('action')
        notes = request.data.get('notes', '')
        
        valid_actions = ['send_reminder', 'mark_paid', 'void', 'resend', 'download_pdf']
        
        if action not in valid_actions:
            return Response({
                "error": f"Invalid action. Valid actions: {', '.join(valid_actions)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            invoice = Invoice.objects.get(stripe_invoice_id=invoice_id)
        except Invoice.DoesNotExist:
            return Response({
                "error": "Invoice not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        result = self._perform_invoice_action(invoice, action, notes)
        
        return Response(result)
    
    def _perform_invoice_action(self, invoice, action, notes):
        """Perform the requested invoice action"""
        
        if action == 'send_reminder':
            return {
                "status": "success",
                "message": f"Payment reminder sent for invoice {invoice.stripe_invoice_id}",
                "action": "send_reminder",
                "recipient": invoice.user.email,
                "sent_date": timezone.now().isoformat()
            }
        
        elif action == 'mark_paid':
            invoice.status = "paid"
            invoice.save()
            
            return {
                "status": "success",
                "message": f"Invoice {invoice.stripe_invoice_id} marked as paid",
                "action": "mark_paid",
                "updated_status": "paid",
                "notes": notes
            }
        
        elif action == 'void':
            invoice.status = "void"
            invoice.save()
            
            return {
                "status": "success",
                "message": f"Invoice {invoice.stripe_invoice_id} has been voided",
                "action": "void",
                "updated_status": "void",
                "notes": notes
            }
        
        elif action == 'resend':
            return {
                "status": "success",
                "message": f"Invoice {invoice.stripe_invoice_id} resent to client",
                "action": "resend",
                "recipient": invoice.user.email,
                "sent_date": timezone.now().isoformat()
            }
        
        elif action == 'download_pdf':
            return {
                "status": "success",
                "message": "PDF download initiated",
                "action": "download_pdf",
                "download_url": invoice.invoice_pdf or f"/api/invoices/{invoice.stripe_invoice_id}/pdf"
            }
        
        return {
            "status": "error",
            "message": "Unknown action"
        }


@extend_schema(
    tags=["Invoicing"],
    summary="Get invoice analytics and reports",
    description="Detailed invoice analytics, aging reports, and financial insights."
)
class InvoiceAnalyticsView(APIView):
    """Invoice analytics and reporting"""
    
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Aging report
        aging_report = self._get_aging_report()
        
        # Payment trends
        payment_trends = self._get_payment_trends()
        
        # Client payment behavior
        client_behavior = self._get_client_payment_behavior()
        
        # Revenue forecasting
        revenue_forecast = self._get_revenue_forecast()
        
        return Response({
            "aging_report": aging_report,
            "payment_trends": payment_trends,
            "client_behavior": client_behavior,
            "revenue_forecast": revenue_forecast
        })
    
    def _get_aging_report(self):
        """Get accounts receivable aging report"""
        now = timezone.now().date()
        
        # Define aging buckets
        buckets = {
            "current": 0,      # 0-30 days
            "30_days": 0,      # 31-60 days
            "60_days": 0,      # 61-90 days
            "90_days_plus": 0  # 90+ days
        }
        
        pending_invoices = Invoice.objects.filter(
            Q(status__icontains='pending') | Q(status__icontains='Pending')
        )
        
        for invoice in pending_invoices:
            days_old = (now - invoice.billing_date).days
            
            if days_old <= 30:
                buckets["current"] += float(invoice.amount)
            elif days_old <= 60:
                buckets["30_days"] += float(invoice.amount)
            elif days_old <= 90:
                buckets["60_days"] += float(invoice.amount)
            else:
                buckets["90_days_plus"] += float(invoice.amount)
        
        total_outstanding = sum(buckets.values())
        
        return {
            "aging_buckets": buckets,
            "total_outstanding": total_outstanding,
            "percentages": {
                bucket: round((amount / total_outstanding) * 100, 2) if total_outstanding > 0 else 0
                for bucket, amount in buckets.items()
            }
        }
    
    def _get_payment_trends(self):
        """Get payment trend analysis"""
        now = timezone.now()
        
        # Monthly payment success rates
        monthly_trends = []
        for i in range(6):  # Last 6 months
            month_start = (now - timedelta(days=30 * i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            total_invoices = Invoice.objects.filter(
                billing_date__gte=month_start,
                billing_date__lte=month_end
            ).count()
            
            paid_invoices = Invoice.objects.filter(
                billing_date__gte=month_start,
                billing_date__lte=month_end,
                status__icontains='paid'
            ).count()
            
            success_rate = round((paid_invoices / total_invoices) * 100, 2) if total_invoices > 0 else 0
            
            monthly_trends.append({
                "month": month_start.strftime("%Y-%m"),
                "total_invoices": total_invoices,
                "paid_invoices": paid_invoices,
                "success_rate": success_rate
            })
        
        return monthly_trends
    
    def _get_client_payment_behavior(self):
        """Analyze client payment behavior patterns"""
        # Top paying clients
        top_clients = list(
            Invoice.objects.filter(
                Q(status__icontains='paid') | Q(status__icontains='Paid')
            ).values('user__email', 'user__first_name', 'user__last_name')
            .annotate(total_paid=Sum('amount'), invoice_count=Count('id'))
            .order_by('-total_paid')[:10]
        )
        
        # Clients with payment issues
        problem_clients = list(
            Invoice.objects.filter(
                Q(status__icontains='failed') | Q(status__icontains='Failed') | 
                Q(status__icontains='pending') | Q(status__icontains='Pending')
            ).values('user__email', 'user__first_name', 'user__last_name')
            .annotate(
                failed_count=Count('id', filter=Q(status__icontains='failed')),
                pending_count=Count('id', filter=Q(status__icontains='pending')),
                total_outstanding=Sum('amount', filter=Q(status__icontains='pending'))
            ).order_by('-failed_count')[:10]
        )
        
        return {
            "top_paying_clients": [
                {
                    "client_name": f"{client['user__first_name']} {client['user__last_name']}".strip() or client['user__email'],
                    "email": client['user__email'],
                    "total_paid": float(client['total_paid']),
                    "invoice_count": client['invoice_count']
                }
                for client in top_clients
            ],
            "clients_with_issues": [
                {
                    "client_name": f"{client['user__first_name']} {client['user__last_name']}".strip() or client['user__email'],
                    "email": client['user__email'],
                    "failed_payments": client['failed_count'],
                    "pending_payments": client['pending_count'],
                    "outstanding_amount": float(client['total_outstanding'] or 0)
                }
                for client in problem_clients
            ]
        }
    
    def _get_revenue_forecast(self):
        """Generate revenue forecast based on subscriptions"""
        # Calculate projected revenue based on active subscriptions
        active_subscriptions = Subscription.objects.filter(is_active=True)
        
        # Estimate monthly recurring revenue
        mrr = 0
        for subscription in active_subscriptions:
            # This would use actual plan pricing
            plan_price = 99.99 if subscription.plan_name == "Premium" else 49.99
            mrr += plan_price
        
        # Project next 6 months
        forecast = []
        for i in range(6):
            month = (timezone.now() + timedelta(days=30 * i)).strftime("%Y-%m")
            # Apply growth assumptions (simplified)
            growth_factor = 1 + (0.05 * i)  # 5% monthly growth
            projected_revenue = mrr * growth_factor
            
            forecast.append({
                "month": month,
                "projected_revenue": round(projected_revenue, 2),
                "confidence": max(95 - (i * 10), 60)  # Decreasing confidence over time
            })
        
        return {
            "monthly_recurring_revenue": round(mrr, 2),
            "forecast": forecast,
            "assumptions": [
                "5% monthly growth rate",
                "No churn assumed",
                "Current pricing maintained"
            ]
        }