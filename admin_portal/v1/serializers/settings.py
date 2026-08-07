from django.contrib.auth.models import User
from rest_framework import serializers

from admin_portal.models import AdminProfile, AdminRole, AuditLog, SystemSettings, LetterheadTemplate


class LetterheadTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LetterheadTemplate
        fields = '__all__'


class SystemSettingsSerializer(serializers.ModelSerializer):
    """System settings serializer"""

    class Meta:
        model = SystemSettings
        fields = [
            "id",
            "company_name",
            "logo",
            "primary_color",
            "contact_email",
            "contact_phone",
            "default_meeting_duration",
            "meeting_buffer_time",
            "business_hours_start",
            "business_hours_end",
            "email_notifications_enabled",
            "notification_email",
            "privacy_policy_url",
            "terms_of_service_url",
            "created_at",
            "updated_at",
        ]


class AdminRoleSerializer(serializers.ModelSerializer):
    """Admin role serializer"""

    users_count = serializers.SerializerMethodField()

    class Meta:
        model = AdminRole
        fields = [
            "id",
            "name",
            "description",
            "can_manage_users",
            "can_view_all_clients",
            "can_edit_clients",
            "can_manage_tickets",
            "can_manage_meetings",
            "can_create_content",
            "can_publish_content",
            "can_view_analytics",
            "can_view_billing",
            "can_manage_settings",
            "can_view_ai_logs",
            "users_count",
        ]

    def get_users_count(self, obj):
        return obj.adminprofile_set.count()


class AdminProfileSerializer(serializers.ModelSerializer):
    """Admin profile serializer"""

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    last_login = serializers.DateTimeField(source="user.last_login", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)
    role_name = serializers.CharField(source="role.get_name_display", read_only=True)

    class Meta:
        model = AdminProfile
        fields = [
            "id",
            "user_id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_name",
            "department",
            "phone",
            "is_active",
            "last_login_ip",
            "last_login",
            "date_joined",
            "created_at",
            "updated_at",
        ]


class UserManagementSerializer(serializers.Serializer):
    """User creation and management serializer"""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=30, required=False)
    last_name = serializers.CharField(max_length=30, required=False)
    role_name = serializers.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        role_choices = [
            (role.name, role.get_name_display()) for role in AdminRole.objects.all()
        ]
        self.fields["role_name"].choices = role_choices

    department = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=20, required=False)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def validate_role_name(self, value):
        if not AdminRole.objects.filter(name=value).exists():
            raise serializers.ValidationError("Invalid role name.")
        return value


class AdminUserListSerializer(serializers.ModelSerializer):
    """Admin user list serializer for assignments"""

    full_name = serializers.SerializerMethodField()
    role_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role_name",
            "is_active",
        ]

    def get_full_name(self, obj):
        full_name = obj.get_full_name().strip()
        if full_name:
            return full_name
        return obj.username or "Unknown User"

    def get_role_name(self, obj):
        if hasattr(obj, 'admin_profile') and obj.admin_profile.role:
            return obj.admin_profile.role.get_name_display()
        return "No Role"


class AuditLogSerializer(serializers.ModelSerializer):
    """Audit log serializer"""

    username = serializers.CharField(source="user.username", allow_null=True)
    user_full_name = serializers.CharField(source="user.get_full_name", allow_null=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "username",
            "user_full_name",
            "action",
            "model_name",
            "object_id",
            "description",
            "ip_address",
            "user_agent",
            "timestamp",
        ]
