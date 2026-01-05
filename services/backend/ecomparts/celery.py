"""
Celery configuration for ECOMPARTS project.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecomparts.settings')

app = Celery('ecomparts')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')


# Scheduled tasks (Celery Beat)
app.conf.beat_schedule = {
    'sync-odoo-products-every-hour': {
        'task': 'apps.sync.tasks.sync_products_from_odoo',
        'schedule': crontab(minute=0),  # Every hour
    },
    'sync-odoo-stock-every-15min': {
        'task': 'apps.sync.tasks.sync_stock_from_odoo',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}
