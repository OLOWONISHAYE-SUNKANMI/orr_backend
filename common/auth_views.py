from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
from admin_portal.models import AdminProfile
from client.models import Profile as ClientProfile
from rest_framework import serializers
from client.v1.serializers.auth import LoginSerializer

class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.DictField()

@extend_schema(
    tags=["Authentication"],
    summary="Login for content editors",
    description="Authenticate content editors and return JWT tokens",
    request=LoginSerializer,
    responses={200: LoginResponseSerializer},
    examples=[
        OpenApiExample(
            "Login Example",
            value={"email": "editor@example.com", "password": "editor123"},
            request_only=True
        )
    ]
)
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        role_info = serializer.validated_data["role_info"]

       
        from admin_portal.models import SystemConfig
        config = SystemConfig.objects.first()
        mfa_required = config.mfa_enforced if config else False
        
        refresh = RefreshToken.for_user(user)
        if mfa_required and user.is_staff:
            refresh['mfa_verified'] = False
        else:
            refresh['mfa_verified'] = True

        return Response(
            {
                "status": status.HTTP_200_OK,
                "message": "Login successful",
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        **role_info,
                    },
                    "mfa_required": mfa_required and user.is_staff
                },
            },
            status=status.HTTP_200_OK,
        )

import os
import uuid
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth import get_user_model

User = get_user_model()

class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField()
    portal = serializers.CharField(required=False, allow_null=True, default="client")

@extend_schema(
    tags=["Authentication"],
    summary="Login with Google",
    description="Authenticate clients using Google credential token",
    request=GoogleLoginSerializer,
    responses={200: LoginResponseSerializer},
)
@method_decorator(csrf_exempt, name='dispatch')
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = GoogleLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["credential"]
        portal = serializer.validated_data.get("portal", "client")
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        
        try:
            if not client_id:
                return Response(
                    {"message": "Google authentication is not configured on the server."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            # Specify the CLIENT_ID of the app that accesses the backend:
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
            
            # ID token is valid. Get the user's Google Account ID from the decoded token.
            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")
            
            if not email:
                return Response(
                    {"message": "Google authentication failed: Email not found in token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
                
            # Find or create user
            user = User.objects.filter(email__iexact=email).first()
            is_new_user = False
            
            # If the portal is admin or PM, the user MUST already exist and have the correct profile.
            if portal in ["admin", "pm"]:
                if not user:
                    return Response(
                        {"message": "Account not found. Access denied."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                if not hasattr(user, 'admin_profile'):
                    return Response(
                        {"message": "Unauthorized portal access. Admin profile not found."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                    
            if not user:
                is_new_user = True
                # Create a new user
                base_username = f"{first_name.lower()}{last_name.lower()}".replace(" ", "")
                if not base_username:
                    base_username = email.split('@')[0]
                
                # Ensure username uniqueness
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,  # Google verified emails are safe to activate
                )
                user.set_unusable_password()
                user.save()
            else:
                # Sync names if missing
                save_user = False
                if not user.first_name and first_name:
                    user.first_name = first_name
                    save_user = True
                if not user.last_name and last_name:
                    user.last_name = last_name
                    save_user = True
                
                # If user exists but is inactive, activate them since they logged in with Google
                if not user.is_active:
                    user.is_active = True
                    save_user = True
                
                if save_user:
                    user.save()
            
            if portal == "consultant":
                # Ensure consultant profile
                from consultation.models import Consultant
                import uuid
                if not hasattr(user, 'consultant'):
                    Consultant.objects.create(
                        user=user,
                        consultant_number=f"CON-{uuid.uuid4().hex[:6].upper()}",
                        status="EMAIL_VERIFIED"
                    )
            elif portal == "client":
                # Ensure Profile and Client records exist for this user
                from client.models import Profile as ClientProfile
                ClientProfile.objects.get_or_create(user=user)
                
                from admin_portal.models import Client as ClientRecord
                try:
                    user.admin_profile  # If this exists, user is an admin - skip client creation
                except Exception:
                    try:
                        user.consultant # Also skip if they are already a consultant
                    except Exception:
                        ClientRecord.objects.get_or_create(
                            user=user,
                            defaults={
                                'company': 'N/A',
                                'primary_pillar': 'strategic',
                            }
                        )
                    
            # Get role info (replicating LoginSerializer's _get_user_role_info)
            role_info = self._get_user_role_info(user)
            
            from admin_portal.models import SystemConfig
            config = SystemConfig.objects.first()
            mfa_required = config.mfa_enforced if config else False
            
            refresh = RefreshToken.for_user(user)
            if mfa_required and user.is_staff:
                refresh['mfa_verified'] = False
            else:
                refresh['mfa_verified'] = True

            return Response(
                {
                    "status": status.HTTP_200_OK,
                    "message": "Login successful",
                    "data": {
                        "access": str(refresh.access_token),
                        "accessToken": str(refresh.access_token),
                        "refresh": str(refresh),
                        "refreshToken": str(refresh),
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            **role_info,
                        },
                        "mfa_required": mfa_required and user.is_staff
                    },
                },
                status=status.HTTP_200_OK,
            )
            
        except ValueError as e:
            # Invalid token
            return Response(
                {"message": f"Invalid Google token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def _get_user_role_info(self, user):
        """Get user role and permissions"""
        try:
            admin_profile = user.admin_profile
            if admin_profile:
                role = admin_profile.role
                permissions = {}
                if role:
                    permissions = {
                        "can_manage_users": role.can_manage_users,
                        "can_view_all_clients": role.can_view_all_clients,
                        "can_edit_clients": role.can_edit_clients,
                        "can_manage_tickets": role.can_manage_tickets,
                        "can_manage_meetings": role.can_manage_meetings,
                        "can_create_content": role.can_create_content,
                        "can_publish_content": role.can_publish_content,
                        "can_view_analytics": role.can_view_analytics,
                        "can_view_billing": role.can_view_billing,
                        "can_manage_settings": role.can_manage_settings,
                        "can_view_ai_logs": role.can_view_ai_logs,
                    }
                return {
                    "user_type": "admin",
                    "role_name": role.name if role else None,
                    "role_display": role.get_name_display() if role else None,
                    "is_onboarding_complete": admin_profile.is_onboarding_complete,
                    "permissions": permissions,
                }
        except Exception:
            pass
            
        try:
            consultant_profile = user.consultant
            if consultant_profile:
                return {
                    "user_type": "consultant",
                    "consultant_number": consultant_profile.consultant_number,
                    "status": consultant_profile.status,
                    "permissions": {
                        "can_access_portal": consultant_profile.status in ['PENDING_REVIEW', 'APPROVED', 'NEEDS_CLARIFICATION'],
                        "can_accept_jobs": consultant_profile.status == 'APPROVED',
                    },
                }
        except Exception:
            pass
            
        # Default to client permissions
        from admin_portal.models import Client
        client_obj = Client.objects.filter(user=user).first()
        return {
            "user_type": "client",
            "client_id": client_obj.id if client_obj else None,
            "permissions": {
                "can_access_portal": True,
                "can_request_meetings": True,
                "can_create_tickets": True,
                "can_view_resources": True,
            },
        }