import time
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from admin_portal.models import SystemConfig


class SessionTimeoutJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that enforces a session timeout based on SystemConfig.
    Tracks the last activity time in cache for each user.
    """
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, token = result
        
        # Get configured timeout, default to 60 minutes if not set or config missing
        config = SystemConfig.objects.first()
        timeout_str = config.session_timeout if config and config.session_timeout else '60'
        
        # Parse timeout string (e.g., '1h', '30m', '60') into minutes
        try:
            timeout_str = str(timeout_str).strip().lower()
            if timeout_str.endswith('h'):
                timeout_minutes = int(timeout_str[:-1]) * 60
            elif timeout_str.endswith('m'):
                timeout_minutes = int(timeout_str[:-1])
            else:
                timeout_minutes = int(timeout_str)
        except (ValueError, TypeError):
            timeout_minutes = 60  # Default fallback
        
        timeout_seconds = timeout_minutes * 60

        cache_key = f"user_last_activity_{user.id}"
        last_activity = cache.get(cache_key)
        current_time = time.time()

        if last_activity:
            time_elapsed = current_time - last_activity
            if time_elapsed > timeout_seconds:
                # Session expired due to inactivity
                cache.delete(cache_key)
                raise AuthenticationFailed("Session expired due to inactivity.", code="session_expired")
        
        # Update last activity
        cache.set(cache_key, current_time, timeout=timeout_seconds * 2)

        return user, token
