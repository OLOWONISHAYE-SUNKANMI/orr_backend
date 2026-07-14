"""
Serializers for Client Problem / Request Brief Form.
"""

from rest_framework import serializers
from client.models import ClientRequest, ClientRequestDocument, ClientRequestVersion


class ClientRequestDocumentSerializer(serializers.ModelSerializer):
    """Serializer for request document uploads."""

    class Meta:
        model = ClientRequestDocument
        fields = [
            'id', 'file', 'file_name', 'file_size', 'description',
            'uploaded_by', 'vault_document', 'created_at',
        ]
        read_only_fields = ['id', 'file_name', 'file_size', 'uploaded_by', 'created_at']


class ClientRequestVersionSerializer(serializers.ModelSerializer):
    """Serializer for request version history / audit trail."""
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ClientRequestVersion
        fields = [
            'id', 'version_number', 'changed_by', 'changed_by_name',
            'field_changed', 'old_value', 'new_value', 'change_reason',
            'created_at',
        ]

    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.email
        return None


class ClientRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing requests."""
    client_name = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = ClientRequest
        fields = [
            'id', 'request_id', 'request_title', 'main_request_type',
            'orr_service_area', 'urgency', 'status', 'sensitivity_level',
            'submission_date', 'created_at', 'updated_at',
            'client', 'client_name', 'submitted_by_name', 'document_count',
        ]
        read_only_fields = fields

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company
        return None

    def get_submitted_by_name(self, obj):
        if obj.submitted_by:
            return obj.submitted_by.get_full_name() or obj.submitted_by.email
        return None

    def get_document_count(self, obj):
        return obj.documents.count()


class ClientRequestSerializer(serializers.ModelSerializer):
    """
    Full CRUD serializer for Client Problem / Request Brief Form.
    Handles creation, updates, and read with all fields from the PDF schema.
    """
    documents_list = ClientRequestDocumentSerializer(
        source='documents', many=True, read_only=True
    )
    client_name = serializers.SerializerMethodField()
    submitted_by_name = serializers.SerializerMethodField()
    assigned_pm_name = serializers.SerializerMethodField()

    class Meta:
        model = ClientRequest
        fields = [
            # System linkage
            'id', 'request_id', 'client', 'client_name',
            'submitted_by', 'submitted_by_name', 'submission_date',
            # Request basics
            'request_title', 'main_request_type', 'orr_service_area',
            # Problem detail
            'short_description', 'desired_outcome', 'background_context',
            'main_question', 'current_challenge', 'actions_taken', 'decision_needed',
            # Scope & expectations
            'expected_support', 'expected_deliverable', 'urgency',
            'target_date', 'budget_expectation',
            # Sector / domain
            'sector', 'jurisdiction', 'location',
            # Documents
            'has_documents',
            # Confidentiality
            'sensitivity_level', 'confidentiality_agreed',
            # Communication
            'preferred_next_step', 'preferred_contact_method',
            'preferred_meeting_language',
            # Compliance / declaration
            'confirm_accuracy', 'confirm_authority',
            'confirm_no_emergency', 'ai_processing_notice',
            # Status
            'status',
            # Internal review (read-only for clients)
            'admin_classification', 'admin_review_notes',
            'assigned_pm', 'assigned_pm_name', 'converted_project',
            # Audit
            'last_updated_by', 'created_at', 'updated_at',
            # Nested
            'documents_list',
        ]
        read_only_fields = [
            'id', 'request_id', 'submission_date', 'client', 'submitted_by',
            'admin_classification', 'admin_review_notes',
            'assigned_pm', 'converted_project',
            'last_updated_by', 'created_at', 'updated_at',
            'documents_list', 'client_name', 'submitted_by_name',
            'assigned_pm_name',
        ]

    def get_client_name(self, obj):
        if obj.client:
            return obj.client.company
        return None

    def get_submitted_by_name(self, obj):
        if obj.submitted_by:
            return obj.submitted_by.get_full_name() or obj.submitted_by.email
        return None

    def get_assigned_pm_name(self, obj):
        if obj.assigned_pm:
            return obj.assigned_pm.get_full_name() or obj.assigned_pm.email
        return None

    def create(self, validated_data):
        """Auto-populate submitted_by and client from the request context."""
        user = self.context['request'].user

        # Auto-set submitted_by
        validated_data['submitted_by'] = user

        # Auto-set client from user's client_profile if not provided
        if 'client' not in validated_data or validated_data['client'] is None:
            from admin_portal.models import Client
            try:
                client = Client.objects.get(user=user)
                validated_data['client'] = client
            except Client.DoesNotExist:
                raise serializers.ValidationError(
                    {"client": "No client profile found. Please complete onboarding first."}
                )

        validated_data['last_updated_by'] = user

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Track last_updated_by on every update."""
        user = self.context['request'].user
        validated_data['last_updated_by'] = user
        return super().update(instance, validated_data)


class ClientRequestAdminReviewSerializer(serializers.Serializer):
    """
    Serializer for Admin review actions.
    Admin can reclassify service area, urgency, sensitivity, and next step.
    """
    action = serializers.ChoiceField(
        choices=[
            'approve_for_meeting',
            'approve_for_pm_assignment',
            'request_clarification',
            'reject',
            'close',
            'archive',
        ],
        help_text="Review action to take."
    )
    admin_classification = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Admin classification notes."
    )
    admin_review_notes = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Admin review notes."
    )
    assigned_pm_id = serializers.IntegerField(
        required=False,
        help_text="User ID of the PM to assign (for approve_for_pm_assignment action)."
    )

    def validate(self, data):
        if data['action'] == 'approve_for_pm_assignment' and not data.get('assigned_pm_id'):
            raise serializers.ValidationError(
                {"assigned_pm_id": "PM assignment is required for this action."}
            )
        return data


class ClientRequestConvertToProjectSerializer(serializers.Serializer):
    """
    Serializer for converting a request into a PM Project.
    """
    project_title = serializers.CharField(
        max_length=300,
        help_text="Title for the new project."
    )
    service_category = serializers.ChoiceField(
        choices=[
            ('strategy_advisory_compliance', 'Strategy Advisory & Compliance'),
            ('operational_systems_infrastructure', 'Operational Systems & Infrastructure'),
            ('living_systems_regeneration', 'Living Systems Regeneration'),
        ],
        help_text="Service category for the project."
    )
