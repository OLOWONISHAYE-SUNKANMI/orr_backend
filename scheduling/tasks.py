from celery import shared_task
import stripe
from django.conf import settings
from django.db import transaction
from admin_portal.models import Meeting
import uuid
from notification.utils import notify_user

stripe.api_key = settings.STRIPE_SECRET_KEY

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def charge_for_meeting(self, meeting_id):
    try:
        meeting = Meeting.objects.get(id=meeting_id)
        subscription = meeting.client.user.subscription
        plan = subscription.plan
        client_user = meeting.client.user

        if plan.billing_type != "metered":
            return "Skipped: Not a metered plan."

        hours_used = meeting.duration_hours
        if hours_used <= 0:
            return "Skipped: Invalid duration."
            
       
        customer_id = meeting.client.user.stripe_customer_id
        if not customer_id:
            raise ValueError(f"User {meeting.client.user.id} has no Stripe Customer ID.")

        # 3. IDEMPOTENCY KEY (Crucial for Senior Devs)
        # Prevents double billing if this task accidentally runs twice.
        # We combine 'meeting_charge' + meeting_id to make it unique.
        idempotency_key = f"meeting_charge_{meeting.id}"

        
        stripe.InvoiceItem.create(
            customer=customer_id,
            price=plan.stripe_price_id, 
            quantity=hours_used,
            description=f"Immediate Charge for Meeting #{meeting.id}",
            subscription=subscription.stripe_subscription_id, 
            idempotency_key=f"{idempotency_key}_item" 
        )

        invoice = stripe.Invoice.create(
            customer=customer_id,
            subscription=subscription.stripe_subscription_id, 
            auto_advance=True, # Auto-finalize this invoice
            description=f"Charge for Meeting {meeting.id}",
            idempotency_key=f"{idempotency_key}_invoice" # Unique key for invoice creation
        )

        # Step C: Force Payment (If auto_advance doesn't trigger fast enough)
        invoice = stripe.Invoice.finalize_invoice(invoice.id)
        
        # Attempt to pay. If card fails, this raises a stripe.error.CardError
        paid_invoice = stripe.Invoice.pay(invoice.id)
        amount_paid = paid_invoice.amount_paid / 100

        # Only update our local DB if the Stripe payment actually succeeded.
        with transaction.atomic():
            subscription.used_hours = (subscription.used_hours or 0) + hours_used
            subscription.save()

            # Send branded payment success email (16-payment-success)
            try:
                from admin_portal.orr_email_service import ORREmailService
                ORREmailService.send_payment_success(
                    recipient_email=client_user.email,
                    invoice_id=paid_invoice.id,
                    amount_paid=str(amount_paid),
                    currency_symbol='$',
                    payment_date=meeting.start_time.strftime('%B %d, %Y') if meeting.start_time else '',
                    payment_method='Stripe',
                    invoice_url=paid_invoice.hosted_invoice_url or 'https://orr.solutions/billing',
                )
            except Exception as email_err:
                logger.error("Failed to send payment success email: %s", email_err)

            notify_user(
            client_user,
            "Payment Successful",
            f"We successfully charged ${amount_paid} for your recent meeting.",
            ["inapp"],
            {
                "type": "payment_success",
            }
        )
            

        return f"Success: Charged ${paid_invoice.amount_paid / 100} on Invoice {paid_invoice.id}"

    except stripe.error.CardError as e:
        # The card was declined. Don't retry blindly, notify the user/admin.
        # Log this specific error or trigger a 'payment_failed' email task.

        # Send branded payment failed email (17-payment-failed)
        try:
            from admin_portal.orr_email_service import ORREmailService
            ORREmailService.send_payment_failed(
                recipient_email=meeting.client.user.email,
                invoice_id=f'meeting-{meeting_id}',
                failure_reason=e.user_message,
                update_payment_url='https://orr.solutions/billing',
            )
        except Exception as email_err:
            logger.error("Failed to send payment failed email: %s", email_err)

        notify_user(
            meeting.client.user,
            "Payment Failed: Action Required",
            f"Your payment for the recent meeting failed. Please update your card.",
            ["inapp"],
            {
                "type": "payment_failed",
            }
        )
        print(f"Payment Declined for Meeting {meeting_id}: {e}")
        return f"Failed: Card Declined - {e.user_message}"

    except Exception as e:
        # For network errors or other crashes, we retry.
        # Idempotency keys above protect us from double-charging during retries.
        self.retry(exc=e)


@shared_task
def send_meeting_reminders():
    """Periodic task to send meeting reminders 1 hour before start"""
    from django.utils import timezone
    from datetime import timedelta
    import logging
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    # Find meetings starting between 55 and 65 minutes from now
    target_time_start = now + timedelta(minutes=55)
    target_time_end = now + timedelta(minutes=65)

    meetings = Meeting.objects.filter(
        status='confirmed',
        requested_datetime__gte=target_time_start,
        requested_datetime__lte=target_time_end
    )

    for meeting in meetings:
        # Prevent duplicate reminders (we could use a flag or cache, but checking this narrow window handles most cases)
        try:
            from admin_portal.orr_email_service import ORREmailService
            from django.contrib.auth.models import User
            
            meeting_time = meeting.requested_datetime.strftime("%Y-%m-%d %H:%M UTC")
            
            # 1. Send to client
            if meeting.client and meeting.client.user.email:
                ORREmailService.send_meeting_reminder(
                    recipient_email=meeting.client.user.email,
                    meeting_subject=f"{meeting.get_meeting_type_display()} with ORR Solutions",
                    meeting_time=meeting_time,
                    minutes_until="60",
                    meeting_link=meeting.meeting_link or "Link will be provided"
                )
            
            # 2. Send to Admin / Host
            admin_emails = []
            if meeting.host and meeting.host.email:
                admin_emails.append(meeting.host.email)
            else:
                # If no host, find superusers or users with 'admin' role
                from admin_portal.models import AdminRole
                admins = User.objects.filter(is_superuser=True, is_active=True)
                for admin in admins:
                    if admin.email:
                        admin_emails.append(admin.email)
                        
            # Remove duplicates
            admin_emails = list(set(admin_emails))
            
            for admin_email in admin_emails:
                ORREmailService.send_meeting_reminder(
                    recipient_email=admin_email,
                    meeting_subject=f"Upcoming {meeting.get_meeting_type_display()} with {meeting.client.user.get_full_name() if meeting.client else 'Client'}",
                    meeting_time=meeting_time,
                    minutes_until="60",
                    meeting_link=meeting.meeting_link or "Link will be provided"
                )
        except Exception as e:
            logger.error(f"Failed to send meeting reminder for meeting {meeting.id}: {e}")