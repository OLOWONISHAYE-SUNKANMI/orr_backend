from rest_framework import serializers
from django.contrib.auth.models import User
from consultation.models import (
    Consultant, ConsultantProfile, ConsultantSpecialization,
    ConsultantSkill, ConsultantITCompetence, ConsultantExperience,
    ConsultantWorkPreference, ConsultantCommercial, ConsultantCompliance
)

class ConsultantRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

class ConsultantVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    consultant_number = serializers.CharField(max_length=50)

class CustomSkillSerializer(serializers.Serializer):
    name = serializers.CharField()
    status = serializers.CharField()

class ConsultantOnboardingSerializer(serializers.Serializer):
    consultantId = serializers.CharField()
    fullName = serializers.CharField(max_length=200)
    displayName = serializers.CharField(max_length=200, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100)
    jobTitle = serializers.CharField(max_length=200, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
    industry = serializers.CharField(max_length=100)
    secondaryIndustries = serializers.ListField(child=serializers.CharField(), required=False)
    
    skills = serializers.ListField(child=serializers.CharField(), required=False)
    skillProficiencies = serializers.DictField(child=serializers.CharField(), required=False)
    skillYearsExperience = serializers.DictField(child=serializers.CharField(), required=False)
    customSkills = CustomSkillSerializer(many=True, required=False)
    
    itConfidence = serializers.CharField(max_length=50, required=False, allow_blank=True)
    aiFamiliarity = serializers.CharField(max_length=50, required=False, allow_blank=True)
    itCapabilities = serializers.ListField(child=serializers.CharField(), required=False)
    softwareExperience = serializers.ListField(child=serializers.CharField(), required=False)
    dataHandling = serializers.ListField(child=serializers.CharField(), required=False)
    
    professionalSummary = serializers.CharField(required=False, allow_blank=True)
    sectorExperience = serializers.ListField(child=serializers.CharField(), required=False)
    professionalEvidence = serializers.CharField(required=False, allow_blank=True)
    portfolioUrl = serializers.URLField(required=False, allow_blank=True)
    
    isAvailable = serializers.BooleanField(default=True)
    weeklyCapacity = serializers.CharField(max_length=50, required=False, allow_blank=True)
    preferredRoles = serializers.ListField(child=serializers.CharField(), required=False)
    workModes = serializers.ListField(child=serializers.CharField(), required=False)
    geoCoverage = serializers.CharField(max_length=255, required=False, allow_blank=True)
    languages = serializers.ListField(child=serializers.CharField(), required=False)
    
    hourlyRate = serializers.CharField(max_length=50, required=False, allow_blank=True)
    currency = serializers.CharField(max_length=10, required=False, allow_blank=True)
    engagementTypes = serializers.ListField(child=serializers.CharField(), required=False)
    
    rightToWork = serializers.BooleanField(default=False)
    ndaAccepted = serializers.BooleanField(default=False)
    conflictOfInterest = serializers.BooleanField(default=False)
    conflictDetails = serializers.CharField(required=False, allow_blank=True)
    dataProtection = serializers.BooleanField(default=False)

from consultation.models import ConsultantJob, ConsultantTask

class ConsultantTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantTask
        fields = ['id', 'job', 'title', 'description', 'due_date', 'priority', 'status', 'deliverable_submitted_at', 'deliverable_notes', 'deliverable_file_name', 'deliverable_file_url']

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        # Reverse sync: Consultant status -> PM Task status
        if 'status' in validated_data:
            from pm.models import PMTask

            # Map Consultant status -> PM status
            REVERSE_STATUS_MAP = {
                'NOT_STARTED': 'not_started',
                'ASSIGNED': 'not_started',
                'IN_PROGRESS': 'in_progress',
                'UNDER_REVIEW': 'submitted_for_review',
                'BLOCKED': 'blocked',
                'COMPLETED': 'completed',
            }

            pm_status = REVERSE_STATUS_MAP.get(instance.status, 'not_started')

            # Find the matching PMTask by pm_task_id
            pm_task = None
            if instance.pm_task_id:
                pm_task = PMTask.objects.filter(task_id=instance.pm_task_id).first()
            
            if not pm_task:
                consultant_user = instance.job.consultant.user
                pm_task = PMTask.objects.filter(
                    assigned_to=consultant_user,
                    title=instance.title
                ).first()
                if pm_task:
                    instance.pm_task_id = pm_task.task_id
                    instance.save(update_fields=['pm_task_id'])

            if pm_task and pm_task.status != pm_status:
                pm_task.status = pm_status
                pm_task.save(update_fields=['status'])

        return instance

class ConsultantJobSerializer(serializers.ModelSerializer):
    tasks = ConsultantTaskSerializer(many=True, read_only=True)
    
    class Meta:
        model = ConsultantJob
        fields = ['id', 'consultant', 'title', 'industry', 'client_sector', 'rate', 'duration', 'description', 'scope', 'deliverables', 'status', 'accepted_at', 'tasks']

from consultation.models import ConsultantInvoice, ConsultantDocument, ConsultantMessage, ConsultantMeeting, ConsultantNotification, Consultant

class ConsultantInvoiceSerializer(serializers.ModelSerializer):
    consultant = serializers.SlugRelatedField(slug_field='consultant_number', queryset=Consultant.objects.all(), required=False)
    class Meta:
        model = ConsultantInvoice
        fields = '__all__'

class ConsultantDocumentSerializer(serializers.ModelSerializer):
    consultant = serializers.SlugRelatedField(slug_field='consultant_number', queryset=Consultant.objects.all())
    link = serializers.SerializerMethodField()
    class Meta:
        model = ConsultantDocument
        fields = '__all__'

    def get_link(self, obj):
        request = self.context.get('request')
        return obj.get_document_link(request)

class ConsultantMessageSerializer(serializers.ModelSerializer):
    consultant = serializers.SlugRelatedField(slug_field='consultant_number', queryset=Consultant.objects.all())
    class Meta:
        model = ConsultantMessage
        fields = '__all__'

class ConsultantMeetingSerializer(serializers.ModelSerializer):
    consultant_number = serializers.CharField(source='consultant.consultant_number', read_only=True)
    consultant = serializers.SlugRelatedField(slug_field='user_id', queryset=Consultant.objects.all())
    class Meta:
        model = ConsultantMeeting
        fields = '__all__'

class ConsultantNotificationSerializer(serializers.ModelSerializer):
    consultant = serializers.SlugRelatedField(slug_field='consultant_number', queryset=Consultant.objects.all())
    class Meta:
        model = ConsultantNotification
        fields = '__all__'
