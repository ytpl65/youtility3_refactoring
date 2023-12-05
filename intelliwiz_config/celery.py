# mysite/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intelliwiz_config.settings')

app = Celery('intelliwiz_config')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object(settings, namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
app.conf.CELERYD_HIJACK_ROOT_LOGGER = False



app.conf.beat_schedule = {
    "ppm_schedule_at_minute_3_past_hour_3_and_16":{
        'task':'schedule_ppm_jobs',
        'schedule': crontab(minute='3', hour='3,16'),#03 3,16 * * *
    },
    "reminder_emails_at_minute_10_past_every_8th_hour.":{
        'task':'send_reminder_emails',
        'schedule': crontab(hour='*/8', minute='10'),
    },
    "auto_close_at_every_30_minute":{
        'task':'auto_close_jobs',
        'schedule': crontab(minute='*/30'),
    },
    "ticket_escalation_every_30min":{
        'task':'ticket_escalation',
        'schedule':crontab(minute='*/30')
    },
    "create_job_at_minute_27_past_every_8th_hour.":{
        'task':'create_job()',
        'schedule':crontab(minute='27', hour='*/8') #27 */8 * * *
    },
    "upload-old-files-to-cloud-storage":{
        'task':'upload-old-files-to-cloud-storage',
        'schedule':crontab(minute=0, hour=0, day_of_week='monday')
    }

}