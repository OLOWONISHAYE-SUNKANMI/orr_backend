from rest_framework.throttling import UserRateThrottle
from admin_portal.models import AdminProfile

class AdminRateThrottle(UserRateThrottle):
    scope = 'admin'

    def allow_request(self, request, view):
        if request.user.is_authenticated:
            # Check if user is an admin
            try:
                admin_profile = AdminProfile.objects.get(user=request.user, is_active=True)
                if admin_profile.role and admin_profile.role.name != 'super_admin':
                    return super().allow_request(request, view)
            except AdminProfile.DoesNotExist:
                pass
        
        # Super admins and non-admins bypass this specific throttle
        return True
class DocumentDownloadThrottle(UserRateThrottle):
    scope = 'document_download'

    def allow_request(self, request, view):
        if request.user.is_authenticated and not request.user.is_superuser:
            # Throttle standard admins or users
            return super().allow_request(request, view)
        
        # Super admins bypass this specific throttle
        return True
