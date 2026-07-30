import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")

app.config_from_object("django.conf:settings", namespace="CELERY")


app.autodiscover_tasks()
app.conf.broker_connection_retry_on_startup = True
app.conf.beat_schedule = {
    'send_upcoming_invoice_reminders_daily': {
        'task': 'payment.tasks.send_upcoming_invoice_reminders',
        'schedule': 86400.0, # Run once a day (in seconds)
    },
    'backup_database_daily': {
        'task': 'common.tasks.backup_database',
        'schedule': 86400.0, # Run once a day
    },
    'backup_workspace_weekly': {
        'task': 'common.tasks.backup_workspace',
        'schedule': 604800.0, # Run once a week
    },
}
