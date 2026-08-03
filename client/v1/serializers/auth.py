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
    portal = serializers.CharField(required=False, allow_null=True, default="client")

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        portal = attrs.get("portal", "client")

        if not email or not password:
            raise serializers.ValidationError(
                "Email and password are required."
            )
        

        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        
        if not user:
            raise serializers.ValidationError("Invalid login credentials.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid login credentials.")
            
        if not user.is_active:
            send_email_verification_notification(user)
            raise serializers.ValidationError(
                "Account not verified. A verification email has been sent."
            )
            
        # Profile Syncing Logic based on portal (mirrored from GoogleLoginView)
        if portal == "consultant":
            # Ensure consultant profile
            from consultation.models import Consultant
            import uuid
            if not hasattr(user, 'consultant'):
                Consultant.objects.create(
                    user=user,
                    consultant_number=f"CON-{uuid.uuid4().hex[:6].upper()}",
                    status="EMAIL_VERIFIED"
                )
        elif portal == "client":
            # Ensure Profile and Client records exist for this user
            from client.models import Profile as ClientProfile
            ClientProfile.objects.get_or_create(user=user)
            
            from admin_portal.models import Client as ClientRecord
            try:
                user.admin_profile
            except Exception:
                try:
                    user.consultant
                except Exception:
                    ClientRecord.objects.get_or_create(
                        user=user,
                        defaults={
                            'company': 'N/A',
                            'primary_pillar': 'strategic',
                        }
                    )
        elif portal in ["admin", "pm"]:
            if not hasattr(user, 'admin_profile'):
                if portal == "pm" and hasattr(user, 'consultant'):
                    pass
                elif getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
                    # Auto-heal missing AdminProfile for staff members
                    from admin_portal.models import AdminRole, AdminProfile
                    admin_role, _ = AdminRole.objects.get_or_create(
                        name="admin",
                        defaults={"description": "Default admin role"}
                    )
                    AdminProfile.objects.create(user=user, role=admin_role, is_active=True)
                else:
                    raise serializers.ValidationError("Unauthorized portal access. Admin profile not found.")
        # Get user role info
        role_info = self._get_user_role_info(user)
        attrs["user"] = user
        attrs["role_info"] = role_info
        return attrs

    def _get_user_role_info(self, user):
        """Get user role and permissions"""
        if hasattr(user, "admin_profile"):
            role = user.admin_profile.role
            permissions = {}
            if role:
                permissions = {
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
                }
            return {
                "user_type": "admin",
                "role_name": role.name if role else None,
                "role_display": role.get_name_display() if role else None,
                "is_onboarding_complete": user.admin_profile.is_onboarding_complete,
                "permissions": permissions,
            }
        elif hasattr(user, "consultant"):
            consultant = user.consultant
            return {
                "user_type": "consultant",
                "consultant_number": consultant.consultant_number,
                "status": consultant.status,
                "permissions": {
                    "can_access_portal": True,
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
