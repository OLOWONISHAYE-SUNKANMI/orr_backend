from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from common.models import Audit

# Import CMS models
from .models_cms import *


class AdminRole(models.Model):
    """Admin roles with flexible permissions"""

    ROLE_CHOICES = [
        ("super_admin", "Super Admin"),
        ("admin", "Admin"),
        ("operator", "Operator/Support"),
        ("content_editor", "Content Editor"),
    ]

    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)

    # Permissions
    can_manage_users = models.BooleanField(default=False)
    can_view_all_clients = models.BooleanField(default=False)
    can_edit_clients = models.BooleanField(default=False)
    can_manage_tickets = models.BooleanField(default=False)
    can_manage_meetings = models.BooleanField(default=False)
    can_create_content = models.BooleanField(default=False)
    can_publish_content = models.BooleanField(default=False)
    can_view_analytics = models.BooleanField(default=False)
    can_view_billing = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)
    can_view_ai_logs = models.BooleanField(default=False)
    # Extended RBAC permissions
    can_manage_roles = models.BooleanField(default=False)
    can_view_audit_logs = models.BooleanField(default=False)
    can_view_security_events = models.BooleanField(default=False)
    can_approve_sensitive_actions = models.BooleanField(default=False)
    can_configure_system = models.BooleanField(default=False)

    def __str__(self):
        return self.get_name_display()


class AdminProfile(Audit):
    """Extended profile for admin users"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="admin_profile"
    )
    role = models.ForeignKey(AdminRole, on_delete=models.SET_NULL, null=True)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    is_onboarding_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role}"


class Client(Audit):
    """Client model for admin portal"""

    STAGE_CHOICES = [
        ("discover", "Discover"),
        ("diagnose", "Diagnose"),
        ("design", "Design"),
        ("deploy", "Deploy"),
        ("grow", "Grow"),
    ]

    PILLAR_CHOICES = [
        ("strategic", "Strategic"),
        ("operational", "Operational"),
        ("financial", "Financial"),
        ("cultural", "Cultural"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="client_profile"
    )
    company = models.CharField(max_length=200)
    role = models.CharField(max_length=100, blank=True)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="discover")
    primary_pillar = models.CharField(max_length=20, choices=PILLAR_CHOICES)
    secondary_pillars = models.JSONField(default=list, blank=True)

    # Admin fields
    assigned_admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_clients",
    )
    internal_notes = models.TextField(blank=True)
    is_portal_active = models.BooleanField(default=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.company}"


class Ticket(Audit):
    """Payment and support ticket system"""

    STATUS_CHOICES = [
        ("new", "New"),
        ("processing", "Processing Payment"),
        ("payment_failed", "Payment Failed"),
        ("payment_disputed", "Payment Disputed"),
        ("refund_requested", "Refund Requested"),
        ("refund_processed", "Refund Processed"),
        ("resolved", "Resolved"),
        ("archived", "Archived"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    SOURCE_CHOICES = [
        ("payment_webhook", "Payment Webhook"),
        ("billing_portal", "Billing Portal"),
        ("subscription_change", "Subscription Change"),
        ("manual_request", "Manual Request"),
        ("client_inquiry", "Client Inquiry"),
    ]

    ticket_id = models.CharField(max_length=20, unique=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="tickets")
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )

    subject = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_website = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default="normal"
    )
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="manual_request"
    )

    # Content
    description = models.TextField()
    internal_notes = models.TextField(blank=True)
    is_escalated = models.BooleanField(default=False)

    # Payment relationships (required - all tickets must be payment-related)
    related_invoice = models.ForeignKey(
        "payment.Invoice", on_delete=models.CASCADE, null=True, blank=True
    )
    related_subscription = models.ForeignKey(
        "payment.Subscription", on_delete=models.CASCADE, null=True, blank=True
    )
    
    # Payment specific fields
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def clean(self):
        # Optional validation - tickets can be general support tickets
        pass
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        needs_ticket_id = is_new and not self.ticket_id

        if needs_ticket_id:
            import uuid
            self.ticket_id = f"tmp-{uuid.uuid4().hex[:10]}"

        super().save(*args, **kwargs)
        
        if needs_ticket_id:
            self.ticket_id = f"TKT-{timezone.now().strftime('%Y%m%d')}-{self.pk}"
            super().save(update_fields=["ticket_id"])
            
            # Re-dispatch post_save so creation hooks fire with the final ticket_id
            from django.db.models.signals import post_save
            post_save.send(sender=self.__class__, instance=self, created=True, update_fields=["ticket_id"])

    def __str__(self):
        return f"{self.ticket_id} - {self.subject}"


class TicketMessage(Audit):
    """Messages within tickets"""

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_internal = models.BooleanField(default=False)  # Internal notes vs client-visible

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ticket.ticket_id} - {self.sender.username}"


class Content(Audit):
    """Content management for client portal"""

    TYPE_CHOICES = [
        ("faq", "FAQ"),
        ("article", "Article"),
        ("checklist", "Checklist"),
        ("template", "Template"),
        ("guide", "Guide"),
        ("announcement", "Announcement"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    STAGE_CHOICES = [
        ("discover", "Discover"),
        ("diagnose", "Diagnose"),
        ("design", "Design"),
        ("deploy", "Deploy"),
        ("grow", "Grow"),
    ]

    PILLAR_CHOICES = [
        ("strategic", "Strategic"),
        ("operational", "Operational"),
        ("financial", "Financial"),
        ("cultural", "Cultural"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.TextField(blank=True)
    content = models.TextField()
    content_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # Categorization
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    pillars = models.JSONField(default=list)  # Multiple pillars allowed

    # Files
    attachment = models.FileField(
        upload_to="content_attachments/", blank=True, null=True
    )

    # Metadata
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    published_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Meeting(Audit):
    """Meeting management system"""

    TYPE_CHOICES = [
        ("discovery", "Discovery"),
        ("first_meeting", "First Meeting"),
        ("follow_up", "Follow Up"),
        ("report_review", "Report Review"),
    ]

    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("confirmed", "Confirmed"),
        ("rescheduled", "Rescheduled"),
        ("declined", "Declined"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="meetings"
    )
    meeting_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="requested"
    )


    requested_datetime = models.DateTimeField()
    confirmed_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)
   

    agenda = models.TextField(blank=True)
    meeting_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    
    basic_context = models.TextField(blank=True)
    goals = models.TextField(blank=True)
    pain_points = models.TextField(blank=True)
    # Assignment
    host = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosted_meetings",
    )

    # Integration
    calendar_event_id = models.CharField(max_length=200, blank=True)
    meeting_link = models.URLField(blank=True)

    @property
    def duration_hours(self):
         # If Calendly sent confirmed start & end time:
        if self.confirmed_datetime and hasattr(self, "end_datetime") and self.end_datetime:
            delta = self.end_datetime - self.confirmed_datetime
            minutes = delta.total_seconds() / 60
            return minutes / 60

        return self.duration_minutes / 60


    @property
    def event_date(self):
        dt = self.confirmed_datetime or self.requested_datetime
        return dt.date()

    @property
    def event_time(self):
        dt = self.confirmed_datetime or self.requested_datetime
        return dt.strftime("%H:%M")

    @property
    def label(self):
        today = timezone.now().date()
        diff = (self.event_date - today).days

        if diff < 0:
            return "Completed"
        if diff == 0:
            return "Today"
        if diff == 1:
            return "Tomorrow"
        return f"{diff} days left"

    @property
    def color(self):
        mapping = {
            "requested": "#60A5FA",  # blue
            "confirmed": "#4ADE80",  # green
            "rescheduled": "#FACC15",  # yellow
            "declined": "#F87171",  # red
            "completed": "#9CA3AF",  # gray
            "cancelled": "#EF4444",  # red
        }
        return mapping.get(self.status, "#6B7280")

    @property
    def title(self):
        return self.get_meeting_type_display()

    def __str__(self):
        return f"{self.client.user.get_full_name()} - {self.get_meeting_type_display()}"


class AIConversation(Audit):
    """AI chat logs and oversight"""

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="ai_conversations"
    )
    session_id = models.CharField(max_length=100)

    # Conversation data
    messages = models.JSONField(default=list)  # Store full conversation
    summary = models.TextField(blank=True)

    # Escalation
    escalated_to_ticket = models.BooleanField(default=False)
    escalation_reason = models.TextField(blank=True)

    # Quality control
    needs_improvement = models.BooleanField(default=False)
    improvement_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.client.user.get_full_name()} - {self.session_id}"


class SystemNotification(Audit):
    """System-wide notifications for admin users"""

    TYPE_CHOICES = [
        ("ticket_created", "New Ticket"),
        ("ticket_assigned", "Ticket Assigned"),
        ("meeting_requested", "Meeting Requested"),
        ("meeting_updated", "Meeting Updated"),
        ("system_error", "System Error"),
        ("ai_improvement", "AI Needs Improvement"),
        ("project_submitted", "Project Submitted"),
        ("project_clarify", "Project Clarification"),
        ("project_approved", "Project Approved"),
        ("project_completed", "Project Completed"),
    ]

    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()

    # Targeting
    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="admin_notifications"
    )
    is_read = models.BooleanField(default=False)

    # Related objects
    related_ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, null=True, blank=True
    )
    related_meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, null=True, blank=True
    )
    related_client = models.ForeignKey(
        Client, on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"


class SystemSettings(models.Model):
    """System configuration settings"""

    # Branding
    company_name = models.CharField(max_length=200, default="ORR")
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#007bff")
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    # Meeting settings
    default_meeting_duration = models.PositiveIntegerField(default=60)  # minutes
    meeting_buffer_time = models.PositiveIntegerField(default=15)  # minutes
    business_hours_start = models.TimeField(default="09:00")
    business_hours_end = models.TimeField(default="17:00")

    # Notification settings
    email_notifications_enabled = models.BooleanField(default=True)
    notification_email = models.EmailField(blank=True)

    # Legal
    privacy_policy_url = models.URLField(blank=True)
    terms_of_service_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"System Settings - {self.company_name}"


class AuditLog(models.Model):
    """Audit trail for compliance"""

    ACTION_CHOICES = [
        ("login", "User Login"),
        ("logout", "User Logout"),
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("publish", "Publish Content"),
        ("archive", "Archive Content"),
        ("role_change", "Role Change"),
        ("permission_change", "Permission Change"),
        ("data_export", "Data Export"),
        ("data_delete", "Data Delete"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"


class SecurityAuditLog(models.Model):
    """Structured security audit trail for enterprise compliance"""

    CATEGORY_CHOICES = [
        ('AUTHENTICATION', 'Authentication'),
        ('DUAL_APPROVALS', 'Dual Approvals'),
        ('DELETIONS', 'Deletions'),
        ('SYSTEMS', 'Systems'),
        ('ROLE_CHANGES', 'Role Changes'),
    ]

    event_timestamp = models.DateTimeField(auto_now_add=True)
    event_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    event_name = models.CharField(max_length=100)
    user_id = models.CharField(max_length=50)
    user_email = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-event_timestamp']
        indexes = [
            models.Index(fields=['-event_timestamp'], name='secaudit_timestamp_idx'),
            models.Index(fields=['event_category'], name='secaudit_category_idx'),
            models.Index(fields=['user_id'], name='secaudit_user_idx'),
        ]

    def __str__(self):
        return f"{self.event_name} - {self.user_email} - {self.event_timestamp}"


class ApprovalQueue(models.Model):
    """Dual-approval workflow queue for sensitive administrative actions"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.CharField(max_length=50, primary_key=True)
    action_type = models.CharField(max_length=100)  # e.g. CLIENT_HARD_DELETE, ROLE_ELEVATION
    requested_by = models.CharField(max_length=50)  # Admin User ID or username
    requested_by_name = models.CharField(max_length=150, blank=True)
    requested_by_role = models.CharField(max_length=50, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()  # Serialised original request data
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    decided_by = models.CharField(max_length=50, blank=True)
    decided_by_name = models.CharField(max_length=150, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status'], name='approvalqueue_status_idx'),
            models.Index(fields=['-requested_at'], name='approvalqueue_requested_idx'),
        ]

    def __str__(self):
        return f"{self.id} - {self.action_type} - {self.status}"


class AdminSession(models.Model):
    """Active admin session tracking for security monitoring"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_sessions')
    session_key = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.user.username} - {self.session_key[:12]}..."


class SystemConfig(models.Model):
    """System-level security and operational configuration flags"""

    mfa_enforced = models.BooleanField(default=True)
    ip_bounds_restricted = models.BooleanField(default=False)
    strict_interceptors = models.BooleanField(default=True)
    maintenance_mode = models.BooleanField(default=False)
    verbose_logging = models.BooleanField(default=False)
    session_timeout = models.CharField(max_length=10, default='1h')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'

    def __str__(self):
        return f"SystemConfig (mfa={self.mfa_enforced}, ip_restrict={self.ip_bounds_restricted})"


class VaultFolder(Audit):
    """Logical folder structure for the vault"""
    name = models.CharField(max_length=200)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='folders')
    project = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['client'], name='vaultfolder_client_idx'),
            models.Index(fields=['parent'], name='vaultfolder_parent_idx'),
        ]

    def __str__(self):
        return f"{self.client.company if self.client else 'Global'} - {self.name}"

class ClientDocument(Audit):
    """Documents specific to clients"""

    SCAN_STATUS_CHOICES = [
        ('scanning', 'Scanning'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]

    VISIBILITY_CHOICES = [
        ('client', 'Client-Facing'),
        ('internal', 'Internal Only'),
    ]

    ACCESS_RULE_CHOICES = [
        ('immediate', 'Immediate'),
        ('payment_linked', 'Payment Linked'),
        ('invoice_linked', 'Invoice Linked'),
        ('date_linked', 'Date Linked'),
    ]

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="documents"
    )
    folder = models.ForeignKey(VaultFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    document = models.FileField(upload_to="client_documents/", null=True, blank=True)
    document_type = models.CharField(max_length=50, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)

    # Access control
    is_visible_to_client = models.BooleanField(default=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='client')
    
    document_source = models.CharField(
        max_length=20, 
        choices=[
            ('file', 'File'), 
            ('google_doc', 'Google Doc'), 
            ('google_sheet', 'Google Sheet'),
            ('google_slide', 'Google Slide')
        ],
        default='file'
    )
    google_drive_id = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Security & Health
    scan_status = models.CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default='passed')
    
    # Unlock Rules
    access_rule_type = models.CharField(max_length=20, choices=ACCESS_RULE_CHOICES, default='immediate')
    access_rule_linked_id = models.CharField(max_length=100, blank=True)
    access_rule_description = models.TextField(blank=True)

    # Analytics
    download_count = models.PositiveIntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['client', 'is_visible_to_client'], name='clientdoc_client_visible_idx'),
            models.Index(fields=['client', 'visibility'], name='clientdoc_client_vis_idx'),
            models.Index(fields=['client', '-updated_at'], name='clientdoc_client_updated_idx'),
            models.Index(fields=['folder'], name='clientdoc_folder_idx'),
            models.Index(fields=['-updated_at'], name='clientdoc_updated_idx'),
            models.Index(fields=['visibility'], name='clientdoc_visibility_idx'),
        ]
        ordering = ['-updated_at']

    def save(self, *args, **kwargs):
        if self.document and not self.document_type:
            import os
            ext = os.path.splitext(self.document.name)[1].lower()
            if ext:
                self.document_type = ext.replace('.', '')
                
        # Populate file_size if not set and document exists
        if self.document and self.file_size is None:
            try:
                self.file_size = self.document.size
            except Exception:
                pass
                
        super().save(*args, **kwargs)

    def get_document_link(self, request=None):
        if self.google_drive_id:
            base_urls = {
                'google_sheet': "https://docs.google.com/spreadsheets/d/",
                'google_slide': "https://docs.google.com/presentation/d/",
                'google_doc': "https://docs.google.com/document/d/"
            }
            # Default to doc if source not recognized but id exists
            base_url = base_urls.get(self.document_source, base_urls['google_doc'])
            return f"{base_url}{self.google_drive_id}/edit?rm=minimal"
        
        if self.document:
            try:
                # Optimized URL builder to completely bypass expensive storage backend cryptographic signing/network calls
                name = self.document.name
                if not name:
                    return None
                
                if name.startswith('http://') or name.startswith('https://'):
                    url = name
                else:
                    from django.conf import settings
                    bucket_name = getattr(settings, 'GS_BUCKET_NAME', 'orr-solutions-media')
                    
                    # If we are in production and using GoogleCloudStorage, construct the direct public storage link
                    default_storage = getattr(settings, 'STORAGES', {}).get('default', {}).get('BACKEND', '')
                    if 'GoogleCloudStorage' in default_storage or 'gcloud' in str(getattr(settings, 'DEFAULT_FILE_STORAGE', '')):
                        url = f"https://storage.googleapis.com/{bucket_name}/{name}"
                    else:
                        # Fallback for local storage
                        media_url = getattr(settings, 'MEDIA_URL', '/media/')
                        url = f"{media_url.rstrip('/')}/{name}"

                # Ensure extension is present for local/cloud files
                if self.document_type and not url.lower().endswith(self.document_type.lower().replace('.', '')):
                     if not url.endswith('.'): url += '.'
                     url += self.document_type.replace('.', '')

                if url.startswith('/'):
                    if request:
                        return request.build_absolute_uri(url)
                    
                    from decouple import config
                    api_url = config('BACKEND_URL', default='https://orr-backend-105825824472.asia-southeast2.run.app')
                    return f"{api_url.rstrip('/')}{url}"
                return url
            except Exception:
                # Direct local fallback to avoid slow storage backend calls
                try:
                    name = self.document.name
                    if name:
                        return f"https://storage.googleapis.com/orr-solutions-media/{name}"
                except Exception:
                    pass
                return None
        return None


    def __str__(self):
        return f"{self.client.user.get_full_name()} - {self.title}"

class DocumentVersion(Audit):
    """Versions of a client document"""
    document = models.ForeignKey(ClientDocument, on_delete=models.CASCADE, related_name='versions')
    version_number = models.PositiveIntegerField()
    file = models.FileField(upload_to="client_documents/versions/")
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.document.title} - v{self.version_number}"


class ProRataApproval(Audit):
    """Pro-rata billing approval requests"""

    ADJUSTMENT_TYPE_CHOICES = [
        ('upgrade', 'Plan Upgrade'),
        ('downgrade', 'Plan Downgrade'),
        ('addon', 'Add-on Service'),
        ('removal', 'Service Removal'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='prorata_approvals')
    subscription_id = models.CharField(max_length=255)
    old_plan_name = models.CharField(max_length=100)
    new_plan_name = models.CharField(max_length=100)
    change_date = models.DateField()
    prorated_amount = models.DecimalField(max_digits=10, decimal_places=2)
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_by = models.CharField(max_length=50)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_prorata')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.user.get_full_name()} - {self.adjustment_type} - ${self.prorated_amount}"


class PaymentDispute(Audit):
    """Payment dispute management"""

    DISPUTE_TYPE_CHOICES = [
        ('chargeback', 'Chargeback'),
        ('inquiry', 'Inquiry'),
        ('refund_request', 'Refund Request'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='payment_disputes')
    invoice = models.ForeignKey('payment.Invoice', on_delete=models.CASCADE, related_name='disputes')
    dispute_amount = models.DecimalField(max_digits=10, decimal_places=2)
    dispute_reason = models.TextField()
    dispute_type = models.CharField(max_length=20, choices=DISPUTE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    stripe_dispute_id = models.CharField(max_length=255, blank=True)
    evidence_due_date = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_disputes')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.user.get_full_name()} - {self.dispute_type} - ${self.dispute_amount}"


class DisputeNote(Audit):
    """Notes for payment disputes"""

    dispute = models.ForeignKey(PaymentDispute, on_delete=models.CASCADE, related_name='notes')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.dispute} - Note by {self.created_by.username}"


class WalletTransaction(Audit):
    """Client wallet transaction history"""

    TRANSACTION_TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='wallet_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    reference_id = models.CharField(max_length=100, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.client.user.get_full_name()} - {self.transaction_type} - ${self.amount}"



class Report(Audit):
    """
    Represents deliverables generated after a meeting, matching the UI cards.
    """
    STATUS_CHOICES = [
        ("draft", "Draft"), 
        ("pending", "Pending"),   
        ("completed", "Completed"), 
    ]

    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name="reports"
    )
    title = models.CharField(max_length=255) 
    description = models.TextField(blank=True) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    
   
    file = models.FileField(upload_to="reports/%Y/%m/") 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def file_size_display(self):
        """
        Returns file size in MB to match UI (e.g., '2.4 MB').
        """
        if self.file and hasattr(self.file, 'size'):
            size_in_mb = self.file.size / (1024 * 1024)
            return f"{size_in_mb:.1f} MB"
        return "0 MB"


class StudioDocument(Audit):
    """Document Studio documents (Docs, Sheets, Slides)

    Stores content for the three editor types:
    - doc:   HTML string (Tiptap/ProseMirror output)
    - sheet: JSON array of FortuneSheet sheet objects
    - slide: JSON array of Fabric.js slide objects
    """

    TYPE_CHOICES = [
        ('doc', 'Document'),
        ('sheet', 'Spreadsheet'),
        ('slide', 'Presentation'),
    ]

    title = models.CharField(max_length=500, default='Untitled')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    folder = models.ForeignKey(
        VaultFolder, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='studio_documents'
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='studio_documents'
    )

    # Content payload — stores HTML string (docs) or JSON array (sheets/slides)
    content = models.JSONField(default=dict, blank=True)

    # Soft-delete support
    is_trashed = models.BooleanField(default=False)
    trashed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at'], name='studiodoc_owner_updated_idx'),
            models.Index(fields=['owner', 'type'], name='studiodoc_owner_type_idx'),
            models.Index(fields=['folder'], name='studiodoc_folder_idx'),
            models.Index(fields=['is_trashed'], name='studiodoc_trashed_idx'),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_type_display()}) — {self.owner.username}"