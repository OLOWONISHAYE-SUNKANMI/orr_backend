from rest_framework import serializers

from admin_portal.models import Client, Meeting, SystemNotification, Ticket


class DashboardStatsSerializer(serializers.Serializer):
    """Dashboard overview statistics"""

    active_clients = serializers.IntegerField()
    active_clients_link = serializers.CharField()
    pending_tickets = serializers.DictField()
    upcoming_meetings = serializers.IntegerField()
    system_notifications = serializers.IntegerField()
    portal_logins_7days = serializers.IntegerField()
    ai_chat_sessions = serializers.IntegerField()
    escalation_rate = serializers.FloatField()
    most_used_resources = serializers.ListField()
    pending_technical_feedback = serializers.IntegerField(required=False)


class QuickClientSerializer(serializers.ModelSerializer):
    """Quick client info for dashboard"""

    full_name = serializers.CharField(source="user.get_full_name")
    email = serializers.CharField(source="user.email")

    class Meta:
        model = Client
        fields = ["id", "full_name", "email", "company", "stage", "last_activity"]


class QuickTicketSerializer(serializers.ModelSerializer):
    """Quick ticket info for dashboard"""

    client_name = serializers.CharField(source="client.user.get_full_name")

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_id",
            "subject",
            "status",
            "priority",
            "client_name",
            "created_at",
        ]


class QuickMeetingSerializer(serializers.ModelSerializer):
    """Quick meeting info for dashboard"""

    client_name = serializers.CharField(source="client.user.get_full_name")

    class Meta:
        model = Meeting
        fields = ["id", "client_name", "meeting_type", "requested_datetime", "status"]
