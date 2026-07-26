from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_task_deadline_reminders():
    """Periodic task to send reminders for PM tasks due in exactly 24 hours"""
    from pm.models import PMTask
    
    now = timezone.now()
    # Find tasks due between 23 and 25 hours from now
    target_time_start = now + timedelta(hours=23)
    target_time_end = now + timedelta(hours=25)

    # Note: due_date is a DateField, not DateTimeField. So we should compare dates.
    # We want tasks due tomorrow.
    target_date = (now + timedelta(days=1)).date()

    tasks = PMTask.objects.filter(
        status__in=['not_started', 'awaiting_assignment', 'awaiting_client_input', 'in_progress', 'blocked'],
        due_date=target_date
    )

    for task in tasks:
        try:
            from admin_portal.orr_email_service import ORREmailService
            
            # Send to assignee if exists
            if hasattr(task, 'assigned_to') and task.assigned_to and task.assigned_to.email:
                ORREmailService.send_task_reminder(
                    recipient_email=task.assigned_to.email,
                    task_name=task.title,
                    due_date=task.due_date.strftime("%Y-%m-%d") if task.due_date else "Tomorrow",
                    task_url=f"https://projectmanager.orr.solutions/tasks/{task.task_id}"
                )
        except Exception as e:
            logger.error(f"Failed to send task deadline reminder for task {task.task_id}: {e}")
