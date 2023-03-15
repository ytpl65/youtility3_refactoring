# mysite/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')

app = Celery('intelliwiz_config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "ppm_schedule":{
        'task':'schedule_ppm_jobs',
        'schedule': crontab(hour=0, minute=0),
    },
    "reminder_emails":{
        'task':'send_reminder_emails',
        'schedule': crontab(hour=0, minute=0),
    },
    "auto_close":{
        'task':'auto_close_jobs',
        'schedule': crontab(hour=0, minute=0),
    },
    "ticket_escalation_every_30min":{
        'task':'ticket_escalation',
        'schedule':crontab(minute='*/30')
    },
    "send_ticket_email":{
        'task':'send_ticket_email',
        'schedule':crontab(minute='*/30')
    }

}

