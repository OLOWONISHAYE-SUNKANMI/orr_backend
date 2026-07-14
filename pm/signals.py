"""
PM Signals
- Auto-generate sequential IDs (ORR-PROJ-000001, ORR-TASK-000001, etc.)
- Track version history on field changes
- Send email notifications on status transitions
"""

import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Auto ID Generation
# ─────────────────────────────────────────────

def _generate_sequential_id(model_class, prefix, field_name='project_id'):
    """Generate a sequential ID like ORR-PROJ-000001."""
    last_obj = model_class.objects.order_by('-id').first()
    if last_obj:
        last_id = getattr(last_obj, field_name, '')
        if last_id and '-' in last_id:
            try:
                num = int(last_id.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = last_obj.id + 1 if last_obj.id else 1
    else:
        num = 1
    return f"{prefix}{num:06d}"


@receiver(pre_save, sender='pm.PMProject')
def generate_project_id(sender, instance, **kwargs):
    """Auto-generate ORR-PROJ-000001 on project creation."""
    if not instance.project_id:
        from .models import PMProject
        instance.project_id = _generate_sequential_id(
            PMProject, 'ORR-PROJ-', 'project_id'
        )


@receiver(pre_save, sender='pm.PMTask')
def generate_task_id(sender, instance, **kwargs):
    """Auto-generate ORR-TASK-000001 on task creation."""
    if not instance.task_id:
        from .models import PMTask
        instance.task_id = _generate_sequential_id(
            PMTask, 'ORR-TASK-', 'task_id'
        )


@receiver(pre_save, sender='pm.PMAssignment')
def generate_assignment_id(sender, instance, **kwargs):
    """Auto-generate ORR-ASG-000001 on assignment creation."""
    if not instance.assignment_id:
        from .models import PMAssignment
        instance.assignment_id = _generate_sequential_id(
            PMAssignment, 'ORR-ASG-', 'assignment_id'
        )


@receiver(pre_save, sender='pm.PMOpportunity')
def generate_opportunity_id(sender, instance, **kwargs):
    """Auto-generate ORR-OPP-000001 on opportunity creation."""
    if not instance.opportunity_id:
        from .models import PMOpportunity
        instance.opportunity_id = _generate_sequential_id(
            PMOpportunity, 'ORR-OPP-', 'opportunity_id'
        )


# ─────────────────────────────────────────────
# Version History Tracking
# ─────────────────────────────────────────────

# Fields to track for version history
PROJECT_TRACKED_FIELDS = [
    'title', 'status', 'pm_approved_summary', 'consultant_facing_summary',
    'client_objective', 'main_problem', 'proposed_scope', 'out_of_scope',
    'expected_deliverable', 'confidentiality_level', 'urgency',
    'target_deadline', 'estimated_hours', 'estimated_budget',
    'assigned_pm_id', 'sourcing_status',
]

TASK_TRACKED_FIELDS = [
    'title', 'description', 'status', 'assigned_to_id', 'due_date',
    'priority', 'review_outcome', 'document_visibility',
]


@receiver(pre_save, sender='pm.PMProject')
def capture_project_old_values(sender, instance, **kwargs):
    """Capture old field values before save for version tracking."""
    if instance.pk:
        try:
            from .models import PMProject
            old = PMProject.objects.get(pk=instance.pk)
            instance._old_values = {
                field: str(getattr(old, field, ''))
                for field in PROJECT_TRACKED_FIELDS
            }
        except sender.DoesNotExist:
            instance._old_values = {}
    else:
        instance._old_values = {}


@receiver(post_save, sender='pm.PMProject')
def create_project_versions(sender, instance, created, **kwargs):
    """Create version entries for changed project fields."""
    if created:
        return  # No version tracking on creation

    old_values = getattr(instance, '_old_values', {})
    if not old_values:
        return

    from .models import PMProjectVersion
    last_version = PMProjectVersion.objects.filter(
        project=instance
    ).order_by('-version_number').first()
    version_num = (last_version.version_number if last_version else 0) + 1

    for field in PROJECT_TRACKED_FIELDS:
        old_val = old_values.get(field, '')
        new_val = str(getattr(instance, field, ''))
        if old_val != new_val:
            PMProjectVersion.objects.create(
                project=instance,
                version_number=version_num,
                field_changed=field,
                old_value=old_val,
                new_value=new_val,
            )
            version_num += 1


@receiver(pre_save, sender='pm.PMTask')
def capture_task_old_values(sender, instance, **kwargs):
    """Capture old field values before save for version tracking."""
    if instance.pk:
        try:
            from .models import PMTask
            old = PMTask.objects.get(pk=instance.pk)
            instance._old_values = {
                field: str(getattr(old, field, ''))
                for field in TASK_TRACKED_FIELDS
            }
        except sender.DoesNotExist:
            instance._old_values = {}
    else:
        instance._old_values = {}


@receiver(post_save, sender='pm.PMTask')
def create_task_versions(sender, instance, created, **kwargs):
    """Create version entries for changed task fields."""
    if created:
        return

    old_values = getattr(instance, '_old_values', {})
    if not old_values:
        return

    from .models import PMTaskVersion
    last_version = PMTaskVersion.objects.filter(
        task=instance
    ).order_by('-version_number').first()
    version_num = (last_version.version_number if last_version else 0) + 1

    for field in TASK_TRACKED_FIELDS:
        old_val = old_values.get(field, '')
        new_val = str(getattr(instance, field, ''))
        if old_val != new_val:
            PMTaskVersion.objects.create(
                task=instance,
                version_number=version_num,
                field_changed=field,
                old_value=old_val,
                new_value=new_val,
            )
            version_num += 1


# ─────────────────────────────────────────────
# Auto-complete task date on completion
# ─────────────────────────────────────────────

@receiver(pre_save, sender='pm.PMTask')
def auto_set_completion_date(sender, instance, **kwargs):
    """Set completion_date when status becomes 'completed'."""
    if instance.pk:
        try:
            from .models import PMTask
            old = PMTask.objects.get(pk=instance.pk)
            if old.status != 'completed' and instance.status == 'completed':
                instance.completion_date = timezone.now()
        except sender.DoesNotExist:
            pass


# ─────────────────────────────────────────────
# Email Notifications
# ─────────────────────────────────────────────

@receiver(post_save, sender='pm.PMProject')
def notify_on_project_status_change(sender, instance, created, **kwargs):
    """Send notifications on project status transitions."""
    if created:
        return

    old_values = getattr(instance, '_old_values', {})
    old_status = old_values.get('status', '')
    new_status = instance.status

    if old_status == new_status:
        return

    try:
        from admin_portal.orr_email_service import ORREmailService
        from admin_portal.models import SystemNotification

        # Project submitted for admin review
        if new_status == 'pending_admin_review':
            # Notify all admins
            from django.contrib.auth.models import User
            admins = User.objects.filter(is_staff=True, is_active=True)
            for admin in admins:
                SystemNotification.objects.create(
                    notification_type='project_submitted',
                    title=f'New Project: {instance.project_id}',
                    message=f'Project "{instance.title}" submitted for review by PM.',
                    recipient=admin,
                )

        # Admin requests PM clarification
        elif new_status == 'needs_pm_clarification' and instance.assigned_pm:
            SystemNotification.objects.create(
                notification_type='project_clarify',
                title=f'Clarification Needed: {instance.project_id}',
                message=f'Admin has requested clarification on project "{instance.title}".',
                recipient=instance.assigned_pm,
            )

        # Project approved for sourcing
        elif new_status == 'approved_for_sourcing' and instance.assigned_pm:
            SystemNotification.objects.create(
                notification_type='project_approved',
                title=f'Project Approved: {instance.project_id}',
                message=f'Project "{instance.title}" approved for consultant sourcing.',
                recipient=instance.assigned_pm,
            )

        # Project completed
        elif new_status == 'completed':
            # Notify PM
            if instance.assigned_pm:
                SystemNotification.objects.create(
                    notification_type='project_completed',
                    title=f'Project Completed: {instance.project_id}',
                    message=f'Project "{instance.title}" has been successfully completed.',
                    recipient=instance.assigned_pm,
                )
            # Notify Client
            if instance.client and instance.client.user:
                SystemNotification.objects.create(
                    notification_type='project_completed',
                    title=f'Project Completed: {instance.project_id}',
                    message=f'Your project "{instance.title}" is now completed.',
                    recipient=instance.client.user,
                )
            # Notify Consultants linked
            for assignment in instance.assignments.filter(status__in=['active', 'completed', 'access_activated']):
                if assignment.consultant and assignment.consultant.user:
                    SystemNotification.objects.create(
                        notification_type='project_completed',
                        title=f'Project Completed: {instance.project_id}',
                        message=f'The project "{instance.title}" you were assigned to has been completed.',
                        recipient=assignment.consultant.user,
                    )
            # Notify Admins
            from django.contrib.auth.models import User
            admins = User.objects.filter(is_staff=True, is_active=True)
            for admin in admins:
                SystemNotification.objects.create(
                    notification_type='project_completed',
                    title=f'Project Completed: {instance.project_id}',
                    message=f'Project "{instance.title}" has been completed.',
                    recipient=admin,
                )

    except Exception as e:
        logger.error(f"Failed to send PM notification: {e}")


@receiver(post_save, sender='pm.PMAssignment')
def notify_on_assignment_invitation(sender, instance, created, **kwargs):
    """Send email notification when assignment invitation is sent."""
    if instance.status == 'invitation_sent' and instance.invitation_sent_at:
        try:
            from admin_portal.orr_email_service import ORREmailService
            consultant_email = instance.consultant.user.email
            consultant_name = instance.consultant.user.get_full_name()

            ORREmailService.send_task_assignment(
                recipient_email=consultant_email,
                consultant_name=consultant_name,
                task_name=f"Assignment: {instance.project.title}",
                task_description=instance.assignment_scope,
                project_name=instance.project.title,
                priority_level=instance.priority.title(),
                due_date=str(instance.assignment_deadline or 'TBD'),
                task_url='https://orr.solutions/consultant/assignments',
            )
        except Exception as e:
            logger.error(f"Failed to send assignment invitation email: {e}")
