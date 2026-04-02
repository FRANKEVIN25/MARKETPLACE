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

# Import tasks explicitly to ensure they're registered
app.autodiscover_tasks(['apps.orders'])


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery"""
    print(f'Request: {self.request!r}')


# Scheduled tasks (Celery Beat)
# Importante: actualizar el schedule cargado desde Django settings, no reemplazarlo.
app.conf.beat_schedule = {
    **getattr(app.conf, 'beat_schedule', {}),
    # Sincronización completa (productos + categorías + almacenes + stock) cada hora
    'sync-odoo-products-every-hour': {
        'task': 'apps.sync.tasks.sync_all_active_providers',
        'schedule': crontab(minute=0),  # Every hour
    },
    # Sincronización solo de stock cada 15 min (más ligera)
    'sync-odoo-stock-every-15min': {
        'task': 'apps.sync.tasks.sync_all_stock',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}
