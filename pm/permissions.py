"""
PM Permissions
Role-based access control for the PM workflow.

Role checks delegate to common.roles (the single source of truth). IsAdminUser is
re-exported from common.permissions so there is exactly one admin definition.
"""

from rest_framework.permissions import BasePermission

from common import roles
from common.permissions import IsAdminUser  # canonical; re-exported below

__all__ = [
    "IsPMUser",
    "IsAdminUser",
    "IsPMOrAdmin",
    "IsAssignedConsultant",
    "IsConsultantUser",
    "CanAccessProject",
]


def _object_pm_check(user, obj):
    """Shared object-level rule for PM-scoped resources.

    Non-PM admins (and superusers) always pass; a PM passes only for objects they
    are assigned to (or unassigned objects). Returns False otherwise.
    """
    if roles.is_non_pm_admin(user):
        return True
    if roles.is_pm(user):
        if hasattr(obj, 'assigned_pm'):
            return obj.assigned_pm == user or obj.assigned_pm is None
        if hasattr(obj, 'project'):
            return obj.project.assigned_pm == user or obj.project.assigned_pm is None
    return False


class IsPMUser(BasePermission):
    """
    User is a project manager, or an Admin/SuperAdmin.
    Object-level access is restricted to the assigned PM.
    """
    message = "You must be the assigned PM for this project."

    def has_permission(self, request, view):
        return roles.is_pm(request.user) or roles.is_non_pm_admin(request.user)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return _object_pm_check(request.user, obj)


class IsPMOrAdmin(BasePermission):
    """
    User is either a PM, an admin, or a superadmin.
    """
    message = "You must be the assigned PM or an ORR admin."

    def has_permission(self, request, view):
        return roles.is_admin(request.user) or roles.is_pm(request.user)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return _object_pm_check(request.user, obj)


class IsAssignedConsultant(BasePermission):
    """
    User is the assigned consultant for the assignment or opportunity.
    """
    message = "You must be the assigned consultant."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if roles.is_admin(request.user):
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
        if roles.is_admin(request.user):
            return True
        return roles.is_consultant(request.user)


class CanAccessProject(BasePermission):
    """
    Enforces confidentiality and access-level rules.
    Admins and superadmins always pass.
    """
    message = "You do not have permission to access this project."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if roles.is_admin(request.user):
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
