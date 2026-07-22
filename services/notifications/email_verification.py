from client.utils import build_verify_password_url


def send_email_verification_notification(user):
    """
    Send verification email to a newly registered user.
    Uses branded ORR template: 01-email-verification.html
    """
    from admin_portal.orr_email_service import ORREmailService

    verification_url = build_verify_password_url(user)

    ORREmailService.send_email_verification(
        recipient_email=user.email,
        verification_link=verification_url,
        verification_token=verification_url.split('/')[-1] if '/' in verification_url else '',
    )

