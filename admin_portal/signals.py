from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
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


@receiver(post_save, sender=Meeting)
def meeting_created_notification(sender, instance, created, **kwargs):
    """Create notification when new meeting is requested"""
    if created:
        # Notify all admin users about new meeting request
        admin_users = User.objects.filter(
            admin_profile__role__can_manage_meetings=True, admin_profile__is_active=True
        )

        for admin_user in admin_users:
            SystemNotification.objects.create(
                notification_type="meeting_requested",
                title="New Meeting Request",
                message=f"New meeting requested by {instance.client.user.get_full_name()}",
                recipient=admin_user,
                related_meeting=instance,
                related_client=instance.client,
            )


@receiver(post_save, sender=Content)
def content_published_notification(sender, instance, created, **kwargs):
    """Create audit log when content is published"""
    if not created and instance.status == "published" and instance.published_at:
        AuditLog.objects.create(
            action="publish",
            model_name="Content",
            object_id=str(instance.pk),
            description=f"Content published: {instance.title}",
        )


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
