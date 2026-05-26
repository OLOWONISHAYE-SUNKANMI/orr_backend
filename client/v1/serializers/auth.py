from django.contrib.auth import get_user_model
from rest_framework import serializers

from admin_portal.models import AdminRole


from services.notifications.email_verification import (
    send_email_verification_notification,
)


User = get_user_model()


class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    user_type = serializers.ChoiceField(
        choices=[("client", "Client"), ("admin", "Admin")], default="client"
    )
    admin_role = serializers.ChoiceField(choices=[], required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate admin_role choices dynamically
        role_choices = [
            (role.name, role.get_name_display()) for role in AdminRole.objects.all()
        ]
        self.fields["admin_role"].choices = role_choices

    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "user_type",
            "admin_role",
        )

    def validate(self, attrs):
        if attrs.get("user_type") == "admin" and not attrs.get("admin_role"):
            raise serializers.ValidationError("Admin role is required for admin users")
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError(
                "Email and password are required."
            )
        

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        
        if not user:
            raise serializers.ValidationError("Invalid login credentials.")

        # Check if this user registered via Google (has unusable password)
        if not user.has_usable_password():
            raise serializers.ValidationError(
                "This account was registered using Google Sign-In. Please use the 'Continue with Google' button to log in."
            )

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid login credentials.")
        if not user.is_active:
            send_email_verification_notification(user)
            raise serializers.ValidationError(
                "Account not verified. A verification email has been sent."
            )
        # Get user role info
        role_info = self._get_user_role_info(user)
        attrs["user"] = user
        attrs["role_info"] = role_info
        return attrs

    def _get_user_role_info(self, user):
        """Get user role and permissions"""
        if hasattr(user, "admin_profile") and user.admin_profile.role:
            role = user.admin_profile.role
            return {
                "user_type": "admin",
                "role_name": role.name,
                "role_display": role.get_name_display(),
                "permissions": {
                    "can_manage_users": role.can_manage_users,
                    "can_view_all_clients": role.can_view_all_clients,
                    "can_edit_clients": role.can_edit_clients,
                    "can_manage_tickets": role.can_manage_tickets,
                    "can_manage_meetings": role.can_manage_meetings,
                    "can_create_content": role.can_create_content,
                    "can_publish_content": role.can_publish_content,
                    "can_view_analytics": role.can_view_analytics,
                    "can_view_billing": role.can_view_billing,
                    "can_manage_settings": role.can_manage_settings,
                    "can_view_ai_logs": role.can_view_ai_logs,
                },
            }
        elif hasattr(user, "profile") or hasattr(user, "client_profile"):
            from admin_portal.models import Client
            client_obj = Client.objects.filter(user=user).first()
            return {
                "user_type": "client",
                "client_id": client_obj.id if client_obj else None,
                "permissions": {
                    "can_access_portal": True,
                    "can_request_meetings": True,
                    "can_create_tickets": True,
                    "can_view_resources": True,
                },
            }
        return {"user_type": "unknown", "permissions": {}}
