"""
PM Permissions
Role-based access control for the PM workflow.
"""

from rest_framework.permissions import BasePermission


class IsPMUser(BasePermission):
    """
    User is the assigned PM for the project, or an Admin/SuperAdmin.
    Checks against PMProject.assigned_pm.
    """
    message = "You must be the assigned PM for this project."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ('admin', 'superadmin', 'superuser'):
            return True
        if getattr(request.user, 'is_staff', False):
            return True
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ('admin', 'superadmin', 'superuser'):
            return True
        if getattr(request.user, 'is_staff', False) and hasattr(request.user, 'admin_profile') and request.user.admin_profile.department != 'PM':
            return True
        if hasattr(obj, 'assigned_pm'):
            return obj.assigned_pm == request.user or obj.assigned_pm is None
        if hasattr(obj, 'project'):
            return obj.project.assigned_pm == request.user or obj.project.assigned_pm is None
        return False


class IsAdminUser(BasePermission):
    """
    User is an ORR admin or superadmin.
    """
    message = "You must be an ORR admin."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ('admin', 'superadmin', 'superuser'):
            return True
        if getattr(request.user, 'is_staff', False):
            return True
        if hasattr(request.user, 'admin_profile'):
            return request.user.admin_profile.department != 'PM'
        return False

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsPMOrAdmin(BasePermission):
    """
    User is either the assigned PM, an admin, or a superadmin.
    """
    message = "You must be the assigned PM or an ORR admin."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ('admin', 'superadmin', 'superuser'):
            return True
        if getattr(request.user, 'is_staff', False):
            return True
        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ('admin', 'superadmin', 'superuser'):
            return True
        if getattr(request.user, 'is_staff', False):
            return True
        if hasattr(request.user, 'admin_profile'):
            if request.user.admin_profile.department != 'PM':
                return True
        if hasattr(obj, 'assigned_pm'):
            return obj.assigned_pm == request.user or obj.assigned_pm is None
        if hasattr(obj, 'project'):
            return obj.project.assigned_pm == request.user or obj.project.assigned_pm is None
        return True


class IsAssignedConsultant(BasePermission):
    """
    User is the assigned consultant for the assignment or opportunity.
    """
    message = "You must be the assigned consultant."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ('admin', 'superadmin', 'superuser'):
            return True
        if not hasattr(request.user, 'consultant'):
            return False
        consultant = request.user.consultant
        if hasattr(obj, 'consultant'):
            return obj.consultant == consultant
        return False


class IsConsultantUser(BasePermission):
    """
    User has a consultant profile (for list views).
    """
    message = "You must be an approved consultant."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ('admin', 'superadmin', 'superuser'):
            return True
        return hasattr(request.user, 'consultant')


class CanAccessProject(BasePermission):
    """
    Enforces confidentiality and access-level rules.
    Superadmins and Admins always pass.
    """
    message = "You do not have permission to access this project."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or getattr(request.user, 'user_type', None) in ('admin', 'superadmin', 'superuser') or getattr(request.user, 'is_staff', False):
            return True
        project = obj if hasattr(obj, 'confidentiality_level') else getattr(obj, 'project', None)
        if not project:
            return True
        if project.assigned_pm == request.user:
            return True
        if hasattr(request.user, 'consultant'):
            return project.assignments.filter(
                consultant=request.user.consultant,
                status__in=['access_activated', 'active']
            ).exists()
        return False
