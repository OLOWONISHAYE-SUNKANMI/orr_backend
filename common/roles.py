"""
Shared role resolver — the single source of truth for RBAC role checks.

Roles are inferred from the presence of a OneToOne profile on the auth User:
  - client      -> client.Profile          (related_name "profile")   [authoritative]
  - admin       -> admin_portal.AdminProfile (related_name "admin_profile", is_active, role FK)
  - consultant  -> consultation.Consultant   (related_name "consultant")
  - PM          -> AdminProfile with department == "PM" (not a separate model)

Note: admin_portal.Client (related_name "client_profile") is a CRM record, NOT a
role signal, and is never consulted here.

All helpers use the reverse OneToOne accessor via getattr(...) so this module has
no import-time dependency on admin_portal/consultation/client (avoids circular
imports, since those apps import from common).
"""

PM_DEPARTMENT = "PM"
SUPER_ADMIN_ROLE = "super_admin"


def get_admin_profile(user):
    """Return the user's active AdminProfile, or None.

    Treats a missing profile and an inactive profile identically (None).
    """
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, "admin_profile", None)
    if profile is not None and profile.is_active:
        return profile
    return None


def is_admin(user):
    """Superuser, or an active AdminProfile that has a role assigned."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = get_admin_profile(user)
    return bool(profile and profile.role is not None)


def is_super_admin(user):
    """Superuser, or an active AdminProfile whose role is 'super_admin'."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = get_admin_profile(user)
    return bool(profile and profile.role and profile.role.name == SUPER_ADMIN_ROLE)


def is_pm(user):
    """Superuser, or an active AdminProfile in the 'PM' department."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = get_admin_profile(user)
    return bool(profile and profile.department == PM_DEPARTMENT)


def is_non_pm_admin(user):
    """Superuser, or an active AdminProfile NOT in the 'PM' department.

    Used to distinguish "real" ORR admins/operators from project managers,
    who share the AdminProfile model but should not inherit full admin rights.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = get_admin_profile(user)
    return bool(profile and profile.department != PM_DEPARTMENT)


def is_client(user):
    """Authoritative client signal: presence of client.Profile ('profile')."""
    return bool(user and user.is_authenticated and hasattr(user, "profile"))


def is_consultant(user):
    """Presence of a consultation.Consultant ('consultant')."""
    return bool(user and user.is_authenticated and hasattr(user, "consultant"))
