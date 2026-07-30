from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from admin_portal.models import AuditLog
from django.contrib.contenttypes.models import ContentType
import inspect
import json

from .thread_local_middleware import get_current_user

@receiver(post_save)
def audit_log_post_save(sender, instance, created, **kwargs):
    # Only track models that inherit from common.models.Audit
    if not hasattr(instance, 'created_at') or not hasattr(instance, 'updated_at'):
        return
        
    # Exclude the AuditLog and SecurityAuditLog models themselves to prevent recursion
    if sender.__name__ in ['AuditLog', 'SecurityAuditLog', 'Session', 'LogEntry', 'StripeEvent', 'SystemConfig']:
        return

    action = 'create' if created else 'update'
    
    try:
        model_name = sender.__name__
        object_id = str(instance.pk)
        description = f"{action.capitalize()} {model_name} {object_id}"
        
        # Only log if we can identify the model cleanly
        AuditLog.objects.create(
            action=action,
            model_name=model_name,
            object_id=object_id,
            description=description,
            user=get_current_user() # Will be None unless we use thread locals
        )
    except Exception as e:
        pass

@receiver(post_delete)
def audit_log_post_delete(sender, instance, **kwargs):
    if not hasattr(instance, 'created_at') or not hasattr(instance, 'updated_at'):
        return
        
    if sender.__name__ in ['AuditLog', 'SecurityAuditLog', 'Session', 'LogEntry', 'StripeEvent']:
        return

    try:
        AuditLog.objects.create(
            action='delete',
            model_name=sender.__name__,
            object_id=str(instance.pk),
            description=f"Deleted {sender.__name__} {instance.pk}",
            user=get_current_user()
        )
    except Exception:
        pass
