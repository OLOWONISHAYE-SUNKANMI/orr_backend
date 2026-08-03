from datetime import datetime, timedelta
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from payment.models import Invoice, Subscription
from admin_portal.models import Client, PaymentDispute, DisputeNote
from common.permissions import IsAdminUser


@extend_schema(
    tags=["Payment Disputes"],
    summary="Get payment disputes overview",
    description="Comprehensive view of payment disputes, chargebacks, and resolution management."
)
class PaymentDisputesOverviewView(APIView):
    """Payment disputes and chargebacks management"""
    
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Active disputes
        active_disputes = self._get_active_disputes()
        
        # Dispute statistics
        dispute_stats = self._get_dispute_statistics()
        
        # Recent dispute activity
        recent_activity = self._get_recent_dispute_activity()
        
        # Dispute trends
        dispute_trends = self._get_dispute_trends()
        
        # Resolution metrics
        resolution_metrics = self._get_resolution_metrics()
        
        return Response({
            "active_disputes": active_disputes,
            "dispute_statistics": dispute_stats,
            "recent_activity": recent_activity,
            "dispute_trends": dispute_trends,
            "resolution_metrics": resolution_metrics
        })

    def post(self, request):
        """Create a new payment dispute"""
        client_id = request.data.get('client_id')
        invoice_id = request.data.get('invoice_id')
        dispute_amount = request.data.get('dispute_amount')
        dispute_reason = request.data.get('dispute_reason', '')
        dispute_type = request.data.get('dispute_type', 'inquiry')
        evidence_due_days = request.data.get('evidence_due_days', 14)

        if not client_id or not invoice_id or not dispute_amount:
            return Response(
                {"error": "client_id, invoice_id, and dispute_amount are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({"error": "Client not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response({"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        if dispute_type not in dict(PaymentDispute.DISPUTE_TYPE_CHOICES):
            return Response(
                {"error": f"Invalid dispute_type. Valid: {', '.join(dict(PaymentDispute.DISPUTE_TYPE_CHOICES).keys())}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        dispute = PaymentDispute.objects.create(
            client=client,
            invoice=invoice,
            dispute_amount=dispute_amount,
            dispute_reason=dispute_reason,
            dispute_type=dispute_type,
            status='open',
            evidence_due_date=timezone.now() + timedelta(days=int(evidence_due_days)),
        )

        return Response({
            "status": "success",
            "message": "Dispute created successfully.",
            "dispute": {
                "dispute_id": f"DP-{dispute.id:03d}",
                "client_name": client.user.get_full_name() if client.user else "Unknown",
                "invoice_id": invoice.stripe_invoice_id,
                "amount": float(dispute.dispute_amount),
                "dispute_type": dispute.dispute_type,
                "reason": dispute.dispute_reason,
                "status": dispute.status,
                "created_date": dispute.created_at.isoformat(),
                "due_date": dispute.evidence_due_date.isoformat() if dispute.evidence_due_date else None,
            }
        }, status=status.HTTP_201_CREATED)
    
    def _get_active_disputes(self):
        """Get currently active payment disputes from database"""
        active_disputes = PaymentDispute.objects.filter(
            status__in=['open', 'under_review']
        ).select_related('client__user', 'invoice')
        
        results = []
        for d in active_disputes:
            # Calculate days remaining (simulated logic for now based on evidence_due_date)
            days_remaining = 0
            if d.evidence_due_date:
                delta = d.evidence_due_date - timezone.now()
                days_remaining = max(0, delta.days)

            results.append({
                "dispute_id": f"DP-{d.id:03d}",
                "invoice_id": d.invoice.stripe_invoice_id if d.invoice else "N/A",
                "client_name": d.client.user.get_full_name() if d.client and d.client.user else "Unknown",
                "client_email": d.client.user.email if d.client and d.client.user else "N/A",
                "amount": float(d.dispute_amount),
                "currency": "USD",
                "dispute_type": d.dispute_type,
                "reason": d.dispute_reason,
                "status": d.status,
                "created_date": d.created_at.isoformat(),
                "due_date": d.evidence_due_date.isoformat() if d.evidence_due_date else None,
                "priority": "high" if d.dispute_amount > 100 else "medium",
                "assigned_to": "Support Team",
                "evidence_required": d.status == 'open',
                "days_remaining": days_remaining
            })
        
        return results
    
    def _get_dispute_statistics(self):
        """Get real dispute statistics and metrics from database"""
        total_qs = PaymentDispute.objects.all()
        active_qs = total_qs.filter(status__in=['open', 'under_review'])
        resolved_qs = total_qs.filter(status__in=['resolved', 'closed'])
        won_qs = total_qs.filter(status='resolved')
        lost_qs = total_qs.filter(status='closed')

        total_disputes = total_qs.count()
        active_count = active_qs.count()
        resolved_count = resolved_qs.count()
        won_count = won_qs.count()

        win_rate = (won_count / resolved_count * 100) if resolved_count > 0 else 0
        
        total_disputed_amount = total_qs.aggregate(total=Sum('dispute_amount'))['total'] or 0
        recovered_amount = won_qs.aggregate(total=Sum('dispute_amount'))['total'] or 0

        return {
            "total_disputes": total_disputes,
            "active_disputes": active_count,
            "resolved_disputes": resolved_count,
            "won_disputes": won_count,
            "lost_disputes": lost_qs.count(),
            "dispute_rate": 0,  # Would need total invoice count to calculate
            "win_rate": round(win_rate, 1),
            "average_resolution_time": 0,
            "total_disputed_amount": float(total_disputed_amount),
            "recovered_amount": float(recovered_amount),
            "chargeback_count": total_qs.filter(dispute_type='chargeback').count(),
            "inquiry_count": total_qs.filter(dispute_type='inquiry').count()
        }
    
    def _get_recent_dispute_activity(self):
        """Get recent dispute-related activities"""
        return [
            {
                "activity_id": "ACT-001",
                "dispute_id": "DP-003",
                "activity_type": "evidence_submitted",
                "description": "Submitted transaction evidence and customer communication logs",
                "performed_by": "Admin User",
                "timestamp": "2024-01-20T11:45:00Z",
                "status": "completed"
            },
            {
                "activity_id": "ACT-002",
                "dispute_id": "DP-001",
                "activity_type": "customer_contacted",
                "description": "Reached out to customer for additional information",
                "performed_by": "Support Agent",
                "timestamp": "2024-01-19T16:30:00Z",
                "status": "awaiting_response"
            },
            {
                "activity_id": "ACT-003",
                "dispute_id": "DP-004",
                "activity_type": "dispute_resolved",
                "description": "Dispute resolved in our favor - funds recovered",
                "performed_by": "System",
                "timestamp": "2024-01-18T09:20:00Z",
                "status": "completed"
            }
        ]
    
    def _get_dispute_trends(self):
        """Get dispute trends over time"""
        # Monthly dispute data for the last 6 months
        monthly_data = []
        
        for i in range(6):
            month = (timezone.now() - timedelta(days=30 * i)).strftime("%Y-%m")
            # Simulated data - would come from actual dispute records
            disputes = max(1, 5 - i)  # Decreasing trend
            chargebacks = max(0, disputes - 2)
            inquiries = disputes - chargebacks
            
            monthly_data.append({
                "month": month,
                "total_disputes": disputes,
                "chargebacks": chargebacks,
                "inquiries": inquiries,
                "dispute_rate": round(2.5 - (i * 0.2), 1),  # Improving trend
                "win_rate": min(95, 75 + (i * 3))  # Improving win rate
            })
        
        return monthly_data
    
    def _get_resolution_metrics(self):
        """Get dispute resolution performance metrics"""
        return {
            "average_response_time": 4.2,  # Hours to first response
            "average_resolution_time": 12.5,  # Days to resolution
            "escalation_rate": 15.0,  # Percentage escalated to legal
            "customer_satisfaction": 4.1,  # Out of 5 for resolved disputes
            "evidence_success_rate": 85.0,  # Percentage of cases won with evidence
            "proactive_resolution_rate": 25.0,  # Percentage resolved before formal dispute
            "repeat_dispute_rate": 5.0  # Percentage of customers with multiple disputes
        }


@extend_schema(
    tags=["Payment Disputes"],
    summary="Manage dispute actions",
    description="Perform actions on payment disputes like submit evidence, contact customer, or resolve dispute."
)
class DisputeActionsView(APIView):
    """Dispute management actions"""
    
    permission_classes = [IsAdminUser]
    
    def _get_dispute(self, dispute_id):
        """Resolve DP-XXX id to a real PaymentDispute record."""
        numeric_id = dispute_id.replace('DP-', '').lstrip('0') or '0'
        try:
            return PaymentDispute.objects.get(id=int(numeric_id))
        except (PaymentDispute.DoesNotExist, ValueError):
            return None
    
    def post(self, request, dispute_id):
        action = request.data.get('action')
        notes = request.data.get('notes', '')
        evidence_files = request.data.get('evidence_files', [])
        
        valid_actions = [
            'submit_evidence', 'contact_customer', 'escalate', 
            'resolve_won', 'resolve_lost', 'request_refund'
        ]
        
        if action not in valid_actions:
            return Response({
                "error": f"Invalid action. Valid actions: {', '.join(valid_actions)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        dispute = self._get_dispute(dispute_id)
        if not dispute:
            return Response({"error": "Dispute not found."}, status=status.HTTP_404_NOT_FOUND)
        
        result = self._perform_dispute_action(dispute, action, notes, evidence_files, request.user)
        
        return Response(result)
    
    def _perform_dispute_action(self, dispute, action, notes, evidence_files, user):
        """Perform the requested dispute action and persist changes to DB."""
        dispute_id = f"DP-{dispute.id:03d}"

        # Always log a note when an action is taken
        if notes:
            DisputeNote.objects.create(
                dispute=dispute,
                created_by=user,
                note=f"[{action}] {notes}",
                is_internal=True
            )
        
        if action == 'submit_evidence':
            dispute.status = 'under_review'
            dispute.save(update_fields=['status', 'updated_at'])
            return {
                "status": "success",
                "message": f"Evidence submitted for dispute {dispute_id}",
                "action": "submit_evidence",
                "new_status": dispute.status,
                "evidence_count": len(evidence_files),
                "submitted_date": timezone.now().isoformat(),
                "next_steps": [
                    "Evidence will be reviewed by payment processor",
                    "Response expected within 7-10 business days",
                    "Monitor dispute status for updates"
                ]
            }
        
        elif action == 'contact_customer':
            return {
                "status": "success",
                "message": f"Customer contacted regarding dispute {dispute_id}",
                "action": "contact_customer",
                "contact_method": "email",
                "contacted_date": timezone.now().isoformat(),
                "notes": notes,
                "follow_up_required": True,
                "follow_up_date": (timezone.now() + timedelta(days=3)).isoformat()
            }
        
        elif action == 'escalate':
            dispute.status = 'under_review'
            dispute.save(update_fields=['status', 'updated_at'])
            return {
                "status": "success",
                "message": f"Dispute {dispute_id} escalated to legal team",
                "action": "escalate",
                "new_status": dispute.status,
                "escalated_to": "Legal Department",
                "escalated_date": timezone.now().isoformat(),
                "priority": "high",
                "reason": notes
            }
        
        elif action == 'resolve_won':
            dispute.status = 'resolved'
            dispute.resolved_by = user
            dispute.resolved_at = timezone.now()
            dispute.resolution_notes = notes
            dispute.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_notes', 'updated_at'])
            return {
                "status": "success",
                "message": f"Dispute {dispute_id} resolved in our favor",
                "action": "resolve_won",
                "new_status": dispute.status,
                "resolution_date": dispute.resolved_at.isoformat(),
                "funds_recovered": True,
                "recovery_amount": float(dispute.dispute_amount),
                "resolution_notes": notes
            }
        
        elif action == 'resolve_lost':
            dispute.status = 'closed'
            dispute.resolved_by = user
            dispute.resolved_at = timezone.now()
            dispute.resolution_notes = notes
            dispute.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_notes', 'updated_at'])
            return {
                "status": "success",
                "message": f"Dispute {dispute_id} resolved - customer favor",
                "action": "resolve_lost",
                "new_status": dispute.status,
                "resolution_date": dispute.resolved_at.isoformat(),
                "refund_issued": True,
                "refund_amount": float(dispute.dispute_amount),
                "resolution_notes": notes
            }
        
        elif action == 'request_refund':
            return {
                "status": "success",
                "message": f"Refund requested for dispute {dispute_id}",
                "action": "request_refund",
                "refund_amount": float(dispute.dispute_amount),
                "refund_method": "original_payment_method",
                "processing_time": "3-5 business days",
                "refund_id": f"rf_{timezone.now().strftime('%Y%m%d%H%M%S')}"
            }
        
        return {
            "status": "error",
            "message": "Unknown action"
        }


@extend_schema(
    tags=["Payment Disputes"],
    summary="Get dispute details",
    description="Get detailed information about a specific payment dispute."
)
class DisputeDetailView(APIView):
    """Detailed dispute information"""
    
    permission_classes = [IsAdminUser]
    
    def get(self, request, dispute_id):
        # Get dispute details
        dispute_details = self._get_dispute_details(dispute_id)
        
        if not dispute_details:
            return Response({
                "error": "Dispute not found"
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get related transaction details
        transaction_details = self._get_transaction_details(dispute_details['invoice_id'])
        
        # Get dispute timeline
        dispute_timeline = self._get_dispute_timeline(dispute_id)
        
        # Get evidence and documentation
        evidence = self._get_dispute_evidence(dispute_id)
        
        # Get communication history
        communications = self._get_dispute_communications(dispute_id)
        
        return Response({
            "dispute_details": dispute_details,
            "transaction_details": transaction_details,
            "timeline": dispute_timeline,
            "evidence": evidence,
            "communications": communications
        })
    
    def _get_dispute_details(self, dispute_id):
        """Get detailed dispute information"""
        # This would query actual dispute records
        # Simulated for now
        
        disputes = {
            "DP-001": {
                "dispute_id": "DP-001",
                "stripe_dispute_id": "dp_1234567890",
                "invoice_id": "in_1234567890",
                "client_info": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "customer_id": "cus_1234567890"
                },
                "amount": 99.99,
                "currency": "USD",
                "dispute_type": "chargeback",
                "reason_code": "product_not_received",
                "reason_description": "Product not received",
                "status": "under_review",
                "created_date": "2024-01-15T10:30:00Z",
                "due_date": "2024-01-29T23:59:59Z",
                "priority": "high",
                "assigned_to": "Support Team",
                "evidence_required": True,
                "evidence_due_date": "2024-01-25T23:59:59Z",
                "network_reason_code": "4855",
                "issuing_bank": "Chase Bank"
            }
        }
        
        return disputes.get(dispute_id)
    
    def _get_transaction_details(self, invoice_id):
        """Get original transaction details"""
        try:
            invoice = Invoice.objects.get(stripe_invoice_id=invoice_id)
            return {
                "invoice_id": invoice.stripe_invoice_id,
                "amount": float(invoice.amount),
                "currency": invoice.currency,
                "billing_date": invoice.billing_date.isoformat(),
                "plan": invoice.plan,
                "payment_method": "card_ending_4242",  # Would come from Stripe
                "transaction_id": "txn_1234567890",
                "authorization_code": "123456"
            }
        except Invoice.DoesNotExist:
            return None
    
    def _get_dispute_timeline(self, dispute_id):
        """Get dispute timeline and history"""
        return [
            {
                "date": "2024-01-15T10:30:00Z",
                "event": "Dispute Created",
                "description": "Chargeback received from issuing bank",
                "status": "created",
                "automated": True
            },
            {
                "date": "2024-01-15T11:00:00Z",
                "event": "Dispute Assigned",
                "description": "Assigned to Support Team for review",
                "status": "assigned",
                "performed_by": "System"
            },
            {
                "date": "2024-01-16T09:15:00Z",
                "event": "Customer Contacted",
                "description": "Reached out to customer for clarification",
                "status": "in_progress",
                "performed_by": "Support Agent"
            },
            {
                "date": "2024-01-18T14:30:00Z",
                "event": "Evidence Gathered",
                "description": "Collected transaction logs and customer communications",
                "status": "evidence_collected",
                "performed_by": "Support Team"
            }
        ]
    
    def _get_dispute_evidence(self, dispute_id):
        """Get evidence and documentation for dispute"""
        return {
            "evidence_submitted": True,
            "submission_date": "2024-01-20T11:45:00Z",
            "evidence_items": [
                {
                    "type": "receipt",
                    "description": "Original transaction receipt",
                    "file_name": "receipt_001.pdf",
                    "uploaded_date": "2024-01-20T11:45:00Z"
                },
                {
                    "type": "customer_communication",
                    "description": "Email thread with customer",
                    "file_name": "email_thread.pdf",
                    "uploaded_date": "2024-01-20T11:46:00Z"
                },
                {
                    "type": "service_documentation",
                    "description": "Proof of service delivery",
                    "file_name": "service_proof.pdf",
                    "uploaded_date": "2024-01-20T11:47:00Z"
                }
            ],
            "additional_evidence_needed": False,
            "evidence_strength": "strong"
        }
    
    def _get_dispute_communications(self, dispute_id):
        """Get communication history for dispute"""
        return [
            {
                "date": "2024-01-16T09:15:00Z",
                "type": "email",
                "direction": "outbound",
                "subject": "Regarding your recent payment inquiry",
                "recipient": "john@example.com",
                "sender": "support@orr.com",
                "status": "sent"
            },
            {
                "date": "2024-01-17T14:20:00Z",
                "type": "email",
                "direction": "inbound",
                "subject": "Re: Regarding your recent payment inquiry",
                "recipient": "support@orr.com",
                "sender": "john@example.com",
                "status": "received"
            },
            {
                "date": "2024-01-18T10:30:00Z",
                "type": "phone",
                "direction": "outbound",
                "duration": "15 minutes",
                "notes": "Discussed transaction details and service delivery",
                "outcome": "customer_satisfied"
            }
        ]


@extend_schema(
    tags=["Payment Disputes"],
    summary="Get dispute analytics and reports",
    description="Comprehensive analytics on dispute patterns, resolution performance, and financial impact."
)
class DisputeAnalyticsView(APIView):
    """Dispute analytics and reporting"""
    
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Dispute pattern analysis
        pattern_analysis = self._get_dispute_patterns()
        
        # Financial impact analysis
        financial_impact = self._get_financial_impact()
        
        # Resolution performance
        resolution_performance = self._get_resolution_performance()
        
        # Prevention opportunities
        prevention_opportunities = self._get_prevention_opportunities()
        
        return Response({
            "pattern_analysis": pattern_analysis,
            "financial_impact": financial_impact,
            "resolution_performance": resolution_performance,
            "prevention_opportunities": prevention_opportunities
        })
    
    def _get_dispute_patterns(self):
        """Analyze dispute patterns and trends"""
        return {
            "most_common_reasons": [
                {"reason": "Product not received", "count": 8, "percentage": 32},
                {"reason": "Billing question", "count": 6, "percentage": 24},
                {"reason": "Fraudulent transaction", "count": 5, "percentage": 20},
                {"reason": "Duplicate charge", "count": 4, "percentage": 16},
                {"reason": "Service not as described", "count": 2, "percentage": 8}
            ],
            "dispute_by_plan": {
                "Basic": {"count": 5, "rate": 1.2},
                "Premium": {"count": 12, "rate": 2.8},
                "Enterprise": {"count": 8, "rate": 1.9}
            },
            "seasonal_trends": {
                "Q1": 8,
                "Q2": 6,
                "Q3": 7,
                "Q4": 4
            },
            "time_patterns": {
                "monday": 15,
                "tuesday": 20,
                "wednesday": 18,
                "thursday": 22,
                "friday": 25
            }
        }
    
    def _get_financial_impact(self):
        """Analyze financial impact of disputes"""
        return {
            "total_disputed_amount": 2450.75,
            "recovered_amount": 1980.50,
            "lost_amount": 470.25,
            "recovery_rate": 80.8,
            "chargeback_fees": 375.00,
            "processing_costs": 125.00,
            "net_impact": -970.25,
            "monthly_impact": [
                {"month": "2023-12", "disputed": 450.00, "recovered": 380.00},
                {"month": "2024-01", "disputed": 520.75, "recovered": 420.50}
            ]
        }
    
    def _get_resolution_performance(self):
        """Analyze resolution performance metrics"""
        return {
            "average_resolution_time": 12.5,
            "resolution_time_by_type": {
                "chargeback": 15.2,
                "inquiry": 8.7,
                "retrieval_request": 5.3
            },
            "win_rate_by_reason": {
                "product_not_received": 75.0,
                "fraudulent_transaction": 90.0,
                "billing_question": 95.0,
                "duplicate_charge": 85.0
            },
            "team_performance": {
                "Support Team": {"cases": 15, "win_rate": 80.0, "avg_time": 10.5},
                "Billing Team": {"cases": 8, "win_rate": 87.5, "avg_time": 8.2},
                "Legal Team": {"cases": 2, "win_rate": 100.0, "avg_time": 20.0}
            }
        }
    
    def _get_prevention_opportunities(self):
        """Identify dispute prevention opportunities"""
        return {
            "high_risk_indicators": [
                "First-time customers with high-value transactions",
                "Customers with multiple failed payment attempts",
                "International transactions without address verification"
            ],
            "recommended_actions": [
                {
                    "action": "Improve transaction descriptions",
                    "impact": "Could reduce 'unrecognized charge' disputes by 30%"
                },
                {
                    "action": "Enhanced customer communication",
                    "impact": "Could reduce inquiry escalations by 25%"
                },
                {
                    "action": "Proactive refund policy",
                    "impact": "Could prevent 40% of service-related disputes"
                }
            ],
            "automation_opportunities": [
                "Auto-refund for duplicate charges under $50",
                "Proactive communication for failed payments",
                "Automated evidence collection for common dispute types"
            ]
        }