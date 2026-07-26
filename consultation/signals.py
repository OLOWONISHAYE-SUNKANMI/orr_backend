import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Consultant

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=Consultant)
def capture_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Consultant.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Consultant.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Consultant)
def process_consultant_approval(sender, instance, created, **kwargs):
    # Check if the status transitioned to APPROVED
    old_status = getattr(instance, '_old_status', None)
    
    if instance.status == 'APPROVED' and old_status != 'APPROVED':
        logger.info(f"Consultant {instance.consultant_number} has been APPROVED. Triggering Workspace provisioning.")
        
        # 1. Determine Professional Display Name or Full Name
        display_name = ""
        try:
            profile = instance.profile
            display_name = profile.display_name if profile.display_name else profile.full_name
        except Exception:
            pass
            
        if not display_name:
            display_name = instance.user.first_name + " " + instance.user.last_name
            
        display_name = display_name.strip()
        if not display_name:
            display_name = f"consultant-{instance.consultant_number.lower()}"
            
        # 2. Generate ORR Email Alias format
        # Example: john.doe@orr.solutions
        formatted_name = display_name.replace(" ", ".").lower()
        orr_email_alias = f"{formatted_name}@orr.solutions"
        
        # 3. Simulate Google Workspace API call to create alias and set routing
        personal_email = instance.user.email
        logger.info(f"[WORKSPACE API MOCK] Created alias {orr_email_alias} for {personal_email}")
        logger.info(f"[WORKSPACE API MOCK] Configured email forwarding from {orr_email_alias} to {personal_email}")
        
        # In a real environment, you would call the Google Admin SDK Directory API here:
        # service = build('admin', 'directory_v1', credentials=creds)
        # alias = {'alias': orr_email_alias}
        # service.users().aliases().insert(userKey=personal_email, body=alias).execute()
        
        # Update user with the new alias conceptually (or save to a field if needed)
        # instance.admin_notes += f"\nWorkspace Alias {orr_email_alias} provisioned."
        # instance.save(update_fields=['admin_notes'])

        # Send workspace setup / approval email to consultant
        try:
            from admin_portal.orr_email_service import ORREmailService
            ORREmailService.send_workspace_setup(
                recipient_email=personal_email,
                workspace_url='https://consultant.orr.solutions/dashboard',
                workspace_email=orr_email_alias,
                storage_limit='5 GB'
            )
            logger.info(f"Workspace setup email sent to {personal_email}")
        except Exception as e:
            logger.error(f"Failed to send workspace setup email: {e}")

@receiver(pre_save, sender='consultation.ConsultantInvoice')
def capture_old_invoice_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            from .models import ConsultantInvoice
            old_instance = ConsultantInvoice.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except ConsultantInvoice.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender='consultation.ConsultantInvoice')
def process_invoice_notifications(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)
    
    try:
        from admin_portal.orr_email_service import ORREmailService
        recipient_email = instance.consultant.user.email
        
        # 1. Invoice submitted
        if created and instance.status == 'SUBMITTED':
            ORREmailService.send_consultant_invoice_confirm(
                recipient_email=recipient_email,
                invoice_id=instance.invoice_number,
                submission_date=instance.submitted_at.strftime("%Y-%m-%d"),
                tracking_url=f"https://consultant.orr.solutions/invoices/{instance.invoice_number}"
            )
            
        # 2. Status change (e.g. APPROVED or REJECTED/UNDER_REVIEW)
        elif not created and old_status != instance.status:
            if instance.status == 'PAID':
                # 3. Paid
                ORREmailService.send_consultant_payout(
                    recipient_email=recipient_email,
                    invoice_id=instance.invoice_number,
                    amount_paid=f"{instance.amount}",
                    payout_date=instance.updated_at.strftime("%Y-%m-%d") if hasattr(instance, 'updated_at') else "today",
                    dashboard_url=f"https://consultant.orr.solutions/invoices/{instance.invoice_number}"
                )
            else:
                ORREmailService.send_consultant_invoice_status(
                    recipient_email=recipient_email,
                    invoice_id=instance.invoice_number,
                    new_status=instance.status,
                    admin_comments=instance.reviewer_notes or "Status updated by admin.",
                    status_url=f"https://consultant.orr.solutions/invoices/{instance.invoice_number}"
                )
                
    except Exception as e:
        logger.error(f"Failed to send invoice notification: {e}")

