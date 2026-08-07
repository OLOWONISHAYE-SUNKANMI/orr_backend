from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.models import AIConversation, Client, ClientDocument, Meeting, Ticket
from admin_portal.permissions import IsAdminUser

@extend_schema(
    tags=["Client Management"],
    summary="Get complete client profile",
    description="Retrieve comprehensive client profile including basic info, engagement history, portal login history, and related links.",
)
class ClientCompleteProfileView(APIView):
    """Complete client profile with all required elements"""

    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            client = Client.objects.select_related("user", "assigned_admin").get(pk=pk)
            
            # Check RBAC
            user_role = request.user.admin_profile.role
            if user_role and user_role.name != "super_admin" and not user_role.can_view_all_clients:
                if client.assigned_admin != request.user:
                    return Response({"detail": "You do not have permission to view this client."}, status=status.HTTP_403_FORBIDDEN)

            # Basic info
            basic_info = {
                "id": client.id,
                "name": client.user.get_full_name(),
                "first_name": client.user.first_name,
                "last_name": client.user.last_name,
                "email": client.user.email,
                "company": client.company,
                "role": client.role,
                "phone": getattr(client.user, "profile", None)
                and client.user.profile.phone_number,
                "date_joined": client.user.date_joined,
                "last_login": client.user.last_login,
            }

            # Stage and pillar tags
            stage_pillar_info = {
                "stage": {
                    "code": client.stage,
                    "display": client.get_stage_display(),
                    "description": self._get_stage_description(client.stage),
                },
                "primary_pillar": {
                    "code": client.primary_pillar,
                    "display": client.get_primary_pillar_display(),
                },
                "secondary_pillars": client.secondary_pillars or [],
            }

            # Engagement history
            engagement_history = {
                "past_meetings": self._get_past_meetings(client),
                "tickets_raised": self._get_tickets_raised(client),
                "reports_delivered": self._get_reports_delivered(client),
                "portal_login_history": self._get_portal_login_history(client),
            }

            # Internal notes
            notes = {
                "internal_notes": client.internal_notes or "",
                "assigned_admin": (
                    client.assigned_admin.get_full_name()
                    if client.assigned_admin
                    else None
                ),
                "is_portal_active": client.is_portal_active,
            }

            # Related links
            related_links = {
                "tickets": f"/admin-portal/v1/tickets/?client={client.id}",
                "meetings": f"/admin-portal/v1/meetings/?client={client.id}",
                "documents": f"/admin-portal/v1/clients/{client.id}/documents/",
                "ai_chat_history": f"/admin-portal/v1/ai-oversight/conversations/?client={client.id}",
            }

            # AI chat history summaries
            ai_chat_summaries = self._get_ai_chat_summaries(client)

            return Response(
                {
                    "basic_info": basic_info,
                    "stage_pillar_info": stage_pillar_info,
                    "engagement_history": engagement_history,
                    "notes": notes,
                    "related_links": related_links,
                    "ai_chat_summaries": ai_chat_summaries,
                }
            )

        except Client.DoesNotExist:
            return Response(
                {"error": "Client not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def _get_stage_description(self, stage):
        """Get description for each ORR journey stage"""
        descriptions = {
            "discover": "Initial exploration and understanding of ORR services",
            "diagnose": "Assessment and analysis of current situation",
            "design": "Planning and designing solutions",
            "deploy": "Implementation and execution phase",
            "grow": "Scaling and optimization phase",
        }
        return descriptions.get(stage, "")

    def _get_past_meetings(self, client):
        """Get past meetings summary"""
        meetings = Meeting.objects.filter(client=client).order_by("-created_at")[:5]
        return [
            {
                "id": meeting.id,
                "type": meeting.get_meeting_type_display(),
                "status": meeting.get_status_display(),
                "datetime": meeting.confirmed_datetime or meeting.requested_datetime,
                "host": meeting.host.get_full_name() if meeting.host else None,
                "notes": (
                    meeting.meeting_notes[:100] + "..."
                    if meeting.meeting_notes and len(meeting.meeting_notes) > 100
                    else meeting.meeting_notes
                ),
            }
            for meeting in meetings
        ]

    def _get_tickets_raised(self, client):
        """Get tickets raised summary"""
        tickets = Ticket.objects.filter(client=client).order_by("-created_at")[:5]
        return [
            {
                "id": ticket.id,
                "ticket_id": ticket.ticket_id,
                "subject": ticket.subject,
                "status": ticket.get_status_display(),
                "priority": ticket.get_priority_display(),
                "created_at": ticket.created_at,
                "assigned_to": (
                    ticket.assigned_to.get_full_name() if ticket.assigned_to else None
                ),
            }
            for ticket in tickets
        ]

    def _get_reports_delivered(self, client):
        """Get reports/documents delivered"""
        documents = ClientDocument.objects.filter(
            client=client, is_visible_to_client=True
        ).order_by("-created_at")[:5]

        return [
            {
                "id": doc.id,
                "title": doc.title,
                "type": doc.document_type or "Report",
                "uploaded_at": doc.created_at,
                "uploaded_by": (
                    doc.uploaded_by.get_full_name() if doc.uploaded_by else None
                ),
                "download_count": doc.download_count,
                "last_accessed": doc.last_accessed,
            }
            for doc in documents
        ]

    def _get_portal_login_history(self, client):
        """Get high-level portal login history"""
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()

        # This is a simplified version - in production you'd track actual sessions
        return {
            "last_login": client.user.last_login,
            "total_sessions_30d": 5,  # Placeholder - would need session tracking
            "avg_session_duration": "22 minutes",  # Placeholder
            "most_active_time": "2:00 PM - 4:00 PM",  # Placeholder
            "login_frequency": "Weekly",  # Placeholder
            "last_7_days_activity": [
                {
                    "date": (now - timedelta(days=i)).date(),
                    "sessions": 1 if i < 3 else 0,
                }
                for i in range(7)
            ],
        }

    def _get_ai_chat_summaries(self, client):
        """Get AI chat history summaries"""
        conversations = AIConversation.objects.filter(client=client).order_by(
            "-created_at"
        )[:5]

        return [
            {
                "id": conv.id,
                "session_id": conv.session_id,
                "summary": conv.summary or "General inquiry about ORR services",
                "escalated_to_ticket": conv.escalated_to_ticket,
                "needs_improvement": conv.needs_improvement,
                "created_at": conv.created_at,
                "message_count": len(conv.messages) if conv.messages else 0,
                "topics": self._extract_topics(conv.messages) if conv.messages else [],
            }
            for conv in conversations
        ]

    def _extract_topics(self, messages):
        """Extract topics from AI conversation messages"""
        # Simplified topic extraction - in production would use NLP
        common_topics = ["billing", "services", "support", "meetings", "reports"]
        if not messages:
            return []

        # Simple keyword matching
        text = " ".join(
            [msg.get("content", "") for msg in messages if isinstance(msg, dict)]
        )
        found_topics = [topic for topic in common_topics if topic in text.lower()]
        return found_topics[:3]  # Return top 3 topics
