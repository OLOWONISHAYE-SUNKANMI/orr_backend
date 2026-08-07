from django.db import models
from django.db.models import Avg, Count, Q, Sum, Max
from django.db.models.functions import Coalesce
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import Ticket, TicketMessage
from admin_portal.permissions import CanManageTickets
from admin_portal.services import NotificationService

from ..serializers.ticket import (
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketListSerializer,
    TicketMessageSerializer,
    TicketMessageCreateSerializer,
    TicketStatsSerializer,
    TicketUpdateSerializer,
)
from ..serializers.settings import AdminUserListSerializer


@extend_schema(
    tags=["Ticket Management"],
    summary="List or create tickets",
    description="Retrieve a filtered list of support tickets or create new tickets. Supports filtering by status, priority, assigned user, source, and date range.",
)
class TicketListView(generics.ListCreateAPIView):
    """List and create tickets"""

    permission_classes = [CanManageTickets]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TicketCreateSerializer
        return TicketListSerializer

    def get_queryset(self):
        queryset = Ticket.objects.select_related("client__user", "assigned_to").annotate(
            last_message_at=Coalesce(Max("messages__created_at"), "created_at"),
            messages_count=Count("messages")
        )

        try:
            user_role = self.request.user.admin_profile.role
            if user_role and user_role.name != "super_admin" and not user_role.can_view_all_clients:
                queryset = queryset.filter(client__assigned_admin=self.request.user)
        except AttributeError:
            pass

        # Search functionality
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(ticket_id__icontains=search)
                | Q(subject__icontains=search)
                | Q(client__user__first_name__icontains=search)
                | Q(client__user__last_name__icontains=search)
                | Q(client__company__icontains=search)
            )

        # Filters
        status_filter = self.request.query_params.get("status", None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority = self.request.query_params.get("priority", None)
        if priority:
            queryset = queryset.filter(priority=priority)

        assigned_to = self.request.query_params.get("assigned_to", None)
        if assigned_to:
            if assigned_to == "unassigned":
                queryset = queryset.filter(assigned_to__isnull=True)
            else:
                queryset = queryset.filter(assigned_to_id=assigned_to)

        source = self.request.query_params.get("source", None)
        if source:
            queryset = queryset.filter(source=source)
            
        is_escalated = self.request.query_params.get("is_escalated", None)
        if is_escalated:
            queryset = queryset.filter(is_escalated=(is_escalated.lower() == 'true'))
            
        # All tickets are payment-related, so no need for has_payment filter
            
        payment_status = self.request.query_params.get("payment_status", None)
        if payment_status:
            payment_statuses = ["processing", "payment_failed", "payment_disputed", "refund_requested", "refund_processed"]
            if payment_status in payment_statuses:
                queryset = queryset.filter(status=payment_status)

        # Date range filter
        date_from = self.request.query_params.get("date_from", None)
        date_to = self.request.query_params.get("date_to", None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset.order_by("-last_message_at")

    def perform_create(self, serializer):
        # Generate ticket ID
        ticket = serializer.save()
        ticket.ticket_id = f"TKT-{timezone.now().strftime('%Y%m%d')}-{ticket.pk:03d}"
        ticket.save()


@extend_schema(
    tags=["Ticket Management"],
    summary="Get or update ticket details",
    description="Retrieve detailed information about a specific ticket or update ticket properties including status, priority, and assignments.",
)
class TicketDetailView(generics.RetrieveUpdateAPIView):
    """Get and update ticket details"""

    permission_classes = [CanManageTickets]

    def get_queryset(self):
        queryset = Ticket.objects.select_related("client__user", "assigned_to").all()
        try:
            user_role = self.request.user.admin_profile.role
            if user_role and user_role.name != "super_admin" and not user_role.can_view_all_clients:
                queryset = queryset.filter(client__assigned_admin=self.request.user)
        except AttributeError:
            pass
        return queryset

    def get_serializer_class(self):
        if self.request.method == "GET":
            return TicketDetailSerializer
        return TicketUpdateSerializer
    
    def perform_update(self, serializer):
        # Get the old assigned user before update
        old_assigned_to = self.get_object().assigned_to
        
        # Save the updated ticket
        ticket = serializer.save()
        
        # Check if assignment changed
        new_assigned_to = ticket.assigned_to
        if old_assigned_to != new_assigned_to and new_assigned_to:
            # Send notification to newly assigned user
            NotificationService.send_ticket_notification(
                ticket, "assigned", new_assigned_to
            )


@extend_schema(
    tags=["Ticket Management"],
    summary="Manage ticket messages",
    description="Retrieve all messages in a ticket conversation or add new messages. Messages can be marked as internal (admin-only) or public (visible to client).",
)
class TicketMessagesView(generics.ListCreateAPIView):
    """List and create ticket messages"""

    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == "POST":
            return TicketMessageCreateSerializer
        return TicketMessageSerializer

    def get_queryset(self):
        ticket_id = self.kwargs.get("ticket_id")
        return TicketMessage.objects.filter(ticket_id=ticket_id).order_by("created_at")

    def perform_create(self, serializer):
        ticket_id = self.kwargs.get("ticket_id")
        message = serializer.save(ticket_id=ticket_id, sender=self.request.user)
        
        # Trigger email to client if an admin relies
        from admin_portal.models import Ticket
        try:
            ticket = Ticket.objects.get(pk=ticket_id)
            if self.request.user != ticket.client.user:
                # Client receives the notification
                NotificationService.send_ticket_notification(
                    ticket, "replied", ticket.client.user
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send ticket reply notification: {e}")


@extend_schema(
    tags=["Ticket Management"],
    summary="Perform ticket actions",
    description="Execute various ticket management actions including assign/unassign, update status/priority, and link to meetings or content.",
)
class TicketActionsView(APIView):
    """Ticket management actions"""

    permission_classes = [CanManageTickets]

    def post(self, request, pk):
        try:
            ticket = Ticket.objects.get(pk=pk)
            action = request.data.get("action")

            if action == "assign":
                assigned_to_id = request.data.get("assigned_to")
                if assigned_to_id:
                    from django.contrib.auth.models import User

                    try:
                        assigned_user = User.objects.get(pk=assigned_to_id)
                        ticket.assigned_to = assigned_user
                        ticket.save()

                        # Send notification
                        NotificationService.send_ticket_notification(
                            ticket, "assigned", assigned_user
                        )

                        return Response({"message": "Ticket assigned successfully"})
                    except User.DoesNotExist:
                        return Response(
                            {"error": "User not found"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    # Unassign ticket
                    ticket.assigned_to = None
                    ticket.save()
                    return Response({"message": "Ticket unassigned"})

            elif action == "update_status":
                new_status = request.data.get("status")
                if new_status in dict(Ticket.STATUS_CHOICES):
                    ticket.status = new_status
                    ticket.save()
                    return Response(
                        {
                            "message": f"Ticket status updated to {new_status}",
                            "status": ticket.status,
                        }
                    )
                else:
                    return Response(
                        {"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST
                    )

            elif action == "update_priority":
                new_priority = request.data.get("priority")
                if new_priority in dict(Ticket.PRIORITY_CHOICES):
                    ticket.priority = new_priority
                    ticket.save()
                    return Response(
                        {
                            "message": f"Ticket priority updated to {new_priority}",
                            "priority": ticket.priority,
                        }
                    )
                else:
                    return Response(
                        {"error": "Invalid priority"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )


                    
            elif action == "update_payment":
                invoice_id = request.data.get("invoice_id")
                subscription_id = request.data.get("subscription_id")
                
                if invoice_id:
                    from payment.models import Invoice
                    try:
                        invoice = Invoice.objects.get(pk=invoice_id)
                        ticket.related_invoice = invoice
                        ticket.payment_amount = invoice.amount
                        ticket.save()
                        return Response({"message": "Invoice linked to ticket"})
                    except Invoice.DoesNotExist:
                        return Response({"error": "Invoice not found"}, status=status.HTTP_400_BAD_REQUEST)
                        
                elif subscription_id:
                    from payment.models import Subscription
                    try:
                        subscription = Subscription.objects.get(pk=subscription_id)
                        ticket.related_subscription = subscription
                        ticket.save()
                        return Response({"message": "Subscription linked to ticket"})
                    except Subscription.DoesNotExist:
                        return Response({"error": "Subscription not found"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    ticket.related_invoice = None
                    ticket.related_subscription = None
                    ticket.payment_amount = None
                    ticket.save()
                    return Response({"message": "Payment unlinked from ticket"})
                    
            elif action == "process_refund":
                refund_amount = request.data.get("refund_amount")
                if refund_amount and ticket.related_invoice:
                    ticket.refund_amount = refund_amount
                    ticket.status = "refund_processed"
                    ticket.save()
                    return Response({"message": "Refund processed"})
                else:
                    return Response({"error": "Invalid refund request"}, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response(
                    {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
                )

        except Ticket.DoesNotExist:
            return Response(
                {"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND
            )


@extend_schema(
    tags=["Ticket Management"],
    summary="Get ticket statistics",
    description="Retrieve comprehensive ticket analytics including counts by status/priority/source, average response times, and resolution metrics.",
)
class TicketStatsView(APIView):
    """Ticket statistics and analytics"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Basic ticket counts
        total_tickets = Ticket.objects.count()
        new_tickets = Ticket.objects.filter(status="new").count()
        processing_payments = Ticket.objects.filter(status="processing").count()
        payment_failed = Ticket.objects.filter(status="payment_failed").count()
        payment_disputed = Ticket.objects.filter(status="payment_disputed").count()
        refund_requested = Ticket.objects.filter(status="refund_requested").count()
        resolved_tickets = Ticket.objects.filter(status="resolved").count()
        
        # Payment-specific metrics
        total_payment_amount = Ticket.objects.filter(payment_amount__isnull=False).aggregate(
            total=models.Sum('payment_amount')
        )['total'] or 0
        
        total_refund_amount = Ticket.objects.filter(refund_amount__isnull=False).aggregate(
            total=models.Sum('refund_amount')
        )['total'] or 0

        # Average response and resolution times (placeholder - would need actual calculation)
        avg_response_time = 2.5  # hours
        avg_resolution_time = 24.0  # hours

        # Tickets by priority
        tickets_by_priority = dict(
            Ticket.objects.values("priority")
            .annotate(count=Count("id"))
            .values_list("priority", "count")
        )

        # Tickets by source
        tickets_by_source = dict(
            Ticket.objects.values("source")
            .annotate(count=Count("id"))
            .values_list("source", "count")
        )

        stats_data = {
            "total_tickets": total_tickets,
            "new_tickets": new_tickets,
            "processing_payments": processing_payments,
            "payment_failed": payment_failed,
            "payment_disputed": payment_disputed,
            "refund_requested": refund_requested,
            "resolved_tickets": resolved_tickets,
            "total_payment_amount": total_payment_amount,
            "total_refund_amount": total_refund_amount,
            "avg_response_time": avg_response_time,
            "avg_resolution_time": avg_resolution_time,
            "tickets_by_priority": tickets_by_priority,
            "tickets_by_source": tickets_by_source,
        }

        serializer = TicketStatsSerializer(stats_data)
        return Response(serializer.data)


@extend_schema(
    tags=["Ticket Management"],
    summary="Get my assigned tickets",
    description="Retrieve all tickets assigned to the current authenticated user, ordered by creation date.",
)
class MyTicketsView(generics.ListAPIView):
    """Get tickets assigned to current user"""

    serializer_class = TicketListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Ticket.objects.filter(assigned_to=self.request.user)
            .select_related("client__user", "assigned_to")
            .order_by("-created_at")
        )


@extend_schema(
    tags=["Ticket Management"],
    summary="Get available users for ticket assignment",
    description="Retrieve list of admin users who can be assigned to tickets.",
)
class TicketAssignableUsersView(generics.ListAPIView):
    """Get users available for ticket assignment"""

    serializer_class = AdminUserListSerializer
    permission_classes = [CanManageTickets]

    def get_queryset(self):
        from django.contrib.auth.models import User
        # Return users who have admin profiles (can be assigned tickets)
        return User.objects.filter(
            admin_profile__isnull=False,
            is_active=True
        ).select_related('admin_profile__role').order_by('first_name', 'last_name', 'username')
