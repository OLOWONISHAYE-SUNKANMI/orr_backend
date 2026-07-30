from django.urls import path
from .views import MFASetupView, MFAVerifySetupView, MFALoginVerifyView, MFAResendOTPView

urlpatterns = [
    path('setup/', MFASetupView.as_view(), name='mfa-setup'),
    path('setup/verify/', MFAVerifySetupView.as_view(), name='mfa-setup-verify'),
    path('verify/', MFALoginVerifyView.as_view(), name='mfa-verify'),
    path('resend/', MFAResendOTPView.as_view(), name='mfa-resend'),
]
