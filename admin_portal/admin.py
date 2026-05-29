from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.apps import apps

# Import admin portal models
from .models import (
    AdminProfile, AdminRole, AIConversation, AuditLog, Client, ClientDocument,
    Content, Meeting, SystemNotification, SystemSettings, Ticket, TicketMessage,
    ProRataApproval, PaymentDispute, DisputeNote, WalletTransaction,
    VaultFolder, DocumentVersion, Report,
)
from .models_cms import (
    HomePage, ServiceCard, Testimonial, FAQ, BlogPost, ContactInfo, SiteSettings,
    ApproachSection, BusinessSystemCard, BusinessSystemSection, ORRRoleSection,
    MessageStrip, ProcessStage, ProcessSection, ORRReportSection, ServicesPage,
    ResourcesBlogsPage, LegacyPolicyPage, ContactPage,
    # Comprehensive CMS Models
    HowWeOperatePageContent, ProcessStep, ServicesPageContent, ServiceStage,
    ServicePillar, ResourcesBlogsPageContent, ContentCard, LegalPolicyPageContent,
    PolicyItem, ContactPageContent,
    # Service Pillar Pages
    StrategicAdvisoryPageContent, OperationalSystemsPageContent, LivingSystemsPageContent,
)


@admin.register(AdminRole)
class AdminRoleAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "can_manage_users", "can_view_all_clients"]
    list_filter = ["can_manage_users", "can_view_all_clients", "can_manage_tickets"]
    search_fields = ["name", "description"]


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "department", "is_active", "created_at"]
    list_filter = ["role", "is_active", "department"]
    search_fields = ["user__username", "user__email", "department"]
    raw_id_fields = ["user"]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "company",
        "stage",
        "primary_pillar",
        "assigned_admin",
        "is_portal_active",
    ]
    list_filter = ["stage", "primary_pillar", "is_portal_active", "assigned_admin"]
    search_fields = ["user__username", "user__email", "company"]
    raw_id_fields = ["user", "assigned_admin"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        "ticket_id",
        "subject",
        "client",
        "status",
        "priority",
        "assigned_to",
        "created_at",
    ]
    list_filter = ["status", "priority", "source", "assigned_to"]
    search_fields = ["ticket_id", "subject", "client__user__email", "client__company"]
    raw_id_fields = ["client", "assigned_to", "related_invoice", "related_subscription"]
    readonly_fields = ["ticket_id", "created_at", "updated_at"]


@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ["ticket", "sender", "is_internal", "created_at"]
    list_filter = ["is_internal", "created_at"]
    search_fields = ["ticket__ticket_id", "sender__username", "message"]
    raw_id_fields = ["ticket", "sender"]


@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "content_type",
        "status",
        "stage",
        "author",
        "published_at",
    ]
    list_filter = ["content_type", "status", "stage", "author"]
    search_fields = ["title", "summary", "content"]
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ["author"]
    readonly_fields = ["view_count", "download_count", "created_at", "updated_at"]


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ["client", "meeting_type", "status", "requested_datetime", "host"]
    list_filter = ["meeting_type", "status", "host"]
    search_fields = ["client__user__email", "client__company", "agenda"]
    raw_id_fields = ["client", "host"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "session_id",
        "escalated_to_ticket",
        "needs_improvement",
        "created_at",
    ]
    list_filter = ["escalated_to_ticket", "needs_improvement", "reviewed_by"]
    search_fields = ["client__user__email", "session_id", "summary"]
    raw_id_fields = ["client", "reviewed_by"]


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "notification_type", "recipient", "is_read", "created_at"]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["title", "message", "recipient__username"]
    raw_id_fields = ["recipient", "related_ticket", "related_meeting", "related_client"]


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ["company_name", "primary_color", "email_notifications_enabled"]

    def has_add_permission(self, request):
        # Only allow one SystemSettings instance
        return not SystemSettings.objects.exists()


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "model_name", "description", "timestamp"]
    list_filter = ["action", "model_name", "timestamp"]
    search_fields = ["user__username", "description", "model_name"]
    readonly_fields = ["timestamp"]
    raw_id_fields = ["user"]


@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "client",
        "folder",
        "document_source",
        "document_type",
        "is_visible_to_client",
        "scan_status",
        "uploaded_by",
        "created_at",
    ]
    list_filter = ["document_source", "document_type", "is_visible_to_client", "scan_status", "uploaded_by", "client"]
    search_fields = ["title", "description", "client__company", "client__user__email", "google_drive_id"]
    raw_id_fields = ["client", "folder", "uploaded_by"]
    readonly_fields = ["download_count", "last_accessed", "created_at", "updated_at"]


@admin.register(ProRataApproval)
class ProRataApprovalAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "adjustment_type",
        "prorated_amount",
        "status",
        "change_date",
        "approved_by",
        "created_at",
    ]
    list_filter = ["status", "adjustment_type", "approved_by", "change_date"]
    search_fields = ["client__user__email", "client__company", "subscription_id", "notes"]
    raw_id_fields = ["client", "approved_by"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "change_date"


@admin.register(PaymentDispute)
class PaymentDisputeAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "dispute_type",
        "dispute_amount",
        "status",
        "evidence_due_date",
        "resolved_by",
        "created_at",
    ]
    list_filter = ["dispute_type", "status", "resolved_by", "created_at"]
    search_fields = ["client__user__email", "client__company", "stripe_dispute_id", "dispute_reason"]
    raw_id_fields = ["client", "invoice", "resolved_by"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"


@admin.register(DisputeNote)
class DisputeNoteAdmin(admin.ModelAdmin):
    list_display = ["dispute", "created_by", "is_internal", "created_at"]
    list_filter = ["is_internal", "created_by", "created_at"]
    search_fields = ["dispute__client__user__email", "note"]
    raw_id_fields = ["dispute", "created_by"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "client",
        "transaction_type",
        "amount",
        "balance_after",
        "processed_by",
        "created_at",
    ]
    list_filter = ["transaction_type", "processed_by", "created_at"]
    search_fields = ["client__user__email", "client__company", "description", "reference_id"]
    raw_id_fields = ["client", "processed_by"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"


@admin.register(VaultFolder)
class VaultFolderAdmin(admin.ModelAdmin):
    list_display = ["name", "client", "project", "parent", "created_at"]
    list_filter = ["client", "project"]
    search_fields = ["name", "project", "client__company"]
    raw_id_fields = ["parent", "client"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ["document", "version_number", "file_name", "file_size", "uploaded_by", "created_at"]
    list_filter = ["version_number", "uploaded_by"]
    search_fields = ["file_name", "document__title", "hash"]
    raw_id_fields = ["document", "uploaded_by"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["title", "meeting", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["title", "description", "meeting__client__company"]
    raw_id_fields = ["meeting"]
    readonly_fields = ["created_at", "updated_at"]


# CMS Admin Registration
@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "last_updated_by", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ServiceCard)
class ServiceCardAdmin(admin.ModelAdmin):
    list_display = ["title", "pillar", "order", "is_active"]
    list_filter = ["pillar", "is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["client_name", "client_company", "rating", "is_featured", "is_active"]
    list_filter = ["rating", "is_featured", "is_active"]
    list_editable = ["is_featured", "is_active"]


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ["question", "category", "order", "is_active"]
    list_filter = ["category", "is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["category", "order"]


# BlogPost admin is handled in main app
# @admin.register(BlogPost)
# class BlogPostAdmin(admin.ModelAdmin):
#     list_display = ["title", "author", "status", "is_featured", "published_at"]
#     list_filter = ["status", "is_featured", "author"]
#     prepopulated_fields = {"slug": ("title",)}
#     readonly_fields = ["view_count"]


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ["company_name", "email", "phone", "is_active"]
    list_filter = ["is_active"]


@admin.register(ApproachSection)
class ApproachSectionAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "updated_at"]
    list_filter = ["is_active"]


@admin.register(BusinessSystemSection)
class BusinessSystemSectionAdmin(admin.ModelAdmin):
    list_display = ["title", "subtitle", "is_active"]
    list_filter = ["is_active"]


@admin.register(BusinessSystemCard)
class BusinessSystemCardAdmin(admin.ModelAdmin):
    list_display = ["title", "order", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]


@admin.register(ORRRoleSection)
class ORRRoleSectionAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "updated_at"]
    list_filter = ["is_active"]


@admin.register(MessageStrip)
class MessageStripAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "updated_at"]
    list_filter = ["is_active"]


@admin.register(ProcessSection)
class ProcessSectionAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "updated_at"]
    list_filter = ["is_active"]


@admin.register(ProcessStage)
class ProcessStageAdmin(admin.ModelAdmin):
    list_display = ["title", "order", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]


@admin.register(ORRReportSection)
class ORRReportSectionAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "updated_at"]
    list_filter = ["is_active"]


@admin.register(ServicesPage)
class ServicesPageAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ResourcesBlogsPage)
class ResourcesBlogsPageAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(LegacyPolicyPage)
class LegacyPolicyPageAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ContactPage)
class ContactPageAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ["site_name", "primary_color", "is_active"]
    list_filter = ["is_active"]


# Comprehensive CMS Admin Registration
@admin.register(HowWeOperatePageContent)
class HowWeOperatePageContentAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ProcessStep)
class ProcessStepAdmin(admin.ModelAdmin):
    list_display = ["step_number", "title", "order", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]


@admin.register(ServicesPageContent)
class ServicesPageContentAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ServiceStage)
class ServiceStageAdmin(admin.ModelAdmin):
    list_display = ["title", "stage_number", "order", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]


@admin.register(ServicePillar)
class ServicePillarAdmin(admin.ModelAdmin):
    list_display = ["title", "order", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]


@admin.register(ResourcesBlogsPageContent)
class ResourcesBlogsPageContentAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ContentCard)
class ContentCardAdmin(admin.ModelAdmin):
    list_display = ["title", "badge", "order", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]


@admin.register(LegalPolicyPageContent)
class LegalPolicyPageContentAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PolicyItem)
class PolicyItemAdmin(admin.ModelAdmin):
    list_display = ["number", "order", "is_active"]
    list_filter = ["is_active"]
    list_editable = ["order", "is_active"]
    ordering = ["order"]


@admin.register(ContactPageContent)
class ContactPageContentAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]


# Service Pillar Pages Admin
@admin.register(StrategicAdvisoryPageContent)
class StrategicAdvisoryPageContentAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Hero Section", {
            "fields": ("hero_title", "hero_subtitle", "hero_description", "hero_image")
        }),
        ("Services Section", {
            "fields": ("services_title", "service_1_title", "service_1_description", 
                      "service_2_title", "service_2_description", "service_3_title", "service_3_description")
        }),
        ("Process Section", {
            "fields": ("process_title", "process_subtitle", "process_description",
                      "process_step_1_title", "process_step_1_subtitle", "process_step_1",
                      "process_step_2_title", "process_step_2", "process_step_3_title", "process_step_3")
        }),
        ("Network Section", {
            "fields": ("network_title", "network_description", "network_cards")
        }),
        ("Digital Solutions Section", {
            "fields": ("digital_title", "digital_subtitle", "digital_description", "digital_image_alt",
                      "digital_who_is_this_for", "digital_features")
        }),
        ("Case Example Section", {
            "fields": ("case_challenge", "case_solution", "case_result", "case_image_alt")
        }),
        ("CTA Section", {
            "fields": ("cta_title", "cta_description", "cta_button_text")
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description")
        }),
        ("Status", {
            "fields": ("is_active",)
        })
    )


@admin.register(OperationalSystemsPageContent)
class OperationalSystemsPageContentAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Hero Section", {
            "fields": ("hero_title", "hero_subtitle", "hero_description", "hero_image")
        }),
        ("Services Section", {
            "fields": ("services_title", "service_1_title", "service_1_description", 
                      "service_2_title", "service_2_description", "service_3_title", "service_3_description")
        }),
        ("Process Section", {
            "fields": ("process_title", "process_description", "process_step_1_title", "process_step_1", "process_step_2_title", "process_step_2", "process_step_3_title", "process_step_3")
        }),
        ("Case Example Section", {
            "fields": ("case_challenge", "case_solution", "case_result", "case_image_alt")
        }),
        ("CTA Section", {
            "fields": ("cta_title", "cta_description", "cta_button_text")
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description")
        }),
        ("Status", {
            "fields": ("is_active",)
        })
    )


@admin.register(LivingSystemsPageContent)
class LivingSystemsPageContentAdmin(admin.ModelAdmin):
    list_display = ["hero_title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        ("Hero Section", {
            "fields": ("hero_title", "hero_subtitle", "hero_description", "hero_image")
        }),
        ("Services Section", {
            "fields": ("services_title", "service_1_title", "service_1_description", 
                      "service_2_title", "service_2_description", "service_3_title", "service_3_description")
        }),
        ("Process Section", {
            "fields": ("process_title", "process_description", "process_step_1", "process_step_2", "process_step_3", "process_step_4")
        }),
        ("Case Example Section", {
            "fields": ("case_challenge", "case_solution", "case_result", "case_image_alt")
        }),
        ("CTA Section", {
            "fields": ("cta_title", "cta_description", "cta_button_text")
        }),
        ("SEO", {
            "fields": ("meta_title", "meta_description")
        }),
        ("Status", {
            "fields": ("is_active",)
        })
    )


# Auto-register models from other apps (skip already registered ones)
def auto_register_remaining_models():
    """Auto-register models from other apps"""
    app_names = ['client', 'main', 'notification', 'organization', 'scheduling', 'common']
    
    for app_name in app_names:
        try:
            app_config = apps.get_app_config(app_name)
            for model in app_config.get_models():
                if model not in admin.site._registry:
                    try:
                        admin.site.register(model)
                    except admin.sites.AlreadyRegistered:
                        pass
        except:
            pass

auto_register_remaining_models()
