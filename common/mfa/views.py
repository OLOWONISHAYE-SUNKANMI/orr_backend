import base64
import io
import qrcode
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django_otp.plugins.otp_totp.models import TOTPDevice
from drf_spectacular.utils import extend_schema
from admin_portal.models import SystemConfig


class MFASetupView(APIView):
    """
    Generates a new TOTP secret for the user and returns a QR code image (base64)
    along with the provisioning URL.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Setup MFA", responses={200: dict})
    def get(self, request):
        user = request.user
        # Delete unconfirmed devices
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        
        # Create a new unconfirmed device
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=False)
        
        url = device.config_url
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        return Response({
            "qr_code_base64": f"data:image/png;base64,{image_base64}",
            "provisioning_url": url,
            "secret": device.key,
        })


class MFAVerifySetupView(APIView):
    """
    Verifies the TOTP code to confirm the device setup.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Verify MFA Setup", responses={200: dict, 400: dict})
    def post(self, request):
        user = request.user
        code = request.data.get('code')
        
        if not code:
            return Response({"error": "Code is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if not device:
            return Response({"error": "No pending MFA setup found"}, status=status.HTTP_400_BAD_REQUEST)
            
        if device.verify_token(code):
            # Confirm device
            device.confirmed = True
            device.save()
            return Response({"message": "MFA setup successfully verified."})
        else:
            return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)


from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.core.cache import cache

class MFALoginVerifyView(APIView):
    """
    Verifies Email OTP code during login.
    Expected to be called after password login but before granting full access,
    or immediately after login if using a 2-step flow.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Verify MFA during Login", responses={200: dict, 400: dict})
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return Response({"error": "Email and code are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
        cache_key = f"mfa_otp_{user.email}"
        cached_code = cache.get(cache_key)
        
        if not cached_code:
            return Response({"error": "OTP has expired or was not generated. Please login again."}, status=status.HTTP_400_BAD_REQUEST)
            
        if str(code).strip() == str(cached_code).strip():
            cache.delete(cache_key)
            refresh = RefreshToken.for_user(user)
            refresh['mfa_verified'] = True
            
            return Response({
                "success": True,
                "message": "MFA verified successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            })
        else:
            return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)

from common.auth_views import generate_and_send_mfa_code

class MFAResendOTPView(APIView):
    """
    Resends Email OTP code during login.
    """
    permission_classes = [AllowAny]

    @extend_schema(summary="Resend Email OTP", responses={200: dict, 400: dict})
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"success": True, "message": "If the email is valid, a new code has been sent."})
            
        generate_and_send_mfa_code(user)
        
        return Response({
            "success": True,
            "message": "A new code has been sent to your email."
        })
