from django.contrib import admin
from .models import (
    Consultant, ConsultantProfile, ConsultantSpecialization,
    ConsultantSkill, ConsultantITCompetence, ConsultantExperience,
    ConsultantWorkPreference, ConsultantCommercial, ConsultantCompliance
)

class ConsultantProfileInline(admin.StackedInline):
    model = ConsultantProfile
    can_delete = False

class ConsultantSpecializationInline(admin.StackedInline):
    model = ConsultantSpecialization
    can_delete = False

class ConsultantSkillInline(admin.TabularInline):
    model = ConsultantSkill
    extra = 1

class ConsultantITCompetenceInline(admin.StackedInline):
    model = ConsultantITCompetence
    can_delete = False

class ConsultantExperienceInline(admin.StackedInline):
    model = ConsultantExperience
    can_delete = False

class ConsultantWorkPreferenceInline(admin.StackedInline):
    model = ConsultantWorkPreference
    can_delete = False

class ConsultantCommercialInline(admin.StackedInline):
    model = ConsultantCommercial
    can_delete = False

class ConsultantComplianceInline(admin.StackedInline):
    model = ConsultantCompliance
    can_delete = False

@admin.register(Consultant)
class ConsultantAdmin(admin.ModelAdmin):
    list_display = ('consultant_number', 'user', 'status', 'internal_rating', 'approval_date')
    list_filter = ('status', 'internal_rating')
    search_fields = ('consultant_number', 'user__email')
    readonly_fields = ('consultant_number',)
    inlines = [
        ConsultantProfileInline,
        ConsultantSpecializationInline,
        ConsultantSkillInline,
        ConsultantITCompetenceInline,
        ConsultantExperienceInline,
        ConsultantWorkPreferenceInline,
        ConsultantCommercialInline,
        ConsultantComplianceInline
    ]

    def save_model(self, request, obj, form, change):
        if not obj.consultant_number:
            consultant_count = Consultant.objects.count() + 1
            obj.consultant_number = f"ORR-CONS-{consultant_count:06d}"
        super().save_model(request, obj, form, change)

@admin.register(ConsultantSkill)
class ConsultantSkillAdmin(admin.ModelAdmin):
    list_display = ('skill_name', 'consultant', 'proficiency_level', 'is_custom', 'custom_status')
    list_filter = ('is_custom', 'custom_status', 'proficiency_level')
    search_fields = ('skill_name', 'consultant__consultant_number')

from .models import ConsultantJob, ConsultantTask, ConsultantInvoice, ConsultantDocument, ConsultantMessage, ConsultantMeeting, ConsultantNotification

class ConsultantTaskInline(admin.TabularInline):
    model = ConsultantTask
    extra = 1

@admin.register(ConsultantJob)
class ConsultantJobAdmin(admin.ModelAdmin):
    list_display = ('title', 'consultant', 'status', 'accepted_at')
    list_filter = ('status',)
    search_fields = ('title', 'consultant__consultant_number')
    inlines = [ConsultantTaskInline]

@admin.register(ConsultantInvoice)
class ConsultantInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'consultant', 'amount', 'status', 'submitted_at')
    list_filter = ('status',)

@admin.register(ConsultantDocument)
class ConsultantDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'consultant', 'category', 'status')
    list_filter = ('category', 'status', 'doc_type')

@admin.register(ConsultantMessage)
class ConsultantMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'consultant', 'created_at')

@admin.register(ConsultantMeeting)
class ConsultantMeetingAdmin(admin.ModelAdmin):
    list_display = ('title', 'consultant', 'start_time', 'end_time', 'status')

@admin.register(ConsultantNotification)
class ConsultantNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'consultant', 'notif_type', 'is_read')

