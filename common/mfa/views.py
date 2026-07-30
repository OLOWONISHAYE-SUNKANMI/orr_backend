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


class MFALoginVerifyView(APIView):
    """
    Verifies TOTP code during login.
    Expected to be called after password login but before granting full access,
    or immediately after login if using a 2-step flow.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Verify MFA during Login", responses={200: dict, 400: dict})
    def post(self, request):
        user = request.user
        code = request.data.get('code')
        
        if not code:
            return Response({"error": "Code is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        
        config = SystemConfig.objects.first()
        mfa_enforced = config.mfa_enforced if config else False

        if not device:
            if mfa_enforced and user.is_staff: # typically enforced for admins
                return Response({"error": "MFA is required but not set up. Please contact an administrator."}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({"message": "MFA not set up, proceeding."}, status=status.HTTP_200_OK)

        if device.verify_token(code):
            refresh = RefreshToken.for_user(user)
            refresh['mfa_verified'] = True
            
            return Response({
                "message": "MFA verified successfully.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            })
        else:
            return Response({"error": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)
