from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_portal.permissions import IsAdminUser


def _build_all_true_permissions():
    """Return a permissions dict with all fields set to True (super admin)."""
    return {
        "can_manage_users": True,
        "can_view_all_clients": True,
        "can_edit_clients": True,
        "can_manage_tickets": True,
        "can_manage_meetings": True,
        "can_create_content": True,
        "can_publish_content": True,
        "can_view_analytics": True,
        "can_view_billing": True,
        "can_manage_settings": True,
        "can_view_ai_logs": True,
        "can_manage_roles": True,
        "can_view_audit_logs": True,
        "can_view_security_events": True,
        "can_approve_sensitive_actions": True,
        "can_configure_system": True,
    }


def _build_role_permissions(role):
    """Build permissions dict from an AdminRole instance."""
    return {
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
        "can_manage_roles": getattr(role, 'can_manage_roles', False),
        "can_view_audit_logs": getattr(role, 'can_view_audit_logs', False),
        "can_view_security_events": getattr(role, 'can_view_security_events', False),
        "can_approve_sensitive_actions": getattr(role, 'can_approve_sensitive_actions', False),
        "can_configure_system": getattr(role, 'can_configure_system', False),
    }


@extend_schema(
    tags=["Authentication"],
    summary="Get current user role and permissions",
    description="Retrieve the current authenticated user's role, permissions, and access levels for the admin portal.",
)
class CurrentUserRoleView(APIView):
    """Get current user's role and permissions — spec-compliant /me endpoint."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        user = request.user

        # Django superuser with no admin_profile
        if not hasattr(user, 'admin_profile') or user.admin_profile is None:
            return Response({
                "id": f"USR-{user.id}",
                "username": user.username,
                "email": user.email,
                "role_name": "super_admin" if user.is_superuser else None,
                "role_display": "Super Admin" if user.is_superuser else None,
                "permissions": _build_all_true_permissions() if user.is_superuser else {},
            })

        admin_profile = user.admin_profile
        role = admin_profile.role

        # Super admin gets all permissions regardless of role flags
        if user.is_superuser or (role and role.name == 'super_admin'):
            perms = _build_all_true_permissions()
        elif role:
            perms = _build_role_permissions(role)
        else:
            perms = {}

        return Response({
            "id": f"USR-{user.id}",
            "username": user.username,
            "email": user.email,
            "role_name": role.name if role else None,
            "role_display": role.get_name_display() if role else None,
            "permissions": perms,
        })


@extend_schema(
    tags=["Authentication"],
    summary="Check specific permission",
    description="Check if the current user has a specific permission for conditional UI rendering.",
)
class CheckPermissionView(APIView):
    """Check if user has specific permission"""

    permission_classes = [IsAdminUser]

    def post(self, request):
        permission = request.data.get("permission")
        user = request.user

        # Superusers always have all permissions
        if user.is_superuser:
            return Response({"permission": permission, "has_permission": True})

        if not hasattr(user, "admin_profile") or not user.admin_profile:
            return Response({"permission": permission, "has_permission": False})

        role = user.admin_profile.role
        if not role:
            return Response({"permission": permission, "has_permission": False})

        if role.name == 'super_admin':
            return Response({"permission": permission, "has_permission": True})

        permission_map = {
            "manage_users": role.can_manage_users,
            "view_all_clients": role.can_view_all_clients,
            "edit_clients": role.can_edit_clients,
            "manage_tickets": role.can_manage_tickets,
            "manage_meetings": role.can_manage_meetings,
            "create_content": role.can_create_content,
            "publish_content": role.can_publish_content,
            "view_analytics": role.can_view_analytics,
            "view_billing": role.can_view_billing,
            "manage_settings": role.can_manage_settings,
            "view_ai_logs": role.can_view_ai_logs,
            "manage_roles": getattr(role, 'can_manage_roles', False),
            "view_audit_logs": getattr(role, 'can_view_audit_logs', False),
            "view_security_events": getattr(role, 'can_view_security_events', False),
            "approve_sensitive_actions": getattr(role, 'can_approve_sensitive_actions', False),
            "configure_system": getattr(role, 'can_configure_system', False),
        }

        has_permission = permission_map.get(permission, False)
        return Response({"permission": permission, "has_permission": has_permission})
