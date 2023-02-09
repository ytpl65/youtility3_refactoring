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
        'schedule': crontab(hour=5, minute=0),
    },
    "reminder_emails":{
        'task':'send_reminder_emails',
        'schedule': crontab(hour=5, minute=0),
    },
    "hi_to_navee":{
        'task':"hello_naveen",
        'schedule': crontab(minute="*"),
    }
}

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(hour=7, minute=30, day_of_week=1),
        'tasks.print_hii'
    )
    sender.add_periodic_task(
        crontab(hour=12, minute=0, day_of_week=1),
        'tasks.print_hii'
    )
