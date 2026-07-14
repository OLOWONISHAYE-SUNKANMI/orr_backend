"""
ORR Project Management Models
Implements the full PM workflow as defined in the PM documentation:
- Project Creation Schema
- Task / Sub-Task Creation Schema
- Consultant Matching / Assignment Schema
- Consultant Opportunity Response / Assignment Acceptance Schema
- PM Workflow (27-step lifecycle)
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from common.models import Audit


# ═══════════════════════════════════════════════════════════
# 1. PROJECT
# ═══════════════════════════════════════════════════════════

class PMProject(Audit):
    """
    Full project record created by PM, linked to an approved client.
    Covers the Project Creation Schema and PM Workflow steps 1–14.
    """

    # ── Status choices (drive portal visibility and workflow permissions) ──
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('awaiting_client_confirmation', 'Awaiting Client Confirmation'),
        ('awaiting_payment', 'Awaiting Payment'),
        ('pending_admin_review', 'Pending Admin Review'),
        ('needs_pm_clarification', 'Needs PM Clarification'),
        ('approved_for_sourcing', 'Approved for Consultant Sourcing'),
        ('ready_for_matching', 'Ready for Consultant Matching'),
        ('sourcing_internally', 'Sourcing Internally'),
        ('sourcing_externally', 'Sourcing Externally'),
        ('consultant_assignment_pending', 'Consultant Assignment Pending'),
        ('active', 'Active'),
        ('internal_review', 'Internal Review'),
        ('delivered', 'Delivered'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]

    SERVICE_CATEGORY_CHOICES = [
        ('strategy_advisory_compliance', 'Strategy Advisory & Compliance'),
        ('operational_systems_infrastructure', 'Operational Systems & Infrastructure'),
        ('living_systems_regeneration', 'Living Systems Regeneration'),
    ]

    PROJECT_TYPE_CHOICES = [
        ('initial_advisory', 'Initial Advisory'),
        ('diagnostic_review', 'Diagnostic Review'),
        ('report_written_opinion', 'Report / Written Opinion'),
        ('implementation_support', 'Implementation Support'),
        ('compliance_support', 'Compliance Support'),
        ('operational_setup', 'Operational Setup'),
        ('retainer_workstream', 'Retainer Workstream'),
        ('technical_review', 'Technical Review'),
        ('other', 'Other'),
    ]

    COMPLEXITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('specialist_multidisciplinary', 'Specialist / Multi-disciplinary'),
    ]

    CONFIDENTIALITY_CHOICES = [
        ('standard', 'Standard'),
        ('confidential', 'Confidential'),
        ('highly_confidential', 'Highly Confidential'),
        ('restricted_access', 'Restricted Access'),
    ]

    URGENCY_CHOICES = [
        ('normal', 'Normal'),
        ('priority', 'Priority'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ]

    DELIVERABLE_CHOICES = [
        ('meeting_summary', 'Meeting Summary'),
        ('advisory_note', 'Advisory Note'),
        ('written_report', 'Written Report'),
        ('compliance_review', 'Compliance Review'),
        ('technical_specification', 'Technical Specification'),
        ('implementation_plan', 'Implementation Plan'),
        ('project_roadmap', 'Project Roadmap'),
        ('risk_assessment', 'Risk Assessment'),
        ('document_review', 'Document Review'),
        ('client_presentation', 'Client Presentation'),
        ('other', 'Other'),
    ]

    BILLING_TYPE_CHOICES = [
        ('first_report', 'First Report'),
        ('fixed_fee', 'Fixed Fee'),
        ('hourly', 'Hourly'),
        ('retainer', 'Retainer'),
        ('included_in_retainer', 'Included in Existing Retainer'),
        ('to_be_confirmed', 'To Be Confirmed'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('not_required_yet', 'Not Required Yet'),
        ('pending_payment', 'Pending Payment'),
        ('paid', 'Paid'),
        ('included_in_retainer', 'Included in Retainer'),
        ('admin_confirmation_required', 'Admin Confirmation Required'),
    ]

    WORK_MODE_CHOICES = [
        ('remote', 'Remote'),
        ('on_site', 'On-site'),
        ('hybrid', 'Hybrid'),
    ]

    # ── System-generated fields ──
    project_id = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text="Auto-generated: ORR-PROJ-000001"
    )

    # ── Linkages ──
    client = models.ForeignKey(
        'admin_portal.Client', on_delete=models.CASCADE, related_name='pm_projects',
        help_text="The approved client this project is linked to."
    )
    assigned_pm = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pm_managed_projects',
        help_text="The PM responsible for this project."
    )

    # ── Project Basics ──
    title = models.CharField(max_length=300)
    service_category = models.CharField(
        max_length=50, choices=SERVICE_CATEGORY_CHOICES
    )
    secondary_categories = models.JSONField(
        default=list, blank=True,
        help_text="Additional service categories. No duplicate of primary."
    )

    # ── AI & PM Summaries ──
    ai_generated_summary = models.TextField(
        blank=True,
        help_text="Original AI-generated project summary."
    )
    pm_approved_summary = models.TextField(
        blank=True,
        help_text="PM-reviewed and approved version of the summary."
    )
    consultant_facing_summary = models.TextField(
        blank=True,
        help_text="Admin-approved summary for consultant circulation."
    )
    restricted_external_summary = models.TextField(
        blank=True,
        help_text="Restricted version for external (non-onboarded) consultants."
    )

    # ── Project Classification ──
    project_type = models.CharField(
        max_length=30, choices=PROJECT_TYPE_CHOICES, default='other'
    )
    complexity = models.CharField(
        max_length=30, choices=COMPLEXITY_CHOICES, default='medium'
    )
    confidentiality_level = models.CharField(
        max_length=30, choices=CONFIDENTIALITY_CHOICES, default='standard'
    )
    urgency = models.CharField(
        max_length=10, choices=URGENCY_CHOICES, default='normal'
    )

    # ── Scope ──
    client_objective = models.TextField(
        blank=True, help_text="What does the client want to achieve?"
    )
    main_problem = models.TextField(
        blank=True,
        help_text="Core problem, question, or decision ORR is being asked to address."
    )
    proposed_scope = models.TextField(
        blank=True,
        help_text="What ORR will review, analyse, prepare, implement, or advise on."
    )
    out_of_scope = models.TextField(
        blank=True,
        help_text="Anything specifically excluded from this project."
    )
    expected_deliverable = models.JSONField(
        default=list, blank=True,
        help_text="Selected deliverable types (multi-select)."
    )
    deliverable_description = models.TextField(
        blank=True,
        help_text="Detailed description of the expected deliverable."
    )

    # ── Timeline ──
    target_start_date = models.DateField(null=True, blank=True)
    target_deadline = models.DateField(null=True, blank=True)
    internal_review_deadline = models.DateField(null=True, blank=True)
    client_delivery_deadline = models.DateField(null=True, blank=True)

    # ── Resources ──
    num_consultants_required = models.PositiveIntegerField(default=1)
    required_expertise = models.JSONField(
        default=list, blank=True,
        help_text="Skills from approved consultant skills database."
    )
    suggested_consultants = models.JSONField(
        default=list, blank=True,
        help_text="Consultant IDs the PM would like to consider."
    )
    required_languages = models.JSONField(
        default=list, blank=True,
        help_text="Working languages required."
    )
    work_mode_required = models.JSONField(
        default=list, blank=True,
        help_text="Remote / On-site / Hybrid."
    )

    # ── PM Notes ──
    internal_pm_notes = models.TextField(
        blank=True,
        help_text="Internal notes for ORR only. Not visible to client."
    )
    client_facing_notes = models.TextField(
        blank=True,
        help_text="Notes that may be shared with the client."
    )

    # ── Commercial ──
    estimated_hours = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    estimated_budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=5, default='EUR', blank=True)
    billing_type = models.CharField(
        max_length=30, choices=BILLING_TYPE_CHOICES, default='to_be_confirmed'
    )
    payment_status = models.CharField(
        max_length=30, choices=PAYMENT_STATUS_CHOICES, default='not_required_yet'
    )

    # ── Client Communication ──
    client_approval_needed = models.BooleanField(
        default=False,
        help_text="Does the client need to approve scope before work starts?"
    )
    send_summary_to_client = models.BooleanField(
        default=False,
        help_text="Send a project summary to the client for confirmation."
    )

    # ── Admin Review ──
    admin_reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pm_reviewed_projects',
    )
    admin_review_notes = models.TextField(blank=True)
    admin_clarification_questions = models.TextField(blank=True)

    # ── Consultant Sourcing ──
    sourcing_status = models.CharField(
        max_length=30, default='not_started', blank=True,
        choices=[
            ('not_started', 'Not Started'),
            ('pm_input_required', 'PM Input Required'),
            ('summary_draft', 'Summary Draft Created'),
            ('summary_under_review', 'Summary Under Review'),
            ('summary_approved', 'Summary Approved for Circulation'),
            ('internal_sourcing', 'Internal Sourcing'),
            ('external_sourcing', 'External Sourcing'),
            ('sourcing_complete', 'Sourcing Complete'),
        ]
    )

    # ── Status ──
    status = models.CharField(
        max_length=40, choices=STATUS_CHOICES, default='draft'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'PM Project'
        verbose_name_plural = 'PM Projects'

    def __str__(self):
        return f"{self.project_id} - {self.title}"


class PMProjectVersion(Audit):
    """Track version history of major project changes."""
    project = models.ForeignKey(
        PMProject, on_delete=models.CASCADE, related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    change_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.project.project_id} v{self.version_number} - {self.field_changed}"


class PMProjectDocument(Audit):
    """Documents linked to or uploaded for a project."""
    DOC_TYPE_CHOICES = [
        ('linked_client_doc', 'Linked Client Document'),
        ('pm_upload', 'PM Upload'),
        ('consultant_upload', 'Consultant Upload'),
        ('admin_upload', 'Admin Upload'),
    ]

    project = models.ForeignKey(
        PMProject, on_delete=models.CASCADE, related_name='documents'
    )
    document_type = models.CharField(
        max_length=30, choices=DOC_TYPE_CHOICES, default='pm_upload'
    )
    # Link to existing client vault document (optional)
    client_document = models.ForeignKey(
        'admin_portal.ClientDocument', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pm_project_links',
    )
    file = models.FileField(
        upload_to='pm/project_documents/', null=True, blank=True
    )
    file_name = models.CharField(max_length=300, blank=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return f"{self.file_name} for {self.project.project_id}"


# ═══════════════════════════════════════════════════════════
# 2. TASKS
# ═══════════════════════════════════════════════════════════

class PMTask(Audit):
    """
    Task / Sub-Task within a project.
    Covers the Task Creation Schema.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('not_started', 'Not Started'),
        ('awaiting_assignment', 'Awaiting Assignment'),
        ('awaiting_client_input', 'Awaiting Client Input'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('submitted_for_review', 'Submitted for Review'),
        ('revision_required', 'Revision Required'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]

    TASK_TYPE_CHOICES = [
        ('pm_action', 'PM Action'),
        ('admin_action', 'Admin Action'),
        ('consultant_work', 'Consultant Work'),
        ('client_follow_up', 'Client Follow-up'),
        ('document_review', 'Document Review'),
        ('research', 'Research'),
        ('technical_analysis', 'Technical Analysis'),
        ('drafting', 'Drafting'),
        ('internal_review', 'Internal Review'),
        ('client_deliverable', 'Client Deliverable'),
        ('meeting', 'Meeting'),
        ('other', 'Other'),
    ]

    TASK_STRUCTURE_CHOICES = [
        ('main_task', 'Main Task'),
        ('sub_task', 'Sub-Task'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('priority', 'Priority'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ]

    EXPECTED_OUTPUT_CHOICES = [
        ('note', 'Note'),
        ('comment', 'Comment'),
        ('file_upload', 'File Upload'),
        ('report_section', 'Report Section'),
        ('review_decision', 'Review Decision'),
        ('client_message', 'Client Message'),
        ('meeting_outcome', 'Meeting Outcome'),
        ('technical_recommendation', 'Technical Recommendation'),
        ('completed_checklist', 'Completed Checklist'),
        ('other', 'Other'),
    ]

    RESPONSIBLE_ROLE_CHOICES = [
        ('pm', 'PM'),
        ('admin', 'Admin'),
        ('consultant', 'Consultant'),
        ('reviewer', 'Reviewer'),
        ('client', 'Client'),
        ('system_ai', 'System / AI-assisted'),
    ]

    DOCUMENT_VISIBILITY_CHOICES = [
        ('pm_admin_only', 'PM/Admin only'),
        ('assigned_consultant_only', 'Assigned consultant only'),
        ('project_team', 'Project team'),
        ('client_visible', 'Client-visible'),
        ('restricted_custom', 'Restricted custom access'),
    ]

    BILLABLE_STATUS_CHOICES = [
        ('billable', 'Billable'),
        ('non_billable', 'Non-billable'),
        ('included_in_retainer', 'Included in Retainer'),
        ('internal_orr', 'Internal ORR'),
        ('to_be_confirmed', 'To Be Confirmed'),
    ]

    REVIEW_OUTCOME_CHOICES = [
        ('approved', 'Approved'),
        ('revision_required', 'Revision Required'),
        ('rejected', 'Rejected'),
        ('escalate_to_admin', 'Escalate to Admin'),
    ]

    # ── System-generated ──
    task_id = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text="Auto-generated: ORR-TASK-000001"
    )

    # ── Linkages ──
    project = models.ForeignKey(
        PMProject, on_delete=models.CASCADE, related_name='tasks'
    )
    parent_task = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='sub_tasks',
        help_text="If set, this becomes a sub-task."
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='pm_created_tasks'
    )

    # ── Task Basics ──
    title = models.CharField(max_length=300)
    task_type = models.CharField(
        max_length=30, choices=TASK_TYPE_CHOICES, default='pm_action'
    )
    description = models.TextField()
    objective = models.TextField(blank=True)
    expected_output = models.JSONField(
        default=list, blank=True,
        help_text="Multi-select of expected output types."
    )

    # ── Structure ──
    task_structure = models.CharField(
        max_length=15, choices=TASK_STRUCTURE_CHOICES, default='main_task'
    )
    related_milestone = models.CharField(max_length=200, blank=True)
    dependencies = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='dependent_tasks',
        help_text="Tasks that must be completed first."
    )

    # ── Assignment ──
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pm_assigned_tasks'
    )
    responsible_role = models.CharField(
        max_length=20, choices=RESPONSIBLE_ROLE_CHOICES, default='pm'
    )
    supporting_users = models.ManyToManyField(
        User, blank=True, related_name='pm_supporting_tasks'
    )
    consultant_access_required = models.BooleanField(default=False)
    client_input_required = models.BooleanField(default=False)

    # ── Timeline ──
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    internal_review_date = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='normal'
    )

    # ── Documents & Communication ──
    document_visibility = models.CharField(
        max_length=30, choices=DOCUMENT_VISIBILITY_CHOICES,
        default='pm_admin_only'
    )
    internal_notes = models.TextField(blank=True)
    client_facing_notes = models.TextField(blank=True)
    consultant_instructions = models.TextField(blank=True)

    # ── Commercial / Workload ──
    estimated_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    actual_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    billable_status = models.CharField(
        max_length=25, choices=BILLABLE_STATUS_CHOICES,
        default='to_be_confirmed'
    )

    # ── Status ──
    status = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default='draft'
    )
    blocker_reason = models.TextField(blank=True)
    completion_notes = models.TextField(blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)

    # ── Review ──
    pm_review_required = models.BooleanField(default=True)
    admin_review_required = models.BooleanField(default=False)
    review_outcome = models.CharField(
        max_length=25, choices=REVIEW_OUTCOME_CHOICES, blank=True
    )
    review_comments = models.TextField(blank=True)

    # ── Notifications ──
    notify_assigned_user = models.BooleanField(default=True)
    notify_pm_on_completion = models.BooleanField(default=True)
    notify_admin = models.BooleanField(default=False)

    class Meta:
        ordering = ['priority', 'due_date']
        verbose_name = 'PM Task'
        verbose_name_plural = 'PM Tasks'

    def __str__(self):
        return f"{self.task_id} - {self.title}"


class PMTaskDocument(Audit):
    """Files linked to a specific task."""
    VISIBILITY_CHOICES = PMTask.DOCUMENT_VISIBILITY_CHOICES

    task = models.ForeignKey(
        PMTask, on_delete=models.CASCADE, related_name='documents'
    )
    file = models.FileField(upload_to='pm/task_documents/')
    file_name = models.CharField(max_length=300, blank=True)
    visibility = models.CharField(
        max_length=30, choices=VISIBILITY_CHOICES, default='pm_admin_only'
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )

    def __str__(self):
        return f"{self.file_name} for {self.task.task_id}"


class PMTaskVersion(Audit):
    """Version history for task changes."""
    task = models.ForeignKey(
        PMTask, on_delete=models.CASCADE, related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True
    )
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.task.task_id} v{self.version_number} - {self.field_changed}"


# ═══════════════════════════════════════════════════════════
# 3. CONSULTANT MATCHING & ASSIGNMENT
# ═══════════════════════════════════════════════════════════

class PMConsultantMatch(Audit):
    """
    AI-generated or manual consultant matching results.
    Used during the matching phase before assignment.
    """
    MATCH_LABEL_CHOICES = [
        ('strong_match', 'Strong Match'),
        ('good_match', 'Good Match'),
        ('partial_match', 'Partial Match'),
        ('manual_review', 'Manual Review'),
    ]

    project = models.ForeignKey(
        PMProject, on_delete=models.CASCADE, related_name='consultant_matches'
    )
    consultant = models.ForeignKey(
        'consultation.Consultant', on_delete=models.CASCADE,
        related_name='pm_matches'
    )
    match_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Percentage or score."
    )
    match_label = models.CharField(
        max_length=20, choices=MATCH_LABEL_CHOICES, default='manual_review'
    )
    match_reason = models.TextField(
        blank=True,
        help_text="Explanation of why the consultant was suggested."
    )
    is_manually_added = models.BooleanField(default=False)

    class Meta:
        unique_together = ['project', 'consultant']
        ordering = ['-match_score']

    def __str__(self):
        return f"Match: {self.consultant} for {self.project.project_id}"


class PMAssignment(Audit):
    """
    Formal consultant assignment to a project.
    Covers the Consultant Matching / Assignment Schema.
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('proposed', 'Proposed'),
        ('invitation_sent', 'Invitation Sent'),
        ('pending_consultant_response', 'Pending Consultant Response'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('conflict_review_required', 'Conflict Review Required'),
        ('access_activated', 'Access Activated'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]

    ASSIGNMENT_ROLE_CHOICES = [
        ('consultant', 'Consultant'),
        ('reviewer', 'Reviewer'),
        ('technical_implementer', 'Technical Implementer'),
        ('project_lead', 'Project Lead'),
        ('subject_matter_expert', 'Subject-Matter Expert'),
    ]

    ACCESS_LEVEL_CHOICES = [
        ('no_access_yet', 'No Access Yet'),
        ('assignment_brief_only', 'Assignment Brief Only'),
        ('selected_documents_only', 'Selected Documents Only'),
        ('full_project_workspace', 'Full Project Workspace'),
        ('restricted_custom_access', 'Restricted Custom Access'),
    ]

    CLIENT_VISIBILITY_CHOICES = [
        ('hidden_anonymised', 'Hidden / Anonymised'),
        ('business_name_only', 'Business Name Only'),
        ('full_client_profile', 'Full Client Profile'),
    ]

    CLIENT_COMMUNICATION_CHOICES = [
        ('no_direct_contact', 'No Direct Contact'),
        ('pm_supervised_only', 'PM-supervised Contact Only'),
        ('direct_messaging', 'Direct Portal Messaging Allowed'),
        ('meeting_attendance', 'Meeting Attendance Allowed'),
    ]

    PAYMENT_BASIS_CHOICES = [
        ('hourly', 'Hourly'),
        ('fixed_assignment', 'Fixed Assignment'),
        ('included_in_retainer', 'Included in Retainer'),
        ('internal_review_only', 'Internal Review Only'),
        ('to_be_confirmed', 'To Be Confirmed'),
    ]

    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('priority', 'Priority'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ]

    # ── System-generated ──
    assignment_id = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text="Auto-generated: ORR-ASG-000001"
    )

    # ── Linkages ──
    project = models.ForeignKey(
        PMProject, on_delete=models.CASCADE, related_name='assignments'
    )
    consultant = models.ForeignKey(
        'consultation.Consultant', on_delete=models.CASCADE,
        related_name='pm_assignments'
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='pm_created_assignments'
    )

    # ── Assignment Details ──
    assignment_role = models.CharField(
        max_length=30, choices=ASSIGNMENT_ROLE_CHOICES, default='consultant'
    )
    assignment_scope = models.TextField(
        help_text="Must be specific. Becomes the consultant-facing assignment brief."
    )
    expected_output = models.JSONField(
        default=list, blank=True,
        help_text="Expected output from this consultant."
    )
    estimated_hours = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    assignment_deadline = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='normal'
    )

    # ── Access Control ──
    project_access_level = models.CharField(
        max_length=30, choices=ACCESS_LEVEL_CHOICES, default='no_access_yet'
    )
    document_access = models.ManyToManyField(
        PMProjectDocument, blank=True,
        related_name='accessible_by_assignments',
        help_text="Documents this consultant may access."
    )
    client_identity_visibility = models.CharField(
        max_length=25, choices=CLIENT_VISIBILITY_CHOICES,
        default='hidden_anonymised'
    )
    client_communication_permission = models.CharField(
        max_length=25, choices=CLIENT_COMMUNICATION_CHOICES,
        default='no_direct_contact'
    )

    # ── Compliance ──
    conflict_declaration_required = models.BooleanField(default=True)
    confidentiality_reconfirmation_required = models.BooleanField(default=True)

    # ── Commercial ──
    consultant_rate_visibility = models.CharField(
        max_length=30, default='admin_only', blank=True
    )
    assignment_budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=5, default='EUR', blank=True)
    payment_basis = models.CharField(
        max_length=25, choices=PAYMENT_BASIS_CHOICES,
        default='to_be_confirmed'
    )

    # ── Invitation ──
    invitation_message = models.TextField(
        blank=True,
        help_text="AI-generated or PM-edited invitation message."
    )
    invitation_sent_at = models.DateTimeField(null=True, blank=True)

    # ── Consultant Response ──
    response_status = models.CharField(
        max_length=25, default='pending', blank=True,
        choices=[
            ('pending', 'Pending'),
            ('accepted', 'Accepted'),
            ('declined', 'Declined'),
            ('needs_clarification', 'Needs Clarification'),
            ('expired', 'Expired'),
        ]
    )
    consultant_clarification = models.TextField(blank=True)
    acceptance_timestamp = models.DateTimeField(null=True, blank=True)

    # ── Status ──
    status = models.CharField(
        max_length=35, choices=STATUS_CHOICES, default='draft'
    )
    access_activation_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'PM Assignment'
        verbose_name_plural = 'PM Assignments'

    def __str__(self):
        return f"{self.assignment_id} - {self.consultant} on {self.project.project_id}"


class PMAssignmentCompliance(Audit):
    """
    Project-specific compliance declarations from the consultant.
    Must be completed before access is activated.
    """
    assignment = models.OneToOneField(
        PMAssignment, on_delete=models.CASCADE, related_name='compliance'
    )
    conflict_declaration = models.BooleanField(
        default=False,
        help_text="Consultant confirms no conflict of interest."
    )
    conflict_details = models.TextField(
        blank=True,
        help_text="If conflict exists, describe it here."
    )
    confidentiality_reconfirmation = models.BooleanField(
        default=False,
        help_text="Consultant reconfirms confidentiality."
    )
    data_handling_confirmation = models.BooleanField(
        default=False,
        help_text="Consultant agrees to handle data per ORR instructions."
    )
    acceptance_confirmation = models.BooleanField(
        default=False,
        help_text="Consultant confirms review of scope, output, deadline, and access conditions."
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    def is_complete(self):
        """Check if all required compliance declarations are done."""
        return (
            self.conflict_declaration
            and self.confidentiality_reconfirmation
            and self.data_handling_confirmation
            and self.acceptance_confirmation
            and not self.conflict_details  # No undisclosed conflicts
        )

    def __str__(self):
        return f"Compliance for {self.assignment.assignment_id}"


# ═══════════════════════════════════════════════════════════
# 4. CONSULTANT OPPORTUNITIES
# ═══════════════════════════════════════════════════════════

class PMOpportunity(Audit):
    """
    Opportunity notice sent to consultants.
    Covers the Consultant Opportunity Response / Assignment Acceptance Schema.
    """

    RESPONSE_CHOICES = [
        ('not_responded', 'Not Responded'),
        ('interested', 'I am interested'),
        ('may_be_interested', 'I may be interested — I need more detail'),
        ('need_clarification', 'I need clarification before deciding'),
        ('not_interested', 'Not interested at this time'),
        ('declined', 'Declined'),
    ]

    RESPONSE_STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('viewed', 'Viewed'),
        ('interested', 'Interested'),
        ('clarification_requested', 'Clarification Requested'),
        ('declined', 'Declined'),
        ('shortlisted', 'Shortlisted'),
        ('not_shortlisted', 'Not Shortlisted'),
        ('selected', 'Selected'),
        ('assignment_offered', 'Assignment Offered'),
        ('assignment_accepted', 'Assignment Accepted'),
        ('assignment_declined', 'Assignment Declined'),
        ('conflict_review_required', 'Conflict Review Required'),
        ('access_activated', 'Access Activated'),
    ]

    DECLINE_REASON_CHOICES = [
        ('not_available', 'Not Available'),
        ('outside_expertise', 'Outside Expertise'),
        ('conflict_of_interest', 'Conflict of Interest'),
        ('timeline_not_suitable', 'Timeline Not Suitable'),
        ('commercial_terms', 'Commercial Terms Not Suitable'),
        ('other', 'Other'),
    ]

    # ── System-generated ──
    opportunity_id = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text="Auto-generated: ORR-OPP-000001"
    )

    # ── Linkages ──
    project = models.ForeignKey(
        PMProject, on_delete=models.CASCADE, related_name='opportunities'
    )
    consultant = models.ForeignKey(
        'consultation.Consultant', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='pm_opportunities',
        help_text="For onboarded consultants."
    )
    external_email = models.EmailField(
        blank=True,
        help_text="For external (non-onboarded) consultants."
    )
    is_external_consultant = models.BooleanField(default=False)
    summary_version_sent = models.TextField(
        blank=True,
        help_text="Version of the consultant-facing summary sent."
    )

    # ── Consultant Response ──
    response = models.CharField(
        max_length=25, choices=RESPONSE_CHOICES, default='not_responded'
    )
    interest_statement = models.TextField(blank=True)
    relevant_experience = models.TextField(blank=True)
    availability_confirmation = models.TextField(blank=True)
    clarification_request = models.TextField(blank=True)
    decline_reason = models.CharField(
        max_length=30, choices=DECLINE_REASON_CHOICES, blank=True
    )
    decline_reason_detail = models.TextField(blank=True)

    # ── Selection Stage ──
    shortlisted_status = models.CharField(
        max_length=30, blank=True, default='',
        choices=[
            ('', 'Not Reviewed'),
            ('shortlisted', 'Shortlisted'),
            ('not_shortlisted', 'Not Shortlisted'),
            ('reserve', 'Reserve'),
            ('needs_follow_up', 'Needs Follow-up'),
        ]
    )
    selection_notes = models.TextField(blank=True)
    is_selected = models.BooleanField(default=False)

    # ── Status ──
    response_status = models.CharField(
        max_length=30, choices=RESPONSE_STATUS_CHOICES, default='invited'
    )
    response_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'PM Opportunity'
        verbose_name_plural = 'PM Opportunities'
        unique_together = ['project', 'consultant']

    def __str__(self):
        recipient = self.consultant or self.external_email
        return f"{self.opportunity_id} - {recipient} for {self.project.project_id}"
