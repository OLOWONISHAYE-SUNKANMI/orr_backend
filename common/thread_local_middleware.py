import threading

_thread_locals = threading.local()

def get_current_user():
    """
    Get the current user from thread-local storage.
    Returns None if no user is set or if not authenticated.
    """
    user = getattr(_thread_locals, 'user', None)
    if user and user.is_authenticated:
        return user
    return None

from rest_framework_simplejwt.authentication import JWTAuthentication

class ThreadLocalUserMiddleware:
    """
    Middleware that stores the current request's user in thread-local storage.
    This is necessary for signals (like post_save) to attribute actions to a specific user
    in the AuditLog, since signals do not have access to the request object.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check standard Django auth first
        user = getattr(request, 'user', None)
        
        # If not authenticated, attempt to parse JWT token manually since DRF auth hasn't run yet
        if not user or not user.is_authenticated:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                try:
                    jwt_auth = JWTAuthentication()
                    token = auth_header.split(' ')[1]
                    validated_token = jwt_auth.get_validated_token(token)
                    user = jwt_auth.get_user(validated_token)
                except Exception:
                    pass

        # Set the user in thread-local storage
        _thread_locals.user = user
        try:
            response = self.get_response(request)
        finally:
            # Clean up after the request finishes to prevent memory leaks
            # and ensure the next request on this thread doesn't inherit the wrong user
            if hasattr(_thread_locals, 'user'):
                del _thread_locals.user
                
        return response
