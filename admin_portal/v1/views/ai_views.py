"""
AI Views — API endpoints for all Gemini-powered AI features.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal import gemini_service
from admin_portal.models import (
    AIConversation,
    Client,
    ClientDocument,
    Content,
    Meeting,
    Ticket,
    TicketMessage,
)
from ..serializers.ai_serializers import (
    AIChatRequestSerializer,
    AIChatResponseSerializer,
    ClientInsightsRequestSerializer,
    ClientInsightsResponseSerializer,
    DashboardInsightsResponseSerializer,
    DocumentSummaryRequestSerializer,
    DocumentSummaryResponseSerializer,
    MeetingPrepRequestSerializer,
    MeetingPrepResponseSerializer,
    SmartReplyRequestSerializer,
    SmartReplyResponseSerializer,
)

logger = logging.getLogger(__name__)


@extend_schema(
    tags=["AI Features"],
    summary="Generate AI smart reply for a ticket",
    description="Uses Gemini AI to generate a contextual, professional reply for a support ticket based on its subject, description, and client context.",
)
class TicketSmartReplyView(APIView):
    """Generate an AI-powered smart reply for a ticket."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SmartReplyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ticket_id = data.get("ticket_id")
        subject = data.get("subject", "")
        description = data.get("description", "")

        client_name = ""
        client_stage = ""
        client_pillar = ""
        previous_messages = []

        if ticket_id:
            try:
                ticket = Ticket.objects.select_related("client__user").get(pk=ticket_id)
                subject = ticket.subject
                description = ticket.description
                client_name = ticket.client.user.get_full_name()
                client_stage = ticket.client.stage
                client_pillar = ticket.client.primary_pillar

                # Get recent messages for context
                recent_msgs = TicketMessage.objects.filter(ticket=ticket).order_by("-created_at")[:5]
                previous_messages = [msg.message for msg in reversed(recent_msgs)]
            except Ticket.DoesNotExist:
                return Response(
                    {"error": "Ticket not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if not subject and not description:
            return Response(
                {"error": "Provide either ticket_id or subject/description"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reply = gemini_service.generate_smart_reply(
            ticket_subject=subject,
            ticket_description=description,
            client_name=client_name,
            client_stage=client_stage,
            client_pillar=client_pillar,
            previous_messages=previous_messages,
        )

        return Response(
            SmartReplyResponseSerializer({"reply": reply, "is_ai_generated": True}).data
        )


@extend_schema(
    tags=["AI Features"],
    summary="Generate AI meeting preparation brief",
    description="Generates a comprehensive meeting preparation brief including talking points, suggested questions, and recommendations.",
)
class MeetingPrepView(APIView):
    """Generate AI meeting preparation brief."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MeetingPrepRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            meeting = Meeting.objects.select_related("client__user").get(
                pk=serializer.validated_data["meeting_id"]
            )
        except Meeting.DoesNotExist:
            return Response(
                {"error": "Meeting not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        result = gemini_service.generate_meeting_prep(
            meeting_type=meeting.get_meeting_type_display(),
            client_name=meeting.client.user.get_full_name(),
            client_company=meeting.client.company,
            client_stage=meeting.client.stage,
            client_pillar=meeting.client.primary_pillar,
            agenda=meeting.agenda,
            goals=meeting.goals,
            pain_points=meeting.pain_points,
            basic_context=meeting.basic_context,
        )

        return Response(MeetingPrepResponseSerializer(result).data)


@extend_schema(
    tags=["AI Features"],
    summary="AI document/content summarization",
    description="Uses Gemini to summarize documents, articles, or raw text. Generates a summary, key points, and suggested tags.",
)
class DocumentSummaryView(APIView):
    """AI-powered document/content summarization."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentSummaryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        title = data.get("title", "Untitled")
        text = data.get("text", "")

        # Try loading from document/content models
        doc_id = data.get("document_id")
        content_id = data.get("content_id")

        if doc_id:
            try:
                doc = ClientDocument.objects.get(pk=doc_id)
                title = doc.title
                text = doc.description or title
            except ClientDocument.DoesNotExist:
                return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

        if content_id:
            try:
                content_obj = Content.objects.get(pk=content_id)
                title = content_obj.title
                text = content_obj.content or content_obj.summary
            except Content.DoesNotExist:
                return Response({"error": "Content not found"}, status=status.HTTP_404_NOT_FOUND)

        if not text:
            return Response(
                {"error": "No text content to summarize. Provide text, document_id, or content_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = gemini_service.summarize_document(title=title, content=text)
        return Response(DocumentSummaryResponseSerializer(result).data)


@extend_schema(
    tags=["AI Features"],
    summary="AI client journey insights",
    description="Analyzes client engagement patterns and generates health scores, insights, and recommendations.",
)
class ClientInsightsView(APIView):
    """AI-powered client engagement analysis."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ClientInsightsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            client_obj = Client.objects.select_related("user").get(
                pk=serializer.validated_data["client_id"]
            )
        except Client.DoesNotExist:
            return Response({"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND)

        # Gather engagement stats
        total_meetings = Meeting.objects.filter(client=client_obj).count()
        total_tickets = Ticket.objects.filter(client=client_obj).count()
        total_documents = ClientDocument.objects.filter(client=client_obj).count()

        result = gemini_service.generate_client_insights(
            client_name=client_obj.user.get_full_name(),
            client_company=client_obj.company,
            stage=client_obj.stage,
            pillar=client_obj.primary_pillar,
            total_meetings=total_meetings,
            total_tickets=total_tickets,
            total_documents=total_documents,
        )

        return Response(ClientInsightsResponseSerializer(result).data)


@extend_schema(
    tags=["AI Features"],
    summary="AI Assistant Chat",
    description="General-purpose AI chat endpoint. Supports conversation history for multi-turn conversations. Used by the client portal AI chatbot, consultant AI helper, and admin AI assistant.",
)
class AIAssistantChatView(APIView):
    """General AI assistant chat — used by all portals."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AIChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Build user context from their profile
        user_context = data.get("context", "")
        if not user_context:
            try:
                client_obj = Client.objects.get(user=request.user)
                user_context = (
                    f"User: {request.user.get_full_name()}, "
                    f"Company: {client_obj.company}, "
                    f"Stage: {client_obj.stage}, "
                    f"Primary Pillar: {client_obj.primary_pillar}"
                )
            except Client.DoesNotExist:
                user_context = f"User: {request.user.get_full_name()}"

        reply = gemini_service.chat(
            message=data["message"],
            conversation_history=data.get("conversation_history", []),
            user_context=user_context,
        )

        # Log the conversation for AI oversight
        try:
            client_obj = Client.objects.get(user=request.user)
            import uuid

            session_id = request.data.get("session_id", str(uuid.uuid4())[:8])
            conversation, _ = AIConversation.objects.get_or_create(
                client=client_obj,
                session_id=session_id,
                defaults={"messages": []},
            )
            messages = conversation.messages or []
            messages.append({"role": "user", "content": data["message"]})
            messages.append({"role": "assistant", "content": reply})
            conversation.messages = messages
            conversation.save()
        except Client.DoesNotExist:
            pass  # Non-client users (admins, consultants) don't get logged
        except Exception as e:
            logger.warning(f"Failed to log AI conversation: {e}")

        return Response(
            AIChatResponseSerializer({"reply": reply, "is_ai_generated": True}).data
        )


@extend_schema(
    tags=["AI Features"],
    summary="AI Dashboard Insights",
    description="Generates AI-powered insights from platform metrics for the admin dashboard.",
)
class DashboardInsightsView(APIView):
    """AI-powered admin dashboard insights."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import timedelta
        from django.utils import timezone

        now = timezone.now()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)

        total_clients = Client.objects.count()
        active_clients = Client.objects.filter(last_activity__gte=last_30_days).count()
        recent_signups = Client.objects.filter(created_at__gte=last_7_days).count()

        total_tickets = Ticket.objects.count()
        open_tickets = Ticket.objects.exclude(status__in=["resolved", "archived"]).count()
        resolved_tickets = Ticket.objects.filter(status="resolved").count()
        resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0

        total_meetings = Meeting.objects.count()
        upcoming_meetings = Meeting.objects.filter(
            requested_datetime__gte=now,
            status__in=["requested", "confirmed"],
        ).count()

        result = gemini_service.generate_dashboard_insights(
            total_clients=total_clients,
            active_clients=active_clients,
            total_tickets=total_tickets,
            open_tickets=open_tickets,
            total_meetings=total_meetings,
            upcoming_meetings=upcoming_meetings,
            recent_signups=recent_signups,
            resolution_rate=resolution_rate,
        )

        return Response(DashboardInsightsResponseSerializer(result).data)
