"""
AI Serializers — Request/response serializers for all AI endpoints.
"""

from rest_framework import serializers


class SmartReplyRequestSerializer(serializers.Serializer):
    ticket_id = serializers.IntegerField(required=False, help_text="Ticket ID to generate a reply for")
    subject = serializers.CharField(required=False, help_text="Ticket subject (if not providing ticket_id)")
    description = serializers.CharField(required=False, help_text="Ticket description (if not providing ticket_id)")


class SmartReplyResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    is_ai_generated = serializers.BooleanField(default=True)


class MeetingPrepRequestSerializer(serializers.Serializer):
    meeting_id = serializers.IntegerField(help_text="Meeting ID to generate preparation brief for")


class MeetingPrepResponseSerializer(serializers.Serializer):
    summary = serializers.CharField()
    talking_points = serializers.ListField(child=serializers.CharField())
    suggested_questions = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())


class DocumentSummaryRequestSerializer(serializers.Serializer):
    document_id = serializers.IntegerField(required=False, help_text="ClientDocument ID")
    content_id = serializers.IntegerField(required=False, help_text="Content ID")
    text = serializers.CharField(required=False, help_text="Raw text to summarize")
    title = serializers.CharField(required=False, default="Untitled")


class DocumentSummaryResponseSerializer(serializers.Serializer):
    summary = serializers.CharField()
    key_points = serializers.ListField(child=serializers.CharField())
    suggested_tags = serializers.ListField(child=serializers.CharField())


class ClientInsightsRequestSerializer(serializers.Serializer):
    client_id = serializers.IntegerField(help_text="Client ID to analyze")


class ClientInsightsResponseSerializer(serializers.Serializer):
    health_score = serializers.IntegerField()
    insights = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())
    risk_flags = serializers.ListField(child=serializers.CharField())


class AIChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="User message to send to AI assistant")
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Previous messages as [{role, content}, ...]",
    )
    context = serializers.CharField(required=False, default="", help_text="Additional user context")


class AIChatResponseSerializer(serializers.Serializer):
    reply = serializers.CharField()
    is_ai_generated = serializers.BooleanField(default=True)


class DashboardInsightsResponseSerializer(serializers.Serializer):
    summary = serializers.CharField()
    highlights = serializers.ListField(child=serializers.CharField())
    alerts = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())
