from rest_framework.permissions import BasePermission
from .models import AdminProfile


class CanCreateContent(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            if admin_profile.role:
                role_name = admin_profile.role.name
                if role_name == 'super_admin':
                    return True
                if admin_profile.role.can_create_content:
                    return True
        except AdminProfile.DoesNotExist:
            pass
        return False


class CanPublishContent(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            if admin_profile.role:
                role_name = admin_profile.role.name
                if role_name == 'super_admin':
                    return True
                if admin_profile.role.can_publish_content:
                    return True
        except AdminProfile.DoesNotExist:
            pass
        return False


class CanManageUsers(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            if admin_profile.role:
                role_name = admin_profile.role.name
                if role_name == 'super_admin':
                    return True
                if admin_profile.role.can_manage_users:
                    return True
        except AdminProfile.DoesNotExist:
            pass
        return False


class CanManageSettings(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            if admin_profile.role:
                role_name = admin_profile.role.name
                if role_name == 'super_admin':
                    return True
                if admin_profile.role.can_manage_settings:
                    return True
        except AdminProfile.DoesNotExist:
            pass
        return False


class CanManageMeetings(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            if admin_profile.role:
                if admin_profile.role.can_manage_meetings:
                    return True
        except AdminProfile.DoesNotExist:
            pass
        return False


class CanManageTickets(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            if admin_profile.role:
                if admin_profile.role.can_manage_tickets:
                    return True
        except AdminProfile.DoesNotExist:
            pass
        return False


class IsAdminExceptContentEditor(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            if admin_profile.role:
                role_name = admin_profile.role.name
                if role_name in ['super_admin', 'admin', 'operator']:
                    return True
        except AdminProfile.DoesNotExist:
            pass
        return False


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            return admin_profile.role is not None
        except AdminProfile.DoesNotExist:
            pass
        return False


class CanEditClients(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            return admin_profile.role and admin_profile.role.can_edit_clients
        except AdminProfile.DoesNotExist:
            return False


class CanViewAllClients(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            return admin_profile.role and admin_profile.role.can_view_all_clients
        except AdminProfile.DoesNotExist:
            return False

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
            return admin_profile.role and admin_profile.role.name == 'super_admin'
        except AdminProfile.DoesNotExist:
            return False