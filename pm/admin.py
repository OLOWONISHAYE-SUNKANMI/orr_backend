from django.contrib import admin
from .models import (
    PMProject, PMProjectVersion, PMProjectDocument,
    PMTask, PMTaskDocument, PMTaskVersion,
    PMConsultantMatch, PMAssignment, PMAssignmentCompliance,
    PMOpportunity
)

@admin.register(PMProject)
class PMProjectAdmin(admin.ModelAdmin):
    list_display = ('project_id', 'title', 'client', 'assigned_pm', 'status', 'target_deadline')
    list_filter = ('status', 'service_category', 'project_type', 'urgency')
    search_fields = ('project_id', 'title', 'client__company')

@admin.register(PMProjectVersion)
class PMProjectVersionAdmin(admin.ModelAdmin):
    list_display = ('project', 'version_number', 'field_changed', 'changed_by', 'created_at')
    list_filter = ('field_changed',)
    search_fields = ('project__project_id', 'project__title')

@admin.register(PMProjectDocument)
class PMProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('project', 'file_name', 'document_type', 'uploaded_by', 'created_at')
    list_filter = ('document_type',)

@admin.register(PMTask)
class PMTaskAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'project', 'title', 'task_type', 'assigned_to', 'status', 'due_date')
    list_filter = ('status', 'task_type', 'priority', 'task_structure')
    search_fields = ('task_id', 'title', 'project__project_id')

@admin.register(PMTaskDocument)
class PMTaskDocumentAdmin(admin.ModelAdmin):
    list_display = ('task', 'file_name', 'visibility', 'uploaded_by', 'created_at')
    list_filter = ('visibility',)

@admin.register(PMTaskVersion)
class PMTaskVersionAdmin(admin.ModelAdmin):
    list_display = ('task', 'version_number', 'field_changed', 'changed_by', 'created_at')

@admin.register(PMConsultantMatch)
class PMConsultantMatchAdmin(admin.ModelAdmin):
    list_display = ('project', 'consultant', 'match_score', 'match_label', 'is_manually_added')
    list_filter = ('match_label', 'is_manually_added')
    search_fields = ('project__project_id', 'consultant__consultant_number')

@admin.register(PMAssignment)
class PMAssignmentAdmin(admin.ModelAdmin):
    list_display = ('assignment_id', 'project', 'consultant', 'assignment_role', 'status', 'assignment_deadline')
    list_filter = ('status', 'assignment_role', 'priority')
    search_fields = ('assignment_id', 'project__project_id', 'consultant__consultant_number')

@admin.register(PMAssignmentCompliance)
class PMAssignmentComplianceAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'conflict_declaration', 'confidentiality_reconfirmation', 'completed_at')

@admin.register(PMOpportunity)
class PMOpportunityAdmin(admin.ModelAdmin):
    list_display = ('opportunity_id', 'project', 'consultant', 'response_status', 'is_external_consultant')
    list_filter = ('response_status', 'response', 'is_external_consultant', 'shortlisted_status')
    search_fields = ('opportunity_id', 'project__project_id', 'consultant__consultant_number', 'external_email')
