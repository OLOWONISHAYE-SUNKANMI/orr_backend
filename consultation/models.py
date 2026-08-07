from django.db import models
from django.contrib.auth.models import User
from common.models import Audit

class Consultant(Audit):
    STATUS_CHOICES = [
        ('ACCOUNT_CREATED', 'Account Created'),
        ('EMAIL_VERIFIED', 'Email Verified'),
        ('DRAFT', 'Draft'),
        ('PENDING_REVIEW', 'Pending Review'),
        ('NEEDS_CLARIFICATION', 'Needs Clarification'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SUSPENDED', 'Suspended'),
        ('ARCHIVED', 'Archived'),
    ]

    RATING_CHOICES = [
        ('NOT_ASSESSED', 'Not Assessed'),
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('PRIORITY', 'Priority'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='consultant')
    consultant_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='ACCOUNT_CREATED')
    
    # Admin fields
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_consultants')
    approval_date = models.DateTimeField(null=True, blank=True)
    internal_rating = models.CharField(max_length=20, choices=RATING_CHOICES, default='NOT_ASSESSED')
    admin_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.consultant_number} - {self.user.email}"

class ConsultantProfile(Audit):
    consultant = models.OneToOneField(Consultant, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=200, blank=True)
    display_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=100, blank=True)
    professional_title = models.CharField(max_length=200, blank=True)
    availability = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.consultant.consultant_number})"

class ConsultantSpecialization(Audit):
    PILLAR_CHOICES = [
        ('Strategy Advisory & Compliance', 'Strategy Advisory & Compliance'),
        ('Operational Systems & Infrastructure', 'Operational Systems & Infrastructure'),
        ('Living Systems Regeneration', 'Living Systems Regeneration'),
    ]

    consultant = models.OneToOneField(Consultant, on_delete=models.CASCADE, related_name='specialization')
    primary_specialization = models.CharField(max_length=100, choices=PILLAR_CHOICES, blank=True)
    secondary_specializations = models.JSONField(default=list, blank=True)
    
    # Newly added fields to match frontend ProfileTab
    expertise_tags = models.JSONField(default=list, blank=True)
    areas_of_specialization = models.JSONField(default=list, blank=True)
    consulting_methodologies = models.JSONField(default=list, blank=True)
    industry_expertise = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.consultant.consultant_number} - {self.primary_specialization}"

class ConsultantSkill(Audit):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('MERGED', 'Merged'),
    ]

    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=200)
    proficiency_level = models.CharField(max_length=50, blank=True)
    years_of_experience = models.CharField(max_length=50, blank=True)
    is_custom = models.BooleanField(default=False)
    custom_status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"{self.skill_name} ({self.consultant.consultant_number})"

class ConsultantITCompetence(Audit):
    consultant = models.OneToOneField(Consultant, on_delete=models.CASCADE, related_name='it_competence')
    it_confidence = models.CharField(max_length=50, blank=True)
    ai_familiarity = models.CharField(max_length=50, blank=True)
    digital_tools = models.JSONField(default=list, blank=True)
    software_experience = models.JSONField(default=list, blank=True)
    data_handling = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"IT Competence for {self.consultant.consultant_number}"

class ConsultantExperience(Audit):
    consultant = models.OneToOneField(Consultant, on_delete=models.CASCADE, related_name='experience')
    professional_summary = models.TextField(blank=True)
    sector_experience = models.JSONField(default=list, blank=True)
    professional_evidence = models.TextField(blank=True)
    portfolio_url = models.URLField(blank=True)
    cv_file = models.FileField(upload_to='consultant_cvs/', null=True, blank=True)
    
    # Newly added fields to match frontend ProfileTab
    years_of_experience = models.IntegerField(default=0, blank=True, null=True)
    current_company = models.CharField(max_length=200, blank=True)
    previous_companies = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    licenses = models.JSONField(default=list, blank=True)
    educational_qualifications = models.JSONField(default=list, blank=True)
    professional_memberships = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Experience for {self.consultant.consultant_number}"

class ConsultantWorkPreference(Audit):
    consultant = models.OneToOneField(Consultant, on_delete=models.CASCADE, related_name='work_preference')
    is_available = models.BooleanField(default=True)
    weekly_capacity = models.CharField(max_length=50, blank=True)
    preferred_roles = models.JSONField(default=list, blank=True)
    work_modes = models.JSONField(default=list, blank=True)
    geo_coverage = models.CharField(max_length=255, blank=True)
    languages = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Work Preferences for {self.consultant.consultant_number}"

class ConsultantCommercial(Audit):
    consultant = models.OneToOneField(Consultant, on_delete=models.CASCADE, related_name='commercials')
    hourly_rate = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=10, blank=True)
    engagement_types = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Commercials for {self.consultant.consultant_number}"

class ConsultantCompliance(Audit):
    consultant = models.OneToOneField(Consultant, on_delete=models.CASCADE, related_name='compliance')
    right_to_work = models.BooleanField(default=False)
    confidentiality = models.BooleanField(default=False)
    conflict_of_interest = models.BooleanField(default=False)
    conflict_details = models.TextField(blank=True)
    data_protection = models.BooleanField(default=False)

    def __str__(self):
        return f"Compliance for {self.consultant.consultant_number}"

# --- Phase 1: Jobs & Tasks ---

class ConsultantJob(Audit):
    STATUS_CHOICES = [
        ('REQUESTED_BY_PM', 'Requested by PM'),
        ('ASSIGNED_BY_ADMIN', 'Assigned by Admin'),
        ('ACCEPTED_BY_CONSULTANT', 'Accepted by Consultant'),
        ('REJECTED_BY_CONSULTANT', 'Rejected by Consultant'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE, related_name='jobs', null=True, blank=True)
    project = models.ForeignKey('client.Project', on_delete=models.CASCADE, related_name='consultant_jobs', null=True, blank=True)
    title = models.CharField(max_length=200)
    industry = models.CharField(max_length=100)
    client_sector = models.CharField(max_length=100)
    rate = models.CharField(max_length=50)
    duration = models.CharField(max_length=50)
    description = models.TextField()
    scope = models.JSONField(default=list)
    deliverables = models.JSONField(default=list)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='REQUESTED_BY_PM')
    consultant_feedback = models.TextField(blank=True, null=True, help_text="Consultant's initial feedback/cost upon accepting the project")
    accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.consultant.consultant_number}"

class ConsultantTask(Audit):
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('UNDER_REVIEW', 'Under Review'),
        ('BLOCKED', 'Blocked'),
        ('COMPLETED', 'Completed'),
    ]
    job = models.ForeignKey(ConsultantJob, on_delete=models.CASCADE, related_name='tasks')
    pm_task_id = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ASSIGNED')
    
    # Deliverable submission
    deliverable_submitted_at = models.DateTimeField(null=True, blank=True)
    deliverable_notes = models.TextField(blank=True)
    deliverable_file_name = models.CharField(max_length=255, blank=True)
    deliverable_file_url = models.URLField(blank=True)

    def __str__(self):
        return f"{self.title} for {self.job.title}"

# --- Phase 2: Invoices ---

class ConsultantInvoice(Audit):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('APPROVED', 'Approved'),
        ('PROCESSING', 'Processing'),
        ('PAID', 'Paid'),
    ]
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=100)
    billing_period = models.CharField(max_length=100)
    hours = models.DecimalField(max_digits=10, decimal_places=2)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    task_title = models.CharField(max_length=200)
    submitted_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SUBMITTED')
    notes = models.TextField(blank=True)
    reviewer_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.consultant.consultant_number}"

# --- Phase 3: Collaboration (Documents, Messages, Meetings) ---

class ConsultantDocument(Audit):
    CATEGORY_CHOICES = [
        ('LEGAL', 'Legal'),
        ('FINANCIAL', 'Financial'),
        ('OPERATIONAL', 'Operational'),
        ('TECHNICAL', 'Technical'),
    ]
    STATUS_CHOICES = [
        ('LOCKED', 'Locked'),
        ('UNLOCKED', 'Unlocked'),
    ]
    DOC_TYPES = [
        ('doc', 'Document'),
        ('sheet', 'Spreadsheet'),
        ('slide', 'Presentation'),
        ('folder', 'Folder'),
        ('file', 'File'),
    ]
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='LEGAL')
    content = models.TextField(blank=True)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES, default='doc')
    job = models.ForeignKey(ConsultantJob, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='LOCKED')
    parent_id = models.CharField(max_length=100, null=True, blank=True)
    file = models.FileField(upload_to='consultant_documents/', null=True, blank=True)
    file_size = models.IntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True)

    def get_document_link(self, request=None):
        if self.file:
            try:
                name = self.file.name
                if not name: return None
                if name.startswith('http://') or name.startswith('https://'):
                    url = name
                else:
                    from django.conf import settings
                    bucket_name = getattr(settings, 'GS_BUCKET_NAME', 'orr-solutions-media')
                    default_storage = getattr(settings, 'STORAGES', {}).get('default', {}).get('BACKEND', '')
                    if 'GoogleCloudStorage' in default_storage or 'gcloud' in str(getattr(settings, 'DEFAULT_FILE_STORAGE', '')):
                        url = f"https://storage.googleapis.com/{bucket_name}/{name}"
                    else:
                        media_url = getattr(settings, 'MEDIA_URL', '/media/')
                        url = f"{media_url.rstrip('/')}/{name}"
                
                # Ensure the url has an extension, docs viewer relies on it.
                if '.' not in url.split('/')[-1]:
                    if 'spreadsheet' in self.mime_type or 'excel' in self.mime_type or self.mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                        url += '.xlsx'
                    elif 'word' in self.mime_type or self.mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                        url += '.docx'
                    elif 'powerpoint' in self.mime_type or 'presentation' in self.mime_type:
                        url += '.pptx'

                if url.startswith('/'):
                    if request: return request.build_absolute_uri(url)
                    from decouple import config
                    api_url = config('BACKEND_URL', default='http://localhost:8000')
                    return f"{api_url.rstrip('/')}{url}"
                return url
            except Exception:
                pass
        return None

class ConsultantMessage(Audit):
    SENDER_CHOICES = [
        ('CONSULTANT', 'Consultant'),
        ('PROJECT_MANAGER', 'Project Manager'),
    ]
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE, related_name='messages')
    pm = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True, related_name='consultant_messages')
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    text = models.TextField()
    attachment_name = models.CharField(max_length=255, blank=True)
    attachment_url = models.URLField(blank=True)
    attachment_type = models.CharField(max_length=50, blank=True)

class ConsultantMeeting(Audit):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE, related_name='meetings')
    pm = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='consultant_meetings')
    title = models.CharField(max_length=255)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    join_link = models.URLField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='UPCOMING')

# --- Phase 4: Notifications ---

class ConsultantNotification(Audit):
    TYPE_CHOICES = [
        ('JOB', 'Job'),
        ('PAYMENT', 'Payment'),
        ('CHAT', 'Chat'),
        ('DOCUMENT', 'Document'),
        ('SYSTEM', 'System'),
    ]
    consultant = models.ForeignKey(Consultant, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='SYSTEM')

    def __str__(self):
        return f"{self.title} for {self.consultant.consultant_number}"
