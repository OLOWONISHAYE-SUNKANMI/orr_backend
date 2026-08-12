from rest_framework import serializers
from admin_portal.models import TechnicalFeedback
from django.contrib.auth.models import User

class UserFeedbackSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name']
        
    def get_name(self, obj):
        return obj.get_full_name() or obj.username

class TechnicalFeedbackSerializer(serializers.ModelSerializer):
    user_details = UserFeedbackSerializer(source='user', read_only=True)
    
    class Meta:
        model = TechnicalFeedback
        fields = [
            'id', 'user', 'user_details', 'subject', 'description',
            'status', 'attachment', 'browser_info', 'os_info',
            'url_path', 'created_at', 'updated_at'
        ]
        # `status` is writable so the admin-only detail PATCH can update it;
        # on create the model default ('open') applies because the reporter's
        # POST payload does not include it.
        read_only_fields = ['id', 'created_at', 'updated_at']
