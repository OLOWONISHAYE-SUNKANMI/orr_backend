from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
import threading

from admin_portal.models import AdminProfile, Meeting, Ticket
from notification.utils import notify_user

from .models import Activity

User = get_user_model()
from admin_portal.models import Client
from client.tasks.activities import invalidate_recommendations_cache

from .models import Profile




@receiver(post_save, sender=Ticket)
def notify_admins_on_ticket_created(sender, instance, created, **kwargs):
    if not created or str(instance.ticket_id).startswith('tmp-'):
        return

    ticket = instance

    admin_profiles = AdminProfile.objects.exclude(role__name="content_editor")
    admin_users = [profile.user for profile in admin_profiles if profile.user.is_active]

    for admin in admin_users:
        notify_user(
            admin,
            "New Support Ticket",
            f"New ticket {ticket.ticket_id} created",
            ["inapp", "email"],
            {
                "type": "ticket",
                "template": "support/ticket_created_admin.html",
                "context": {
                    "ticket_id": ticket.ticket_id,
                    "subject": ticket.subject,
                    "priority": ticket.priority,
                    "status": ticket.status,
                    "source": ticket.source,
                    "client_name": (
                        ticket.client.user.first_name
                        if ticket.client and ticket.client.user
                        else ticket.contact_name
                    ),
                    "client_email": (
                        ticket.client.user.email
                        if ticket.client and ticket.client.user
                        else ticket.contact_email
                    ),
                    "description": ticket.description,
                    "created_at": ticket.created_at,
                },
            },
        )




@receiver(post_save)
def auto_create_activity(sender, instance, created, **kwargs):
    """Auto-create activities for key models"""
    if sender == Meeting and created:
        user = getattr(instance, "requester", None)
        if not user:
            return
        Activity.objects.create(
            user=user,
            action_type="Meeting Activity",
            title="Upcoming meeting scheduled",
            message="Meeting on {instance.requested_datetime}",
        )
        invalidate_recommendations_cache.delay(user.id)


@receiver(post_save, sender=User)
def create_profiles(sender, instance, created, **kwargs):
    """Create client and profile for new users (only for self-registration)"""
    if created:
        # Skip users who already have an admin profile
        if AdminProfile.objects.filter(user=instance).exists():
            return
            
        # Skip if user is staff or superuser (admin-created)
        if instance.is_staff or instance.is_superuser:
            return
            
        # Skip if this is being created by admin portal (check for specific marker)
        # We'll use a thread-local variable to mark admin-created users
        import threading
        if hasattr(threading.current_thread(), 'skip_auto_client_creation'):
            return

        # Create a general Profile if it doesn't exist
        if not Profile.objects.filter(user=instance).exists():
            Profile.objects.create(user=instance)

        # Create Client if it doesn't exist (only for self-registered users)
        if not Client.objects.filter(user=instance).exists():
            # Provide defaults for required fields
            Client.objects.create(
                user=instance,
                company="N/A",  # or get from registration data
                primary_pillar="strategic",  # default
            )


# ═══════════════════════════════════════════════════════════
# CLIENT REQUEST SIGNALS
# ═══════════════════════════════════════════════════════════

from .models import ClientRequest


@receiver(post_save, sender=ClientRequest)
def handle_client_request_post_save(sender, instance, created, **kwargs):
    """
    Auto-generate request_id on creation.
    Notify admins when a request is submitted.
    Create Activity records for the client.
    """
    if created:
        # Auto-generate request_id if not set
        if not instance.request_id:
            instance.request_id = f"ORR-REQ-{instance.pk:06d}"
            ClientRequest.objects.filter(pk=instance.pk).update(
                request_id=instance.request_id
            )

    # Notify admins when status changes to 'submitted'
    update_fields = kwargs.get('update_fields')
    if update_fields and 'status' in update_fields and instance.status == 'submitted':
        # Create activity for the client
        try:
            Activity.objects.create(
                user=instance.submitted_by,
                activity_type='USER',
                title='Request Submitted',
                message=f'Your request "{instance.request_title}" ({instance.request_id}) has been submitted for review.',
                metadata={
                    'request_id': instance.request_id,
                    'request_pk': instance.pk,
                }
            )
        except Exception:
            pass

        # Notify admin users
        try:
            admin_profiles = AdminProfile.objects.exclude(role__name="content_editor")
            admin_users = [p.user for p in admin_profiles if p.user.is_active]
            for admin in admin_users:
                notify_user(
                    admin,
                    "New Client Request",
                    f"New request {instance.request_id}: {instance.request_title}",
                    ["inapp"],
                    {
                        "type": "client_request",
                        "context": {
                            "request_id": instance.request_id,
                            "request_title": instance.request_title,
                            "client_name": instance.client.company if instance.client else "Unknown",
                            "urgency": instance.urgency,
                            "sensitivity": instance.sensitivity_level,
                        },
                    },
                )
        except Exception:
            pass

