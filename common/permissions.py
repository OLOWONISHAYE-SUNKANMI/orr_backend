from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

class IsClientUser(BasePermission):
    """Permission for client portal users"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and hasattr(request.user, "profile")


class IsAdminUser(BasePermission):
    """Permission for admin portal users"""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, "admin_profile")
            and request.user.admin_profile.is_active
        )


class IsClientOrAdmin(BasePermission):
    """Permission for both client and admin users"""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return hasattr(request.user, "profile") or (
            hasattr(request.user, "admin_profile")
            and request.user.admin_profile.is_active
        )


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