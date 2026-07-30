from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from admin_portal.models import SystemConfig

class MFAEnforcementMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith('/api/auth/login') or request.path.startswith('/api/auth/mfa') or request.path.startswith('/admin'):
            return None
            
        if request.user.is_authenticated:
            # Check if MFA is enforced globally
            config = SystemConfig.objects.first()
            if config and config.mfa_enforced:
                
                # Determine user roles
                roles = set()
                if request.user.is_superuser:
                    roles.add('super_admin')
                if request.user.is_staff:
                    roles.add('staff')
                if hasattr(request.user, 'admin_profile') and request.user.admin_profile.is_active:
                    if request.user.admin_profile.role:
                        roles.add(request.user.admin_profile.role.name)
                    else:
                        roles.add('admin')
                if hasattr(request.user, 'profile'): # Client profile
                    roles.add('client')
                if hasattr(request.user, 'consultant'):
                    roles.add('consultant')

                enforced_roles = config.mfa_enforced_roles
                requires_mfa = False
                
                if enforced_roles:
                    if "all" in enforced_roles:
                        requires_mfa = True
                    else:
                        requires_mfa = any(role in enforced_roles for role in roles)
                else:
                    # Fallback if unconfigured
                    requires_mfa = request.user.is_staff

                if requires_mfa:
                    mfa_verified = request.session.get('mfa_verified', False)
                    # For JWT, check claims
                    if hasattr(request, 'auth') and request.auth:
                        token = request.auth
                        if not token.get('mfa_verified', False):
                            return JsonResponse({"error": "MFA Verification Required", "code": "mfa_required"}, status=401)
        return None
