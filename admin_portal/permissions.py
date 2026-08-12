from rest_framework.permissions import BasePermission
from common import roles


class CanCreateContent(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        if admin_profile and admin_profile.role:
            if admin_profile.role.name == 'super_admin':
                return True
            if admin_profile.role.can_create_content:
                return True
        return False


class CanPublishContent(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        if admin_profile and admin_profile.role:
            if admin_profile.role.name == 'super_admin':
                return True
            if admin_profile.role.can_publish_content:
                return True
        return False


class CanManageUsers(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        if admin_profile and admin_profile.role:
            if admin_profile.role.name == 'super_admin':
                return True
            if admin_profile.role.can_manage_users:
                return True
        return False


class CanManageSettings(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        if admin_profile and admin_profile.role:
            if admin_profile.role.name == 'super_admin':
                return True
            if admin_profile.role.can_manage_settings:
                return True
        return False


class CanManageMeetings(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        if admin_profile and admin_profile.role:
            if admin_profile.role.can_manage_meetings:
                return True
        return False


class CanManageTickets(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        if admin_profile and admin_profile.role:
            if admin_profile.role.can_manage_tickets:
                return True
        return False


class IsAdminExceptContentEditor(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        if admin_profile and admin_profile.role:
            if admin_profile.role.name in ['super_admin', 'admin', 'operator']:
                return True
        return False


class IsAdminUser(BasePermission):
    """Admin permission for admin_portal views.

    Delegates to the canonical roles.is_admin (superuser or active AdminProfile
    with a role). Kept in this module because many admin_portal views import it
    from here.
    """
    def has_permission(self, request, view):
        return roles.is_admin(request.user)


class CanEditClients(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        return bool(admin_profile and admin_profile.role and admin_profile.role.can_edit_clients)


class CanViewAllClients(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        admin_profile = roles.get_admin_profile(request.user)
        return bool(admin_profile and admin_profile.role and admin_profile.role.can_view_all_clients)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return roles.is_super_admin(request.user)
