from client.utils import create_password_reset_url


def send_password_reset_notification(user):
    """
    Send a password reset email to the user with UID + token URL.
    Uses branded ORR template: 02-password-reset.html
    """
    from admin_portal.orr_email_service import ORREmailService

    reset_url = create_password_reset_url(user)

    ORREmailService.send_password_reset(
        recipient_email=user.email,
        reset_link=reset_url,
    )

