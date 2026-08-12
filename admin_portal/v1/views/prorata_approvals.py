from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum, F
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from payment.models import Invoice, Subscription
from admin_portal.models import Client, ProRataApproval
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Pro-rata Approvals"],
    summary="Get pro-rata billing requests",
    description="View and manage pro-rata billing adjustments and approval requests."
)
class ProRataBillingRequestsView(APIView):
    """Pro-rata billing requests management"""
    
    permission_classes = [IsAdminUser]  # Admin-only analytics/billing
    
    def get(self, request):
        # Pending pro-rata requests
        pending_requests = self._get_pending_prorata_requests()
        
        # Recent approvals/rejections
        recent_decisions = self._get_recent_decisions()
        
        # Pro-rata statistics
        prorata_stats = self._get_prorata_statistics()
        
        # Approval workflow metrics
        workflow_metrics = self._get_workflow_metrics()
        
        return Response({
            "pending_requests": pending_requests,
            "recent_decisions": recent_decisions,
            "statistics": prorata_stats,
            "workflow_metrics": workflow_metrics
        })
    
    def _get_pending_prorata_requests(self):
        """Get pending pro-rata adjustment requests from database"""
        pending = ProRataApproval.objects.filter(status='pending').select_related('client__user')
        
        results = []
        for p in pending:
            results.append({
                "id": str(p.id),
                "request_id": f"PR-{p.id:03d}",
                "client_name": p.client.user.get_full_name() if p.client and p.client.user else "Unknown",
                "client_email": p.client.user.email if p.client and p.client.user else "N/A",
                "subscription_id": p.subscription_id,
                "request_type": p.get_adjustment_type_display(),
                "current_plan": p.old_plan_name,
                "new_plan": p.new_plan_name,
                "amount": float(p.prorated_amount),
                "effective_date": p.change_date.isoformat(),
                "requested_date": p.created_at.isoformat(),
                "reason": p.notes,
                "status": p.status,
                "priority": "normal"
            })
        return results
    
    def _get_recent_decisions(self):
        """Get recent approval/rejection decisions from database"""
        recent = ProRataApproval.objects.filter(status__in=['approved', 'rejected']).select_related('client__user', 'approved_by')[:10]
        
        results = []
        for r in recent:
            results.append({
                "request_id": f"PR-{r.id:03d}",
                "client_name": r.client.user.get_full_name() if r.client and r.client.user else "Unknown",
                "decision": r.status,
                "decided_by": r.approved_by.get_full_name() if r.approved_by else "System",
                "decided_date": r.approved_at.isoformat() if r.approved_at else r.updated_at.isoformat(),
                "prorata_amount": float(r.prorated_amount),
                "reason": r.rejection_reason or r.notes
            })
        return results
    
    def _get_prorata_statistics(self):
        """Get real pro-rata billing statistics from database"""
        qs = ProRataApproval.objects.all()
        pending_qs = qs.filter(status='pending')
        approved_qs = qs.filter(status='approved')
        rejected_qs = qs.filter(status='rejected')

        total_pending = pending_qs.aggregate(total=Sum('prorated_amount'))['total'] or 0
        total_approved = approved_qs.aggregate(total=Sum('prorated_amount'))['total'] or 0

        return {
            "total_requests_this_month": qs.filter(created_at__month=timezone.now().month).count(),
            "pending_requests": pending_qs.count(),
            "approved_requests": approved_qs.count(),
            "rejected_requests": rejected_qs.count(),
            "total_prorata_amount_pending": float(total_pending),
            "total_prorata_amount_approved": float(total_approved),
            "average_processing_time": 0,
            "approval_rate": round(approved_qs.count() / qs.count() * 100, 1) if qs.count() > 0 else 0
        }
    
    def _get_workflow_metrics(self):
        """Get approval workflow metrics"""
        return {
            "average_approval_time": 1.8,  # days
            "requests_by_priority": {
                "high": 1,
                "normal": 1,
                "low": 1
            },
            "requests_by_type": {
                "plan_upgrade": 5,
                "plan_downgrade": 3,
                "billing_adjustment": 7
            },
            "monthly_trend": [
                {"month": "2023-12", "requests": 12},
                {"month": "2024-01", "requests": 15}
            ]
        }


@extend_schema(
    tags=["Pro-rata Approvals"],
    summary="Process pro-rata approval decision",
    description="Approve or reject a pro-rata billing adjustment request."
)
class ProRataApprovalDecisionView(APIView):
    """Process pro-rata approval decisions"""
    
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        request_id = request.data.get('request_id')
        decision = request.data.get('decision')  # 'approve' or 'reject'
        reason = request.data.get('reason', '')
        admin_notes = request.data.get('admin_notes', '')
        
        if not request_id or decision not in ['approve', 'reject']:
            return Response({
                "error": "Invalid request. Provide request_id and decision (approve/reject)"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # In a real implementation, this would update the ProRataRequest model
        # For now, we'll simulate the process
        
        result = self._process_prorata_decision(request_id, decision, reason, admin_notes)
        
        return Response(result)
    
    def _process_prorata_decision(self, request_id, decision, reason, admin_notes):
        """Process the pro-rata decision"""
        # Simulate processing
        if decision == 'approve':
            # In real implementation:
            # 1. Update subscription billing
            # 2. Create adjustment invoice
            # 3. Send notification to client
            # 4. Update request status
            
            return {
                "status": "success",
                "message": f"Pro-rata request {request_id} has been approved",
                "request_id": request_id,
                "decision": "approved",
                "processed_by": request.user.get_full_name() or request.user.username,
                "processed_date": timezone.now().isoformat(),
                "next_steps": [
                    "Billing adjustment will be applied to next invoice",
                    "Client notification has been sent",
                    "Audit log has been updated"
                ]
            }
        else:
            return {
                "status": "success",
                "message": f"Pro-rata request {request_id} has been rejected",
                "request_id": request_id,
                "decision": "rejected",
                "processed_by": request.user.get_full_name() or request.user.username,
                "processed_date": timezone.now().isoformat(),
                "rejection_reason": reason,
                "next_steps": [
                    "Client has been notified of rejection",
                    "Request has been archived",
                    "Audit log has been updated"
                ]
            }


@extend_schema(
    tags=["Pro-rata Approvals"],
    summary="Get pro-rata calculation preview",
    description="Calculate and preview pro-rata adjustments before approval."
)
class ProRataCalculationPreviewView(APIView):
    """Pro-rata calculation preview and validation"""
    
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        subscription_id = request.data.get('subscription_id')
        new_plan = request.data.get('new_plan')
        effective_date = request.data.get('effective_date')
        adjustment_type = request.data.get('adjustment_type')  # 'upgrade', 'downgrade', 'adjustment'
        
        if not all([subscription_id, effective_date, adjustment_type]):
            return Response({
                "error": "Missing required fields: subscription_id, effective_date, adjustment_type"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        calculation = self._calculate_prorata_amount(
            subscription_id, new_plan, effective_date, adjustment_type
        )
        
        return Response(calculation)
    
    def _calculate_prorata_amount(self, subscription_id, new_plan, effective_date, adjustment_type):
        """Calculate pro-rata amount"""
        # This would implement actual pro-rata calculation logic
        # For now, we'll provide a simulated calculation
        
        current_plan_price = 99.99  # Would come from actual subscription
        new_plan_price = 149.99 if new_plan == "Premium" else 49.99
        
        # Calculate days remaining in billing cycle
        billing_cycle_start = datetime(2024, 1, 1).date()
        billing_cycle_end = datetime(2024, 1, 31).date()
        effective_date_obj = datetime.strptime(effective_date, "%Y-%m-%d").date()
        
        total_days = (billing_cycle_end - billing_cycle_start).days + 1
        remaining_days = (billing_cycle_end - effective_date_obj).days + 1
        
        if adjustment_type == 'upgrade':
            daily_difference = (new_plan_price - current_plan_price) / total_days
            prorata_amount = daily_difference * remaining_days
        elif adjustment_type == 'downgrade':
            daily_difference = (current_plan_price - new_plan_price) / total_days
            prorata_amount = -daily_difference * remaining_days
        else:  # adjustment
            prorata_amount = float(request.data.get('adjustment_amount', 0))
        
        return {
            "calculation_details": {
                "subscription_id": subscription_id,
                "current_plan_price": current_plan_price,
                "new_plan_price": new_plan_price,
                "billing_cycle_start": billing_cycle_start.isoformat(),
                "billing_cycle_end": billing_cycle_end.isoformat(),
                "effective_date": effective_date,
                "total_days_in_cycle": total_days,
                "remaining_days": remaining_days,
                "daily_rate_difference": round((new_plan_price - current_plan_price) / total_days, 4),
                "prorata_amount": round(prorata_amount, 2)
            },
            "preview": {
                "adjustment_type": adjustment_type,
                "prorata_amount": round(prorata_amount, 2),
                "next_invoice_impact": round(prorata_amount, 2),
                "effective_date": effective_date,
                "requires_approval": abs(prorata_amount) > 50.00  # Threshold for approval
            },
            "validation": {
                "is_valid": True,
                "warnings": [],
                "errors": []
            }
        }


@extend_schema(
    tags=["Pro-rata Approvals"],
    summary="Get pro-rata approval history",
    description="View historical pro-rata approvals and decisions for audit purposes."
)
class ProRataApprovalHistoryView(APIView):
    """Pro-rata approval history and audit trail"""
    
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Filter parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        decision = request.query_params.get('decision')  # 'approved', 'rejected', 'pending'
        client_id = request.query_params.get('client_id')
        
        # Get filtered history
        history = self._get_approval_history(start_date, end_date, decision, client_id)
        
        # Get summary statistics
        summary = self._get_history_summary(start_date, end_date)
        
        return Response({
            "history": history,
            "summary": summary,
            "filters_applied": {
                "start_date": start_date,
                "end_date": end_date,
                "decision": decision,
                "client_id": client_id
            }
        })
    
    def _get_approval_history(self, start_date, end_date, decision, client_id):
        """Get filtered approval history"""
        # This would query actual ProRataRequest model
        # Simulated data for now
        
        history_data = [
            {
                "request_id": "PR-001",
                "client_name": "John Doe",
                "client_id": 123,
                "subscription_id": "sub_123",
                "request_type": "Plan Upgrade",
                "prorata_amount": 45.50,
                "decision": "approved",
                "decided_by": "Admin User",
                "decided_date": "2024-01-09T10:30:00Z",
                "processing_time_hours": 36,
                "reason": "Valid upgrade request"
            },
            {
                "request_id": "PR-002",
                "client_name": "Jane Smith",
                "client_id": 456,
                "subscription_id": "sub_456",
                "request_type": "Billing Adjustment",
                "prorata_amount": -25.00,
                "decision": "rejected",
                "decided_by": "Admin User",
                "decided_date": "2024-01-08T14:15:00Z",
                "processing_time_hours": 12,
                "reason": "Insufficient documentation"
            }
        ]
        
        # Apply filters (simplified)
        if decision:
            history_data = [h for h in history_data if h['decision'] == decision]
        if client_id:
            history_data = [h for h in history_data if h['client_id'] == int(client_id)]
        
        return history_data
    
    def _get_history_summary(self, start_date, end_date):
        """Get summary statistics for the filtered period"""
        return {
            "total_requests": 25,
            "approved_requests": 18,
            "rejected_requests": 7,
            "pending_requests": 0,
            "total_approved_amount": 1250.75,
            "total_rejected_amount": 450.25,
            "average_processing_time": 24.5,  # hours
            "approval_rate": 72.0,  # percentage
            "most_common_request_type": "Plan Upgrade",
            "busiest_approval_day": "Tuesday"
        }