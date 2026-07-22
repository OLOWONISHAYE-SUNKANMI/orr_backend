from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from admin_portal.models import Ticket, Client
from ..serializers.tickets import TicketHistorySerializer , ClientInquiryTicketSerializer
from rest_framework import status
from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=["Ticket"],
)
class ClientTicketHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TicketHistorySerializer
    def get(self, request):
        user = request.user
        client, created = Client.objects.get_or_create(user=user)

        if not client:
            return Response(
                {"detail": "Client profile not found"},
                status=400,
            )

        tickets = (
            Ticket.objects
            .filter(client=client)
            .order_by("-created_at")
        )

        serializer = TicketHistorySerializer(tickets, many=True)
        return Response(serializer.data)



@extend_schema(
    tags=["Ticket"],
)
class ClientTicketCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ClientInquiryTicketSerializer
    def post(self, request):
        user = request.user
        client, created = Client.objects.get_or_create(user=user)

        if not client:
            return Response(
                {"detail": "Client profile not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ClientInquiryTicketSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        ticket = serializer.save(
            client=client,
        )

        # Trigger emails
        try:
            from admin_portal.orr_email_service import ORREmailService
            import datetime
            
            # Send confirmation to client
            ORREmailService.send_form_confirmation(
                recipient_email=user.email,
                form_name=ticket.subject,
                reference_id=ticket.ticket_id,
                submission_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                summary_text=ticket.description[:100] + "..." if len(ticket.description) > 100 else ticket.description,
                tracking_link=f"https://orr.solutions/dashboard/tickets/{ticket.ticket_id}"
            )
            
            # Notify admins
            from django.contrib.auth.models import User as AdminUser
            admin_emails = list(AdminUser.objects.filter(is_staff=True, is_active=True).values_list('email', flat=True))
            if admin_emails:
                ORREmailService.send_admin_notification(
                    recipient_emails=admin_emails,
                    submitter_name=user.get_full_name() or user.username,
                    submitter_email=user.email,
                    form_name="Client Inquiry Ticket",
                    reference_id=ticket.ticket_id,
                    admin_link=f"https://orr.solutions/admin/tickets/{ticket.ticket_id}"
                )
        except Exception as e:
            import logging
            logging.error(f"Failed to send ticket creation emails: {e}")

        return Response(
            {
                "message": "Ticket created successfully",
                "ticket_id": ticket.ticket_id,
            },
            status=status.HTTP_201_CREATED,
        )