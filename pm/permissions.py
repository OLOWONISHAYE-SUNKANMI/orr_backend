"""
PM Permissions
Role-based access control for the PM workflow.
"""

from rest_framework.permissions import BasePermission


class IsPMUser(BasePermission):
    """
    User is the assigned PM for the project.
    Checks against PMProject.assigned_pm.
    """
    message = "You must be the assigned PM for this project."

    def has_object_permission(self, request, view, obj):
        # Handle PMProject directly
        if hasattr(obj, 'assigned_pm'):
            return obj.assigned_pm == request.user
        # Handle objects with a project FK (PMTask, PMAssignment, etc.)
        if hasattr(obj, 'project'):
            return obj.project.assigned_pm == request.user
        return False


class IsAdminUser(BasePermission):
    """
    User is an ORR admin (staff user with admin_profile).
    """
    message = "You must be an ORR admin."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff and hasattr(request.user, 'admin_profile') and request.user.admin_profile.department != 'PM'


class IsPMOrAdmin(BasePermission):
    """
    User is either the assigned PM or an admin.
    For list views, allows any authenticated PM or admin.
    For object views, checks PM assignment.
    """
    message = "You must be the assigned PM or an ORR admin."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Admins always pass
        if request.user.is_staff and hasattr(request.user, 'admin_profile'):
            if request.user.admin_profile.department != 'PM':
                return True
        # PMs pass list views
        if request.user.is_staff and hasattr(request.user, 'admin_profile') and request.user.admin_profile.department == 'PM':
            return True
        return False

    def has_object_permission(self, request, view, obj):
        # Admins always pass
        if request.user.is_staff and hasattr(request.user, 'admin_profile'):
            if request.user.admin_profile.department != 'PM':
                return True
        # Check PM assignment
        if hasattr(obj, 'assigned_pm'):
            return obj.assigned_pm == request.user
        if hasattr(obj, 'project'):
            return obj.project.assigned_pm == request.user
        return False


class IsAssignedConsultant(BasePermission):
    """
    User is the assigned consultant for the assignment or opportunity.
    """
    message = "You must be the assigned consultant."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
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
        return hasattr(request.user, 'consultant')


class CanAccessProject(BasePermission):
    """
    Enforces confidentiality and access-level rules.
    For Restricted Access or Highly Confidential projects,
    only consultants with appropriate admin clearance are selectable.
    """
    message = "You do not have permission to access this project."

    def has_object_permission(self, request, view, obj):
        project = obj if hasattr(obj, 'confidentiality_level') else getattr(obj, 'project', None)
        if not project:
            return True

        # Admins always have access
        if request.user.is_staff:
            return True

        # PMs have access to their projects
        if project.assigned_pm == request.user:
            return True

        # Consultants: check if they have an active assignment
        if hasattr(request.user, 'consultant'):
            return project.assignments.filter(
                consultant=request.user.consultant,
                status__in=['access_activated', 'active']
            ).exists()

        return False
