from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.models import User

from common.permissions import IsAdminUser
from payment.models import Invoice, Subscription
from payment.v1.serializers import InvoiceHistorySerializer


@extend_schema(tags=["admin-billing"])
class AdminBillingHistoryView(ListAPIView):
    """Admin view to see ALL payments made by all users"""
    serializer_class = InvoiceHistorySerializer
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get_queryset(self):
        queryset = Invoice.objects.all().order_by("-created_at")
        
        # Apply filters if provided
        user_id = self.request.query_params.get('user_id')
        status = self.request.query_params.get('status')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if status:
            queryset = queryset.filter(status__icontains=status)
        if start_date:
            queryset = queryset.filter(billing_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(billing_date__lte=end_date)
            
        return queryset


@extend_schema(tags=["admin-billing"])
class AdminBillingStatsView(APIView):
    """Admin view to get billing statistics for all users"""
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Calculate stats for all payments
        total_revenue = Invoice.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        completed_count = Invoice.objects.filter(
            Q(status__icontains='paid') | Q(status__icontains='Paid')
        ).count()
        
        pending_count = Invoice.objects.filter(
            Q(status__icontains='pending') | Q(status__icontains='Pending')
        ).count()
        
        pending_amount = Invoice.objects.filter(
            Q(status__icontains='pending') | Q(status__icontains='Pending')
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Monthly revenue for current year
        current_year = timezone.now().year
        monthly_revenue = []
        for month in range(1, 13):
            month_revenue = Invoice.objects.filter(
                billing_date__year=current_year,
                billing_date__month=month
            ).filter(
                Q(status__icontains='paid') | Q(status__icontains='Paid')
            ).aggregate(total=Sum('amount'))['total'] or 0
            monthly_revenue.append(month_revenue)
        
        # Recent activity (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_revenue = Invoice.objects.filter(
            billing_date__gte=thirty_days_ago
        ).filter(
            Q(status__icontains='paid') | Q(status__icontains='Paid')
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return Response({
            'total_revenue': float(total_revenue),
            'pending_amount': float(pending_amount),
            'completed_transactions': completed_count,
            'pending_transactions': pending_count,
            'monthly_revenue': monthly_revenue,
            'recent_revenue': float(recent_revenue),
            'total_customers': Subscription.objects.count(),
            'active_subscriptions': Subscription.objects.filter(is_active=True).count()
        })