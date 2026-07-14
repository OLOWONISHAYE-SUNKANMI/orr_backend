"""
PM Serializers
Complete serializer layer for all PM models.
"""

from rest_framework import serializers
from django.contrib.auth.models import User

from .models import (
    PMProject, PMProjectVersion, PMProjectDocument,
    PMTask, PMTaskDocument, PMTaskVersion,
    PMConsultantMatch, PMAssignment, PMAssignmentCompliance,
    PMOpportunity,
)


# ═══════════════════════════════════════════════
# Helper Serializers
# ═══════════════════════════════════════════════

class UserMiniSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name']

    def get_full_name(self, obj):
        return obj.get_full_name()


class PMProjectVersionSerializer(serializers.ModelSerializer):
    changed_by = UserMiniSerializer(read_only=True)

    class Meta:
        model = PMProjectVersion
        fields = [
            'id', 'version_number', 'changed_by',
            'field_changed', 'old_value', 'new_value',
            'change_reason', 'created_at',
        ]


class PMProjectDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserMiniSerializer(read_only=True)

    class Meta:
        model = PMProjectDocument
        fields = [
            'id', 'document_type', 'client_document', 'file',
            'file_name', 'uploaded_by', 'created_at',
        ]
        read_only_fields = ['uploaded_by']


class PMTaskVersionSerializer(serializers.ModelSerializer):
    changed_by = UserMiniSerializer(read_only=True)

    class Meta:
        model = PMTaskVersion
        fields = [
            'id', 'version_number', 'changed_by',
            'field_changed', 'old_value', 'new_value',
            'created_at',
        ]


class PMTaskDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = UserMiniSerializer(read_only=True)

    class Meta:
        model = PMTaskDocument
        fields = [
            'id', 'file', 'file_name', 'visibility',
            'uploaded_by', 'created_at',
        ]
        read_only_fields = ['uploaded_by']


# ═══════════════════════════════════════════════
# PROJECT Serializers
# ═══════════════════════════════════════════════

class PMProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project list views."""
    assigned_pm = UserMiniSerializer(read_only=True)
    client_name = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()
    assignment_count = serializers.SerializerMethodField()
    interested_consultants = serializers.SerializerMethodField()
    selected_consultant_id = serializers.SerializerMethodField()

    class Meta:
        model = PMProject
        fields = [
            'id', 'project_id', 'title', 'client', 'client_name',
            'assigned_pm', 'service_category', 'project_type',
            'confidentiality_level', 'urgency', 'status',
            'sourcing_status', 'target_deadline',
            'task_count', 'assignment_count',
            'interested_consultants', 'selected_consultant_id',
            'created_at', 'updated_at',
        ]

    def get_client_name(self, obj):
        return f"{obj.client.user.get_full_name()} - {obj.client.company}" if obj.client else ''

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_assignment_count(self, obj):
        return obj.assignments.count()

    def get_interested_consultants(self, obj):
        consultants = []
        # Get from opportunities where consultant showed interest
        opportunities = obj.opportunities.filter(
            response__in=['interested', 'may_be_interested']
        )
        for opp in opportunities:
            if opp.consultant:
                consultants.append({
                    'id': opp.consultant.id,
                    'name': opp.consultant.user.get_full_name(),
                    'expertise': opp.consultant.specialization.primary_specialization if hasattr(opp.consultant, 'specialization') else '',
                    'cost': 'TBD',
                })
        
        # Also include any auto-matches that haven't been rejected
        matches = obj.consultant_matches.all()
        for match in matches:
            if match.consultant and not any(c['id'] == match.consultant.id for c in consultants):
                consultants.append({
                    'id': match.consultant.id,
                    'name': match.consultant.user.get_full_name(),
                    'expertise': match.consultant.specialization.primary_specialization if hasattr(match.consultant, 'specialization') else '',
                    'cost': 'TBD',
                })
        return consultants

    def get_selected_consultant_id(self, obj):
        assignment = obj.assignments.first()
        if assignment and assignment.consultant:
            return assignment.consultant.id
        return None


class PMProjectDetailSerializer(serializers.ModelSerializer):
    """Full serializer for project detail views."""
    assigned_pm = UserMiniSerializer(read_only=True)
    admin_reviewer = UserMiniSerializer(read_only=True)
    client_name = serializers.SerializerMethodField()
    documents = PMProjectDocumentSerializer(many=True, read_only=True)
    versions = PMProjectVersionSerializer(many=True, read_only=True)
    interested_consultants = serializers.SerializerMethodField()
    selected_consultant_id = serializers.SerializerMethodField()

    class Meta:
        model = PMProject
        fields = '__all__'
        read_only_fields = ['project_id', 'created_at', 'updated_at']

    def get_client_name(self, obj):
        return f"{obj.client.user.get_full_name()} - {obj.client.company}" if obj.client else ''

    def get_interested_consultants(self, obj):
        consultants = []
        opportunities = obj.opportunities.filter(
            response__in=['interested', 'may_be_interested']
        )
        for opp in opportunities:
            if opp.consultant:
                consultants.append({
                    'id': opp.consultant.id,
                    'name': opp.consultant.user.get_full_name(),
                    'expertise': opp.consultant.specialization.primary_specialization if hasattr(opp.consultant, 'specialization') else '',
                    'cost': 'TBD',
                })
        
        matches = obj.consultant_matches.all()
        for match in matches:
            if match.consultant and not any(c['id'] == match.consultant.id for c in consultants):
                consultants.append({
                    'id': match.consultant.id,
                    'name': match.consultant.user.get_full_name(),
                    'expertise': match.consultant.specialization.primary_specialization if hasattr(match.consultant, 'specialization') else '',
                    'cost': 'TBD',
                })
        return consultants

    def get_selected_consultant_id(self, obj):
        assignment = obj.assignments.first()
        if assignment and assignment.consultant:
            return assignment.consultant.id
        return None


class PMProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating projects."""

    class Meta:
        model = PMProject
        fields = [
            'client', 'title', 'service_category', 'secondary_categories',
            'project_type', 'complexity', 'confidentiality_level', 'urgency',
            'client_objective', 'main_problem', 'proposed_scope', 'out_of_scope',
            'expected_deliverable', 'deliverable_description',
            'target_start_date', 'target_deadline',
            'internal_review_deadline', 'client_delivery_deadline',
            'num_consultants_required', 'required_expertise',
            'suggested_consultants', 'required_languages', 'work_mode_required',
            'internal_pm_notes', 'client_facing_notes',
            'estimated_hours', 'estimated_budget', 'currency',
            'billing_type', 'payment_status',
            'client_approval_needed', 'send_summary_to_client',
            'status', 'pm_approved_summary', 'consultant_facing_summary',
        ]

    def create(self, validated_data):
        # Auto-set the PM to the requesting user
        validated_data['assigned_pm'] = self.context['request'].user
        return super().create(validated_data)


# ═══════════════════════════════════════════════
# TASK Serializers
# ═══════════════════════════════════════════════

class PMTaskListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for task list views."""
    assigned_to = UserMiniSerializer(read_only=True)
    sub_task_count = serializers.SerializerMethodField()
    project_id_display = serializers.CharField(source='project.project_id', read_only=True)

    class Meta:
        model = PMTask
        fields = [
            'id', 'task_id', 'project', 'project_id_display',
            'parent_task', 'title', 'task_type', 'task_structure',
            'assigned_to', 'responsible_role', 'priority',
            'status', 'due_date', 'start_date',
            'estimated_hours', 'actual_hours', 'billable_status',
            'pm_review_required', 'admin_review_required',
            'review_outcome', 'sub_task_count',
            'created_at', 'updated_at',
        ]

    def get_sub_task_count(self, obj):
        return obj.sub_tasks.count()


class PMTaskDetailSerializer(serializers.ModelSerializer):
    """Full serializer for task detail views."""
    assigned_to = UserMiniSerializer(read_only=True)
    created_by = UserMiniSerializer(read_only=True)
    supporting_users = UserMiniSerializer(many=True, read_only=True)
    documents = PMTaskDocumentSerializer(many=True, read_only=True)
    versions = PMTaskVersionSerializer(many=True, read_only=True)
    sub_tasks = serializers.SerializerMethodField()

    class Meta:
        model = PMTask
        fields = '__all__'
        read_only_fields = ['task_id', 'created_at', 'updated_at', 'completion_date']

    def get_sub_tasks(self, obj):
        sub_tasks = obj.sub_tasks.all()
        return PMTaskListSerializer(sub_tasks, many=True).data


class PMTaskCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating tasks."""
    supporting_user_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )
    dependency_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    class Meta:
        model = PMTask
        fields = [
            'project', 'parent_task', 'title', 'task_type',
            'description', 'objective', 'expected_output',
            'task_structure', 'related_milestone',
            'assigned_to', 'responsible_role',
            'supporting_user_ids', 'dependency_ids',
            'consultant_access_required', 'client_input_required',
            'start_date', 'due_date', 'internal_review_date', 'priority',
            'document_visibility', 'internal_notes',
            'client_facing_notes', 'consultant_instructions',
            'estimated_hours', 'billable_status',
            'pm_review_required', 'admin_review_required',
            'notify_assigned_user', 'notify_pm_on_completion', 'notify_admin',
            'status',
        ]

    def create(self, validated_data):
        supporting_ids = validated_data.pop('supporting_user_ids', [])
        dependency_ids = validated_data.pop('dependency_ids', [])
        validated_data['created_by'] = self.context['request'].user

        # Auto-set as sub_task if parent_task is provided
        if validated_data.get('parent_task'):
            validated_data['task_structure'] = 'sub_task'

        task = super().create(validated_data)

        if supporting_ids:
            task.supporting_users.set(User.objects.filter(id__in=supporting_ids))
        if dependency_ids:
            task.dependencies.set(PMTask.objects.filter(id__in=dependency_ids))
            
        # Sync to Consultant Portal if assigned to a consultant
        assigned_user = task.assigned_to
        if assigned_user and hasattr(assigned_user, 'consultant'):
            from consultation.models import ConsultantTask, ConsultantJob
            from pm.models import PMAssignment
            
            # Find or create a ConsultantJob representation for this project assignment
            assignment = PMAssignment.objects.filter(
                project=task.project,
                consultant=assigned_user.consultant
            ).first()
            
            if assignment:
                desc = assignment.assignment_scope or task.project.client_objective or 'Auto-generated job for PM project.'
            else:
                desc = task.project.client_objective or 'Auto-generated job for PM project.'

            job, _ = ConsultantJob.objects.get_or_create(
                consultant=assigned_user.consultant,
                title=f"Assignment: {task.project.title}",
                defaults={
                    'industry': task.project.service_category or 'Consulting',
                    'client_sector': 'TBD',
                    'description': desc,
                    'status': 'ACTIVE'
                }
            )
            
            # Map PM status -> Consultant status (1:1 for matching Kanban boards)
            STATUS_MAP = {
                'draft': 'NOT_STARTED',
                'not_started': 'NOT_STARTED',
                'awaiting_assignment': 'ASSIGNED',
                'awaiting_client_input': 'ASSIGNED',
                'in_progress': 'IN_PROGRESS',
                'submitted_for_review': 'UNDER_REVIEW',
                'revision_required': 'IN_PROGRESS',
                'blocked': 'BLOCKED',
                'on_hold': 'BLOCKED',
                'completed': 'COMPLETED',
                'cancelled': 'COMPLETED',
            }
            pm_status = task.status or 'not_started'
            mapped_status = STATUS_MAP.get(pm_status, 'ASSIGNED')

            PRIORITY_MAP = {
                'low': 'LOW',
                'normal': 'MEDIUM',
                'priority': 'HIGH',
                'urgent': 'HIGH',
                'critical': 'HIGH',
            }
            mapped_priority = PRIORITY_MAP.get(task.priority, 'MEDIUM') if task.priority else 'MEDIUM'

            ConsultantTask.objects.create(
                job=job,
                pm_task_id=task.task_id,
                title=task.title,
                description=task.description or '',
                due_date=task.due_date,
                priority=mapped_priority,
                status=mapped_status
            )

        return task

    def update(self, instance, validated_data):
        supporting_ids = validated_data.pop('supporting_user_ids', None)
        dependency_ids = validated_data.pop('dependency_ids', None)

        instance = super().update(instance, validated_data)

        if supporting_ids is not None:
            instance.supporting_users.set(User.objects.filter(id__in=supporting_ids))
        if dependency_ids is not None:
            instance.dependencies.set(PMTask.objects.filter(id__in=dependency_ids))

        # Sync to Consultant Portal if a linked task exists
        from consultation.models import ConsultantTask
        
        # Map PM status -> Consultant status (1:1 for matching Kanban boards)
        STATUS_MAP = {
            'draft': 'NOT_STARTED',
            'not_started': 'NOT_STARTED',
            'awaiting_assignment': 'ASSIGNED',
            'awaiting_client_input': 'ASSIGNED',
            'in_progress': 'IN_PROGRESS',
            'submitted_for_review': 'UNDER_REVIEW',
            'revision_required': 'IN_PROGRESS',
            'blocked': 'BLOCKED',
            'on_hold': 'BLOCKED',
            'completed': 'COMPLETED',
            'cancelled': 'COMPLETED',
        }
        pm_status = instance.status or 'not_started'
        mapped_status = STATUS_MAP.get(pm_status, 'ASSIGNED')

        PRIORITY_MAP = {
            'low': 'LOW',
            'normal': 'MEDIUM',
            'priority': 'HIGH',
            'urgent': 'HIGH',
            'critical': 'HIGH',
        }
        mapped_priority = PRIORITY_MAP.get(instance.priority, 'MEDIUM') if instance.priority else 'MEDIUM'

        c_task = ConsultantTask.objects.filter(pm_task_id=instance.task_id).first()

        if not c_task:
            # Fallback for older tasks
            c_task = ConsultantTask.objects.filter(title=instance.title).first()
            if c_task:
                c_task.pm_task_id = instance.task_id
        
        if c_task:
                c_task.status = mapped_status
                c_task.title = instance.title
                c_task.description = instance.description or ''
                c_task.due_date = instance.due_date
                c_task.priority = mapped_priority
                c_task.save(update_fields=['status', 'title', 'description', 'due_date', 'priority'])

        return instance


# ═══════════════════════════════════════════════
# CONSULTANT MATCHING Serializers
# ═══════════════════════════════════════════════

class PMConsultantMatchSerializer(serializers.ModelSerializer):
    consultant_name = serializers.SerializerMethodField()
    consultant_number = serializers.CharField(
        source='consultant.consultant_number', read_only=True
    )
    specialization = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()

    class Meta:
        model = PMConsultantMatch
        fields = [
            'id', 'project', 'consultant', 'consultant_name',
            'consultant_number', 'specialization', 'skills',
            'availability', 'match_score', 'match_label',
            'match_reason', 'is_manually_added', 'created_at',
        ]

    def get_consultant_name(self, obj):
        return obj.consultant.user.get_full_name()

    def get_specialization(self, obj):
        try:
            return obj.consultant.specialization.primary_specialization
        except Exception:
            return ''

    def get_skills(self, obj):
        return list(obj.consultant.skills.values_list('skill_name', flat=True))

    def get_availability(self, obj):
        try:
            return obj.consultant.work_preference.is_available
        except Exception:
            return None


# ═══════════════════════════════════════════════
# ASSIGNMENT Serializers
# ═══════════════════════════════════════════════

class PMAssignmentSerializer(serializers.ModelSerializer):
    """Full assignment serializer."""
    consultant_name = serializers.SerializerMethodField()
    assigned_by = UserMiniSerializer(read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    compliance = serializers.SerializerMethodField()

    class Meta:
        model = PMAssignment
        fields = '__all__'
        read_only_fields = [
            'assignment_id', 'created_at', 'updated_at',
            'invitation_sent_at', 'acceptance_timestamp',
            'access_activation_date',
        ]

    def get_consultant_name(self, obj):
        return obj.consultant.user.get_full_name()

    def get_compliance(self, obj):
        try:
            return PMAssignmentComplianceSerializer(obj.compliance).data
        except PMAssignmentCompliance.DoesNotExist:
            return None


class PMAssignmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating assignments."""
    document_access_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, write_only=True
    )

    class Meta:
        model = PMAssignment
        fields = [
            'project', 'consultant',
            'assignment_role', 'assignment_scope', 'expected_output',
            'estimated_hours', 'assignment_deadline', 'priority',
            'project_access_level', 'document_access_ids',
            'client_identity_visibility', 'client_communication_permission',
            'conflict_declaration_required',
            'confidentiality_reconfirmation_required',
            'assignment_budget', 'currency', 'payment_basis',
            'invitation_message',
        ]

    def create(self, validated_data):
        doc_ids = validated_data.pop('document_access_ids', [])
        validated_data['assigned_by'] = self.context['request'].user
        assignment = super().create(validated_data)

        if doc_ids:
            assignment.document_access.set(
                PMProjectDocument.objects.filter(id__in=doc_ids)
            )
        return assignment


class PMAssignmentComplianceSerializer(serializers.ModelSerializer):
    """Serializer for consultant compliance declarations."""
    is_complete = serializers.SerializerMethodField()

    class Meta:
        model = PMAssignmentCompliance
        fields = [
            'id', 'assignment', 'conflict_declaration', 'conflict_details',
            'confidentiality_reconfirmation', 'data_handling_confirmation',
            'acceptance_confirmation', 'completed_at', 'is_complete',
        ]
        read_only_fields = ['completed_at']

    def get_is_complete(self, obj):
        return obj.is_complete()


# ═══════════════════════════════════════════════
# OPPORTUNITY Serializers
# ═══════════════════════════════════════════════

class PMOpportunityListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for consultant opportunity list."""
    project_title = serializers.CharField(source='project.title', read_only=True)
    service_category = serializers.CharField(
        source='project.service_category', read_only=True
    )
    urgency = serializers.CharField(source='project.urgency', read_only=True)
    deadline = serializers.DateField(source='project.target_deadline', read_only=True)

    class Meta:
        model = PMOpportunity
        fields = [
            'id', 'opportunity_id', 'project', 'project_title',
            'service_category', 'urgency', 'deadline',
            'response', 'response_status',
            'is_external_consultant', 'created_at',
        ]


class PMOpportunityDetailSerializer(serializers.ModelSerializer):
    """Full opportunity detail for consultant view."""
    project_title = serializers.CharField(source='project.title', read_only=True)
    project_summary = serializers.SerializerMethodField()
    required_expertise = serializers.JSONField(
        source='project.required_expertise', read_only=True
    )
    required_languages = serializers.JSONField(
        source='project.required_languages', read_only=True
    )
    work_mode = serializers.JSONField(
        source='project.work_mode_required', read_only=True
    )
    expected_deliverable = serializers.JSONField(
        source='project.expected_deliverable', read_only=True
    )
    deadline = serializers.DateField(source='project.target_deadline', read_only=True)

    class Meta:
        model = PMOpportunity
        fields = [
            'id', 'opportunity_id', 'project', 'project_title',
            'project_summary', 'required_expertise',
            'required_languages', 'work_mode', 'expected_deliverable',
            'deadline', 'summary_version_sent',
            'response', 'response_status', 'interest_statement',
            'relevant_experience', 'availability_confirmation',
            'clarification_request', 'decline_reason', 'decline_reason_detail',
            'shortlisted_status', 'is_selected',
            'is_external_consultant', 'created_at', 'updated_at',
        ]

    def get_project_summary(self, obj):
        """Return appropriate summary based on consultant type."""
        if obj.is_external_consultant:
            return obj.project.restricted_external_summary
        return obj.project.consultant_facing_summary


class PMOpportunityResponseSerializer(serializers.Serializer):
    """Serializer for consultant opportunity response submission."""
    response = serializers.ChoiceField(
        choices=PMOpportunity.RESPONSE_CHOICES
    )
    interest_statement = serializers.CharField(required=False, allow_blank=True)
    relevant_experience = serializers.CharField(required=False, allow_blank=True)
    availability_confirmation = serializers.CharField(required=False, allow_blank=True)
    clarification_request = serializers.CharField(required=False, allow_blank=True)
    decline_reason = serializers.ChoiceField(
        choices=PMOpportunity.DECLINE_REASON_CHOICES,
        required=False, allow_blank=True
    )
    decline_reason_detail = serializers.CharField(required=False, allow_blank=True)


# ═══════════════════════════════════════════════
# MEETINGS Serializer
# ═══════════════════════════════════════════════

from consultation.models import ConsultantMeeting

class PMMeetingSerializer(serializers.ModelSerializer):
    consultant_name = serializers.SerializerMethodField()
    consultant_number = serializers.CharField(source='consultant.consultant_number', read_only=True)
    
    class Meta:
        model = ConsultantMeeting
        fields = [
            'id', 'consultant', 'consultant_name', 'consultant_number',
            'title', 'start_time', 'end_time', 'join_link', 'status',
            'created_at', 'updated_at'
        ]

    def get_consultant_name(self, obj):
        try:
            name = f"{obj.consultant.user.first_name} {obj.consultant.user.last_name}".strip()
            return name if name else obj.consultant.consultant_number
        except AttributeError:
            return obj.consultant.consultant_number
