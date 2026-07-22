import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema
from rest_framework import status, views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer, OpenApiExample
from services.notifications.email_verification import (
    send_email_verification_notification,
)

from ..serializers.auth import LoginSerializer, SignUpSerializer

User = get_user_model()


@extend_schema(tags=["auth"])
class SignupView(views.APIView):
    permission_classes = [AllowAny]
    serializer_class = SignUpSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        first_name = serializer.validated_data["first_name"]
        last_name = serializer.validated_data["last_name"]
        user_type = serializer.validated_data.get("user_type", "client")
        admin_role = serializer.validated_data.get("admin_role")

        try:
            validate_password(password)
        except Exception as exc:
            return Response(
                {"error": "Weak password.", "details": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {"message": "Username already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"message": "Email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )
        user.set_password(password)
        user.save()

        # Create appropriate profile based on user type
        if user_type == "admin" and admin_role:
            from admin_portal.models import AdminProfile, AdminRole

            role_instance = AdminRole.objects.get(name=admin_role)
            AdminProfile.objects.create(user=user, role=role_instance)
        else:
            # Create client profile (handled by signals)
            pass

        try:
            send_email_verification_notification(user)
        except Exception as e:
            logging.error(f"Signup email failed to send: {e}")

        return Response(
            {"detail": "Registration successful. Email sent."},
            status=status.HTTP_201_CREATED,
        )




@extend_schema(tags=["auth"])
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

       
        refresh = RefreshToken.for_user(user)

        # Send login alert email in background
        from admin_portal.orr_email_service import ORREmailService
        import datetime
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if client_ip:
            client_ip = client_ip.split(',')[0]
        else:
            client_ip = request.META.get('REMOTE_ADDR', 'Unknown IP')
        
        try:
            ORREmailService.send_login_alert(
                recipient_email=user.email,
                login_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                ip_address=client_ip,
                location="Unknown Location",
                secure_account_link="https://orr.solutions/security"
            )
        except Exception as e:
            logging.error(f"Failed to send login alert: {e}")

        return Response(
            {
                "status": status.HTTP_200_OK,
                "message": "Login successful",
                "data": {
                    "accessToken": str(refresh.access_token),
                    "refreshToken": str(refresh),
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        **role_info,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
