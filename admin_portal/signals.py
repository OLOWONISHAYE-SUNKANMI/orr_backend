from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.apps import apps
import logging

from .models import (
    AdminProfile,
    AdminRole,
    AuditLog,
    Content,
    Meeting,
    SystemNotification,
    Ticket,
    TicketMessage,
    WalletTransaction,
    ApprovalQueue,
)
from .auto_reply_service import AutoReplyService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Ticket)
def ticket_created_notification(sender, instance, created, **kwargs):
    """Create notification and auto-reply when new ticket is created"""
    if created and not str(instance.ticket_id).startswith('tmp-'):
        # Send automatic reply to client asynchronously
        import threading
        threading.Thread(target=AutoReplyService.send_initial_auto_reply, args=(instance,)).start()
        
        # Notify assigned admin if any
        if instance.assigned_to:
            SystemNotification.objects.create(
                notification_type="ticket_created",
                title=f"New Ticket: {instance.ticket_id}",
                message=f"New ticket created: {instance.subject}",
                recipient=instance.assigned_to,
                related_ticket=instance,
                related_client=instance.client,
            )

        # Create audit log
        AuditLog.objects.create(
            action="create",
            model_name="Ticket",
            object_id=str(instance.pk),
            description=f"Ticket created: {instance.ticket_id} - {instance.subject}",
        )


@receiver(pre_save, sender=Meeting)
def capture_old_meeting_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Meeting.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Meeting.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Meeting)
def meeting_notification_handler(sender, instance, created, **kwargs):
    """Create notification when new meeting is requested and send emails on status change"""
    old_status = getattr(instance, '_old_status', None)

    if created:
        # Notify all admin users about new meeting request
        admin_users = User.objects.filter(
            admin_profile__role__can_manage_meetings=True, admin_profile__is_active=True
        )

        admin_emails = []
        for admin_user in admin_users:
            SystemNotification.objects.create(
                notification_type="meeting_requested",
                title="New Meeting Request",
                message=f"New meeting requested by {instance.client.user.get_full_name()}",
                recipient=admin_user,
                related_meeting=instance,
                related_client=instance.client,
            )
            if admin_user.email:
                admin_emails.append(admin_user.email)
                
        if admin_emails:
            try:
                from .orr_email_service import ORREmailService
                ORREmailService.send_admin_notification(
                    recipient_emails=admin_emails,
                    submitter_name=instance.client.user.get_full_name(),
                    submitter_email=instance.client.user.email,
                    form_name="Meeting Request",
                    reference_id=f"MTG-{instance.id}",
                    admin_link="https://projectmanager.orr.solutions/meetings"
                )
            except Exception as e:
                logger.error(f"Failed to send admin notification for meeting: {e}")
            
    # Send Email Notifications for Meeting Status
    try:
        from .orr_email_service import ORREmailService
        recipient_email = instance.client.user.email
        meeting_time = instance.confirmed_datetime.strftime("%Y-%m-%d %H:%M UTC") if instance.confirmed_datetime else instance.requested_datetime.strftime("%Y-%m-%d %H:%M UTC")
        
        if instance.status == 'confirmed' and (created or old_status != 'confirmed'):
            ORREmailService.send_meeting_scheduled(
                recipient_email=recipient_email,
                meeting_topic=instance.get_meeting_type_display(),
                meeting_time=meeting_time,
                meeting_link=instance.meeting_link or "Link will be provided",
                calendar_url=f"https://orr.solutions/meetings/{instance.id}"
            )
        elif instance.status == 'rescheduled' and old_status != 'rescheduled':
            ORREmailService.send_meeting_rescheduled(
                recipient_email=recipient_email,
                meeting_topic=instance.get_meeting_type_display(),
                new_meeting_time=meeting_time,
                meeting_link=instance.meeting_link or "Link will be provided"
            )
        elif instance.status in ['cancelled', 'declined'] and old_status not in ['cancelled', 'declined']:
            ORREmailService.send_meeting_cancelled(
                recipient_email=recipient_email,
                meeting_topic=instance.get_meeting_type_display(),
                cancellation_reason="Meeting was cancelled or declined by admin.",
                reschedule_url="https://orr.solutions/meetings/request"
            )
    except Exception as e:
        logger.error(f"Failed to send meeting notification email: {e}")


@receiver(pre_save, sender=Content)
def capture_old_content_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Content.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Content.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Content)
def content_published_notification(sender, instance, created, **kwargs):
    """Create audit log and send announcements when content is published"""
    old_status = getattr(instance, '_old_status', None)
    
    if not created and instance.status == "published" and old_status != "published":
        # Create audit log
        AuditLog.objects.create(
            action="publish",
            model_name="Content",
            object_id=str(instance.pk),
            description=f"Content published: {instance.title}",
        )

        # Broadcast Feature Announcement if it's an announcement
        if instance.content_type == "announcement":
            try:
                from .orr_email_service import ORREmailService
                # Send to all active users across different portals (simplified for integration: sending to admins and clients here)
                from django.contrib.auth.models import User
                users = User.objects.filter(is_active=True).exclude(email="")
                
                for user in users:
                    ORREmailService.send_feature_announcement(
                        recipient_email=user.email,
                        feature_name=instance.title,
                        feature_brief=instance.excerpt or "Check out our latest update!",
                        feature_screenshot_url="https://orr.solutions/images/feature-placeholder.jpg",
                        try_now_url="https://orr.solutions/dashboard",
                        changelog_url="https://orr.solutions/changelog"
                    )
            except Exception as e:
                logger.error(f"Failed to send feature announcement emails: {e}")


@receiver(post_save, sender=User)
def create_admin_profile(sender, instance, created, **kwargs):
    """Create admin profile for staff users"""
    if created and instance.is_staff:
        # Get or create default admin role
        admin_role, _ = AdminRole.objects.get_or_create(
            name="admin",
            defaults={
                "description": "Default admin role",
                "can_view_all_clients": True,
                "can_manage_tickets": True,
                "can_manage_meetings": True,
                "can_create_content": True,
                "can_view_analytics": True,
            },
        )

        AdminProfile.objects.get_or_create(
            user=instance, defaults={"role": admin_role, "is_active": True}
        )


import threading

@receiver(post_save, sender=TicketMessage)
def ticket_message_auto_reply(sender, instance, created, **kwargs):
    """Handle auto-reply and notifications for ticket messages"""
    if created and not instance.is_internal:
        from .email_service import MessageEmailService
        from .tasks import check_message_escalation_task
        
        # If message is from a client
        if hasattr(instance.sender, 'client_profile'):
            # 1. Notify admin of new client message asynchronously
            threading.Thread(target=MessageEmailService.send_admin_new_message_email, args=(instance.ticket, instance)).start()
            
            # 2. Schedule escalation check (e.g., 4 hours = 240 minutes)
            check_message_escalation_task.apply_async(
                args=[instance.ticket.id, instance.id],
                countdown=4 * 60 * 60  # 4 hours
            )
            
        
        # If message is from an admin
        elif instance.sender.is_staff:
            # 1. Notify client of admin response
            MessageEmailService.send_client_admin_response_email(instance.ticket, instance)
            
            # 2. Reset escalation status if it was escalated
            if instance.ticket.is_escalated:
                instance.ticket.is_escalated = False
                instance.ticket.save(update_fields=['is_escalated'])

        # WhatsApp notification to admin (existing logic preserved)
        if instance.sender.username != 'system_auto_reply':
            try:
                from .tasks import send_admin_whatsapp_notification
                send_admin_whatsapp_notification.apply_async(
                    args=[instance.ticket.id],
                    countdown=10
                )
            except ImportError:
                logger.info(f"WhatsApp notification would be sent for ticket {instance.ticket.ticket_id}")


@receiver(post_delete, sender=Content)
def content_deleted_audit(sender, instance, **kwargs):
    """Create audit log when content is deleted"""
    AuditLog.objects.create(
        action="delete",
        model_name="Content",
        object_id=str(instance.pk),
        description=f"Content deleted: {instance.title}",
    )


@receiver(post_save, sender=WalletTransaction)
def sync_wallet_balance(sender, instance, created, **kwargs):
    """Sync balance to Wallet model whenever a transaction is recorded"""
    if created:
        Wallet = apps.get_model('client', 'Wallet')
        client_user = instance.client.user
        
        # Get or create the wallet for the user
        wallet, _ = Wallet.objects.get_or_create(owner=client_user)
        
        # Update the wallet balance with the new after-transaction balance
        wallet.balance = instance.balance_after
        wallet.save(update_fields=['balance'])

        # Create audit log for the financial transaction
        AuditLog.objects.create(
            action="update",
            model_name="Wallet",
            object_id=str(wallet.pk),
            description=f"Wallet balance adjusted to {wallet.balance} via {instance.transaction_type} for {client_user.email}",
        )

        # Send wallet top-up email notification (21-wallet-topup.html)
        if instance.transaction_type in ('deposit', 'credit', 'topup', 'top_up'):
            try:
                from .orr_email_service import ORREmailService
                ORREmailService.send_wallet_topup(
                    recipient_email=client_user.email,
                    transaction_id=str(instance.id),
                    added_amount=str(instance.amount),
                    currency_symbol='$',
                    new_balance=str(instance.balance_after),
                    wallet_url='https://orr.solutions/wallet',
                )
            except Exception as e:
                logger.error(f"Failed to send wallet top-up email: {e}")

@receiver(pre_save, sender=ApprovalQueue)
def capture_old_approval_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = ApprovalQueue.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except ApprovalQueue.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=ApprovalQueue)
def handle_approval_queue_notifications(sender, instance, created, **kwargs):
    old_status = getattr(instance, '_old_status', None)
    
    try:
        from .orr_email_service import ORREmailService
        
        # In a real app, you might look up the requester's email.
        # Assuming requested_by holds a username or ID that we can query.
        requester_user = User.objects.filter(username=instance.requested_by).first()
        requester_email = requester_user.email if requester_user else None
        
        if created:
            # Send template 36 to super admins
            super_admins = User.objects.filter(admin_profile__role__name='super_admin', is_active=True)
            for sa in super_admins:
                ORREmailService.send_admin_approval_request(
                    recipient_email=sa.email,
                    requester_name=instance.requested_by_name or instance.requested_by,
                    action_type=instance.action_type,
                    request_details="Please review the pending action in the approval queue.",
                    review_url=f"https://orr.solutions/admin/approvals/{instance.id}"
                )
        elif old_status != instance.status and instance.status in ['APPROVED', 'REJECTED']:
            # Send template 37 to requester
            if requester_email:
                ORREmailService.send_admin_approval_status(
                    recipient_email=requester_email,
                    action_type=instance.action_type,
                    approval_status=instance.status,
                    reviewer_comments=instance.rejection_reason or "No comments provided."
                )
    except Exception as e:
        logger.error(f"Failed to send approval queue emails: {e}")

@receiver(pre_save, sender=AdminProfile)
def capture_old_admin_role(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = AdminProfile.objects.get(pk=instance.pk)
            instance._old_role_id = old.role_id
        except AdminProfile.DoesNotExist:
            instance._old_role_id = None
    else:
        instance._old_role_id = None

@receiver(post_save, sender=AdminProfile)
def handle_admin_role_change(sender, instance, created, **kwargs):
    old_role_id = getattr(instance, '_old_role_id', None)
    if not created and old_role_id != instance.role_id and instance.role:
        try:
            from .orr_email_service import ORREmailService
            ORREmailService.send_role_change_notification(
                recipient_email=instance.user.email,
                new_role=instance.role.get_name_display(),
                permissions_summary=f"Role changed to {instance.role.name}",
                portal_url="https://orr.solutions/admin"
            )
        except Exception as e:
            logger.error(f"Failed to send role change email: {e}")
