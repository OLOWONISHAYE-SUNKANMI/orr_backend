from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from admin_portal.models import ClientDocument, Client
from common.models import Audit
from common.state_machine import StateMachineMixin
from django.utils import timezone


class Profile(Audit):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nickname = models.CharField(max_length=100, blank=True)
    full_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(
        max_length=20,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("prefer_not_say", "Prefer not to say"),
        ],
        blank=True,
    )
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    language = models.CharField(max_length=50, default="en")
    timezone = models.CharField(max_length=100, default="UTC")
    profile_pic = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    bio_text = models.TextField(blank=True)
    bio_attachment = models.FileField(
        upload_to="profile_bio_attachments/", blank=True, null=True
    )
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"




class Activity(Audit):
    ACTIVITY_TYPES = [
        ("DOCUMENT", "Document Uploaded"),
        ("TICKET", "Support Ticket Activity"),
        ("MEETING", "Meeting Activity"),
        ("CHECKLIST", "Checklist Update"),
        ("REPORT", "Report Update"),
        ("USER", "General User Activity"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities",
        null=True,
        blank=True,
    )
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"]), models.Index(fields=["user"])]

    def __str__(self):
        return f"{self.title} - {self.user}"


class OnboardingQuestionnaire(Audit):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="onboarding"
    )
    is_completed = models.BooleanField(default=False)
    jurisdiction = models.CharField(
        max_length=50,
        choices=[
            ("malta", "Malta"),
            ("eu_non_malta", "EU (non-Malta)"),
            ("non_eu", "Non-EU"),
            ("other", "Other (specify)"),
        ],
    )
    jurisdiction_other = models.CharField(max_length=100, blank=True)

    language = models.CharField(
        max_length=20,
        choices=[
            ("en", "English"),
            ("mt", "Maltese"),
            ("it", "Italian"),
            ("other", "Other (specify)"),
        ],
    )
    language_other = models.CharField(max_length=100, blank=True)

    keyboard_layout = models.CharField(
        max_length=20,
        choices=[
            ("en_us", "EN-US"),
            ("en_uk", "EN-UK"),
            ("mt", "MT"),
            ("it", "IT"),
            ("other", "Other"),
        ],
    )
    keyboard_other = models.CharField(max_length=100, blank=True)

    date_format = models.CharField(
        max_length=20,
        choices=[("dd_mm_yyyy", "DD/MM/YYYY"), ("mm_dd_yyyy", "MM/DD/YYYY")],
    )
    time_format_24h = models.BooleanField(default=True)
    accepted_service_agreement = models.BooleanField(default=False)
    portal_interests = models.JSONField(default=list)
    portal_interests_other = models.TextField(blank=True)

    user_type = models.CharField(
        max_length=50,
        choices=[
            ("founder", "Founder / Entrepreneur"),
            ("small_business", "Small business owner"),
            ("corporate", "Corporate representative"),
            ("public_ngo", "Public sector / NGO"),
            ("academic", "Researcher / Academic"),
            ("professional", "Individual professional"),
            ("other", "Other (specify)"),
        ],
    )
    user_type_other = models.CharField(max_length=100, blank=True)

    project_stage = models.CharField(
        max_length=50,
        choices=[
            ("exploration", "Early Exploration"),
            ("pre_startup", "Pre-Startup / Planning"),
            ("operational", "Operational but seeking optimisation"),
            ("scaling", "Scaling / Growth"),
            ("unsure", "Unsure"),
        ],
    )

    orr_pillars = models.JSONField(default=list)

    has_active_project = models.CharField(
        max_length=10, choices=[("yes", "Yes"), ("no", "No"), ("maybe", "Maybe")]
    )
    
    ai_preference = models.CharField(
        max_length=50,
        choices=[
            ("concise", "Concise"),
            ("scientific", "Scientific/Technical"),
            ("friendly", "Friendly/Conversational"),
            ("professional", "Professional/Formal"),
        ],
        default="concise",
    )
    project_description = models.TextField(
        blank=True, validators=[MinLengthValidator(10)]
    )
    challenges = models.JSONField(default=list)
    challenges_other = models.TextField(blank=True)

    meeting_format = models.CharField(
        max_length=20,
        choices=[
            ("video", "Online (video)"),
            ("phone", "Phone call"),
            ("in_person", "In-person (subject to availability)"),
        ],
    )

    communication_tone = models.CharField(
        max_length=20,
        choices=[
            ("concise", "Concise and direct"),
            ("detailed", "Detailed and explanatory"),
            ("technical", "Technical"),
            ("non_technical", "Non-technical"),
            ("no_preference", "No preference"),
        ],
    )

    notification_preference = models.CharField(
        max_length=20,
        choices=[
            ("email", "Email"),
            ("portal_only", "In-portal notifications only"),
            ("both", "Both"),
        ],
    )
    ai_specialist_domains = models.JSONField(default=list)
    ai_specialist_other = models.TextField(blank=True)
    additional_context = models.TextField(blank=True)

    class Meta:
        verbose_name = "Onboarding Questionnaire"
        verbose_name_plural = "Onboarding Questionnaires"

    def __str__(self):
        return f"Onboarding - {self.user.get_full_name() or self.user.email}"


class FavoriteDocument(Audit):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_documents"
    )
    document = models.ForeignKey(
        ClientDocument,
        on_delete=models.CASCADE,
        related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "document") 

    def __str__(self):
        return f"{self.user} -> {self.document.title}"




class Project(Audit):
    """
    Groups meetings and tracks 'Active Projects' shown on the dashboard.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    SOURCE_CHOICES = (
        ("client_portal", "Client Portal"),
        ("internally_sourced", "Internally Sourced"),
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255) 
    source = models.CharField(
        max_length=50, choices=SOURCE_CHOICES, default="client_portal"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.name} - {self.client}"

class Wallet(Audit):
    """
    Stores the 'My Wallet' balance shown on the bottom right.
    One wallet per Host (User).
    """
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
   
    def __str__(self):
        return f"{self.owner}'s Wallet ({self.balance} {self.currency})"

class Transaction(Audit):
    """
    Tracks 'Revenue' and distinct payments.
    Linked to a Project or Meeting to know where money came from.
    """
    TRANSACTION_TYPES = [
        ('top_up', 'Wallet Top-up'),
        ('payment', 'Payment Received'),
        ('withdrawal', 'Withdrawal'),
        ('refund', 'Refund'),
        ('deduction', 'Deduction'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    date = models.DateTimeField(default=timezone.now)
    description = models.CharField(max_length=255, blank=True)
    reference_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-update wallet balance on save
        if not self.pk: # Only on create
            if self.transaction_type in ['top_up', 'payment', 'refund']:
                self.wallet.balance += self.amount
            elif self.transaction_type in ['withdrawal', 'deduction']:
                if self.wallet.balance < self.amount:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError("Insufficient wallet balance for this transaction.")
                self.wallet.balance -= self.amount
            self.wallet.save()
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════
# CLIENT REQUEST / PROBLEM BRIEF
# ═══════════════════════════════════════════════════════════

class ClientRequest(StateMachineMixin, Audit):
    """
    Client Problem / Request Brief Form.
    Main client-side intake form used to capture the specific issue, question,
    objective, opportunity, or business problem the client wants ORR to assess.

    One client may submit multiple requests over time. A request may later become
    a meeting, a project, several projects, a rejected request, or part of a
    retainer workstream.
    """

    # ── Status Choices (from PDF: drives client visibility and internal workflow) ──
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pending_orr_review', 'Pending ORR Review'),
        ('clarification_requested', 'Clarification Requested'),
        ('approved_for_meeting', 'Approved for Meeting'),
        ('approved_for_pm_assignment', 'Approved for PM Assignment'),
        ('converted_to_project', 'Converted to Project'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ]

    # ── Request Type Choices ──
    REQUEST_TYPE_CHOICES = [
        ('advice', 'I need advice'),
        ('written_review', 'I need a written review or report'),
        ('operational_problem', 'I need help solving an operational problem'),
        ('compliance_regulatory', 'I need compliance or regulatory support'),
        ('it_systems', 'I need IT / systems support'),
        ('land_agriculture_environment', 'I need land, agriculture, or environmental support'),
        ('ongoing_support', 'I need ongoing support'),
        ('not_sure', 'I am not sure'),
    ]

    # ── Service Area Choices ──
    SERVICE_AREA_CHOICES = [
        ('strategy_advisory_compliance', 'Strategy Advisory & Compliance'),
        ('operational_systems_infrastructure', 'Operational Systems & Infrastructure'),
        ('living_systems_regeneration', 'Living Systems Regeneration'),
        ('not_sure', 'Not sure'),
    ]

    # ── Urgency Choices ──
    URGENCY_CHOICES = [
        ('normal', 'Normal'),
        ('priority', 'Priority'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ]

    # ── Budget Expectation Choices ──
    BUDGET_CHOICES = [
        ('not_sure', 'Not sure'),
        ('small_initial_review', 'Small initial review only'),
        ('fixed_project_budget', 'Fixed project budget'),
        ('retainer_support', 'Retainer support'),
        ('prefer_to_discuss', 'I prefer to discuss'),
    ]

    # ── Sensitivity Level Choices ──
    SENSITIVITY_CHOICES = [
        ('standard', 'Standard'),
        ('confidential', 'Confidential'),
        ('highly_confidential', 'Highly Confidential'),
        ('restricted', 'Restricted / commercially sensitive'),
    ]

    # ── Preferred Next Step Choices ──
    NEXT_STEP_CHOICES = [
        ('schedule_consultation', 'Schedule a first consultation'),
        ('receive_feedback', 'Receive initial feedback from ORR'),
        ('upload_documents', 'Upload documents first'),
        ('discuss_pricing', 'Discuss pricing'),
        ('not_sure', 'I am not sure'),
    ]

    # ── System Linkage Fields ──
    SOURCE_CHOICES = (
        ("client_portal", "Client Portal"),
        ("internally_sourced", "Internally Sourced"),
    )

    request_id = models.CharField(
        max_length=20, unique=True, blank=True,
        help_text="Auto-generated: ORR-REQ-000001"
    )
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='requests',
        help_text="Linked Client ID. Client should not manually enter this."
    )
    source = models.CharField(
        max_length=50, choices=SOURCE_CHOICES, default="client_portal"
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='submitted_requests',
        help_text="User account ID of the person submitting the request."
    )
    submission_date = models.DateTimeField(
        null=True, blank=True,
        help_text="Auto-recorded on submission."
    )

    # ── Request Basics ──
    request_title = models.CharField(
        max_length=300,
        help_text="Short title for the request."
    )
    main_request_type = models.CharField(
        max_length=50, choices=REQUEST_TYPE_CHOICES,
        help_text="What do you need ORR to help with?"
    )
    orr_service_area = models.CharField(
        max_length=50, choices=SERVICE_AREA_CHOICES, blank=True,
        help_text="Which ORR service area best fits? If 'Not sure', Admin/PM can classify later."
    )

    # ── Problem Detail ──
    short_description = models.TextField(
        help_text="Core intake field. Feeds Admin review and AI project summary generation."
    )
    desired_outcome = models.TextField(
        help_text="What outcome the client is hoping to achieve."
    )
    background_context = models.TextField(
        blank=True,
        help_text="Background information to help ORR understand the situation."
    )
    main_question = models.TextField(
        blank=True,
        help_text="Useful for advisory and strategy requests."
    )
    current_challenge = models.TextField(
        blank=True,
        help_text="Helps identify urgency, risk, and next action."
    )
    actions_taken = models.TextField(
        blank=True,
        help_text="Prevents duplication and gives PM context."
    )
    decision_needed = models.TextField(
        blank=True,
        help_text="Useful for converting request into project scope."
    )

    # ── Scope & Expectations ──
    expected_support = models.JSONField(
        default=list, blank=True,
        help_text="Multi-select: Initial consultation, Written advice, Document review, etc."
    )
    expected_deliverable = models.JSONField(
        default=list, blank=True,
        help_text="Multi-select: Meeting summary, Advisory note, Written report, etc."
    )
    urgency = models.CharField(
        max_length=10, choices=URGENCY_CHOICES, default='normal',
        help_text="How urgent is this request?"
    )
    target_date = models.DateField(
        null=True, blank=True,
        help_text="Is there a deadline or target date?"
    )
    budget_expectation = models.CharField(
        max_length=30, choices=BUDGET_CHOICES, blank=True,
        help_text="Do you already have a budget expectation for this request?"
    )

    # ── Sector / Domain ──
    sector = models.JSONField(
        default=list, blank=True,
        help_text="Multi-select + Other: Agriculture, IT / Software, Regulatory Affairs, etc."
    )
    jurisdiction = models.TextField(
        blank=True,
        help_text="Which country or jurisdiction does this request concern?"
    )
    location = models.TextField(
        blank=True,
        help_text="Location of the business, project, land, asset, or operation."
    )

    # ── Documents ──
    has_documents = models.BooleanField(
        default=False,
        help_text="Do you have documents that may help ORR assess this request?"
    )

    # ── Confidentiality ──
    sensitivity_level = models.CharField(
        max_length=30, choices=SENSITIVITY_CHOICES, default='standard',
        help_text="How sensitive is this request?"
    )
    confidentiality_agreed = models.BooleanField(
        default=False,
        help_text="Sensitive Information Notice acknowledgement."
    )

    # ── Communication Preferences ──
    preferred_next_step = models.CharField(
        max_length=30, choices=NEXT_STEP_CHOICES, blank=True,
        help_text="What would you prefer as the next step?"
    )
    preferred_contact_method = models.JSONField(
        default=list, blank=True,
        help_text="Multi-select: Portal message, Email, Phone, Video meeting, WhatsApp."
    )
    preferred_meeting_language = models.JSONField(
        default=list, blank=True,
        help_text="Multi-select: English, Maltese, Italian, French, Spanish, Other."
    )

    # ── Compliance / Declaration ──
    confirm_accuracy = models.BooleanField(
        default=False,
        help_text="I confirm that the information provided is accurate."
    )
    confirm_authority = models.BooleanField(
        default=False,
        help_text="I confirm that I am authorised to submit this request."
    )
    confirm_no_emergency = models.BooleanField(
        default=False,
        help_text="I understand this does not create an emergency support obligation."
    )
    ai_processing_notice = models.BooleanField(
        default=False,
        help_text="I understand ORR may use secure internal AI-assisted tools."
    )

    # ── Status ──
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='draft',
        help_text="Status drives client visibility and internal workflow."
    )

    # ── Internal Review (Not visible to client) ──
    admin_classification = models.TextField(
        blank=True,
        help_text="Admin can reclassify service area, urgency, sensitivity, and next step."
    )
    admin_review_notes = models.TextField(blank=True)
    assigned_pm = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_requests',
        help_text="If request is approved, Admin can assign client/request to PM."
    )
    converted_project = models.ForeignKey(
        'pm.PMProject', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='source_requests',
        help_text="One request may become one or more projects."
    )

    # ── Audit Trail ──
    last_updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='updated_requests',
        help_text="Store user ID of last editor."
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Client Request'
        verbose_name_plural = 'Client Requests'
        indexes = [
            models.Index(fields=['client', '-created_at'], name='clientreq_client_created_idx'),
            models.Index(fields=['status'], name='clientreq_status_idx'),
            models.Index(fields=['assigned_pm'], name='clientreq_pm_idx'),
        ]

    def __str__(self):
        return f"{self.request_id} - {self.request_title}"


class ClientRequestDocument(Audit):
    """
    Documents uploaded with a Client Request.
    Files should be linked to Request ID and Client ID.
    Upload can also happen later through the Client Vault.
    """
    request = models.ForeignKey(
        ClientRequest, on_delete=models.CASCADE, related_name='documents'
    )
    file = models.FileField(
        upload_to='request_documents/',
        help_text="Upload documents relevant to this request."
    )
    file_name = models.CharField(max_length=300, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(
        blank=True,
        help_text="Briefly describe what each uploaded document is."
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    # Optional link to vault document
    vault_document = models.ForeignKey(
        ClientDocument, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='request_links',
        help_text="Link to existing Client Vault document."
    )

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.file and not self.file_name:
            self.file_name = self.file.name
        if self.file and self.file_size is None:
            try:
                self.file_size = self.file.size
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file_name} for {self.request.request_id}"


class ClientRequestVersion(Audit):
    """
    Audit trail: Preserve changes to description, scope, documents,
    sensitivity, status, and Admin/PM classification.
    """
    request = models.ForeignKey(
        ClientRequest, on_delete=models.CASCADE, related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    change_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-version_number']

    def __str__(self):
        return f"{self.request.request_id} v{self.version_number} - {self.field_changed}"


# Signals for Wallet Creation
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(owner=instance)
