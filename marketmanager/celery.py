from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketmanager.settings')

app = Celery('marketmanager')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Beat scheduler
app.conf.beat_schedule = {
    'clear_task_results': {
        'task': 'api.tasks.clear_task_results',
        'schedule': crontab(minute=0, hour=10, day_of_week=0),
    },
    'clear_stale_markets': {
        'task': 'api.tasks.clear_stale_markets',
        'schedule': crontab(minute=0, hour=10),
    }
}
