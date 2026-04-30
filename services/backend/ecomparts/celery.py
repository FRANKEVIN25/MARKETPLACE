"""
Celery configuration for ECOMPARTS project.
"""
import os

from celery import Celery

from ecomparts.beat_schedule import get_periodic_schedule

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecomparts.settings')

app = Celery('ecomparts')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Import tasks explicitly to ensure they're registered
app.autodiscover_tasks(['apps.orders'])


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')


# Scheduled tasks (Celery Beat)
# Importante: actualizar el schedule cargado desde Django settings, no reemplazarlo.
app.conf.update(beat_schedule=get_periodic_schedule(getattr(app.conf, 'beat_schedule', {})))
