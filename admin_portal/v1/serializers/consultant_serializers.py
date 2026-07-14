from rest_framework import serializers
from consultation.models import (
    Consultant,
    ConsultantProfile,
    ConsultantSpecialization,
    ConsultantSkill,
    ConsultantITCompetence,
    ConsultantExperience,
    ConsultantWorkPreference,
    ConsultantCommercial,
    ConsultantCompliance,
)

class ConsultantProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantProfile
        exclude = ('consultant', 'created_at', 'updated_at')

class ConsultantSpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantSpecialization
        exclude = ('consultant', 'created_at', 'updated_at')

class ConsultantSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantSkill
        exclude = ('consultant', 'created_at', 'updated_at')

class ConsultantITCompetenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantITCompetence
        exclude = ('consultant', 'created_at', 'updated_at')

class ConsultantExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantExperience
        exclude = ('consultant', 'created_at', 'updated_at')

class ConsultantWorkPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantWorkPreference
        exclude = ('consultant', 'created_at', 'updated_at')

class ConsultantCommercialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantCommercial
        exclude = ('consultant', 'created_at', 'updated_at')

class ConsultantComplianceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultantCompliance
        exclude = ('consultant', 'created_at', 'updated_at')

class PendingConsultantSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    
    profile = ConsultantProfileSerializer(read_only=True)
    specialization = ConsultantSpecializationSerializer(read_only=True)
    skills = ConsultantSkillSerializer(many=True, read_only=True)
    it_competence = ConsultantITCompetenceSerializer(read_only=True)
    experience = ConsultantExperienceSerializer(read_only=True)
    work_preference = ConsultantWorkPreferenceSerializer(read_only=True)
    commercials = ConsultantCommercialSerializer(read_only=True)
    compliance = ConsultantComplianceSerializer(read_only=True)

    class Meta:
        model = Consultant
        fields = [
            'id', 'consultant_number', 'status', 'internal_rating', 'admin_notes',
            'email', 'first_name', 'last_name', 'created_at',
            'profile', 'specialization', 'skills', 'it_competence',
            'experience', 'work_preference', 'commercials', 'compliance'
        ]
