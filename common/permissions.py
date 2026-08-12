from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from common import roles


class IsClientUser(BasePermission):
    """Permission for client portal users"""

    def has_permission(self, request, view):
        return roles.is_client(request.user)


class IsAdminUser(BasePermission):
    """Canonical admin permission: superuser or an active AdminProfile with a role.

    This is the single source of truth for "is an ORR admin"; pm.permissions and
    admin_portal.permissions both defer to roles.is_admin.
    """

    message = "You must be an ORR admin."

    def has_permission(self, request, view):
        return roles.is_admin(request.user)


class IsClientOrAdmin(BasePermission):
    """Permission for both client and admin users"""

    def has_permission(self, request, view):
        return roles.is_client(request.user) or roles.is_admin(request.user)


class HasActiveSubscription(BasePermission):
    """
    Allows access only to users with an active subscription.
    """

    def has_permission(self, request, view):
        user = request.user

        return (
            user.is_authenticated
            and hasattr(user, "subscription")
            and user.subscription.is_active
        )


class HasSubscriptionPlan(BasePermission):
    """
    Allows access only to users whose plan_name matches allowed plans.
    """

    allowed_plans = []  # e.g  allowed_plans = ["pro"]

    def has_permission(self, request, view):
        user = request.user

        if not (
            user.is_authenticated
            and hasattr(user, "subscription")
            and user.subscription.is_active
        ):
            return False

        return user.subscription.plan_name.lower() in [
            plan.lower() for plan in self.allowed_plans
        ]




class HasActivePaidSubscription(BasePermission):
    message = "Active subscription with valid payment method required."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        subscription = (
            user.subscriptions
            .filter(
                is_active=True
            )
            .select_related("plan")
            .order_by("-id")  
            .first()
        )

        if not subscription:
            raise PermissionDenied("Active subscription required.")

        stripe_profile = getattr(user, "stripe_profile", None)
        if not stripe_profile:
            raise PermissionDenied("No payment method on file.")

        if stripe_profile.last_payment_failed:
            raise PermissionDenied(
                "Payment failed. Please update your card to continue."
            )

        return True

class IsHardenedSuperAdmin(BasePermission):
    """
    Strict permission class for highly sensitive actions.
    Requires the user to be an active super_admin and to have a verified OTP device.
    """
    message = "Super Admin privileges with active 2FA required for this action."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Must be an active super_admin (superuser or role.name == 'super_admin')
        if not roles.is_super_admin(user):
            return False

        # Must have an OTP device verified (2FA enforcement check)
        from django_otp import user_has_device
        if not user_has_device(user):
            raise PermissionDenied("2FA must be enabled for this account to perform super admin actions.")

        return True