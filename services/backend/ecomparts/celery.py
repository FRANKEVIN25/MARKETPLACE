"""
Celery configuration for ECOMPARTS project.
"""
import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

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

# ── Periodo de recálculo de scores de talleres ────────────────────────────────
# Cambia el valor de 'hour' para ajustar la frecuencia.
# Ejemplos: crontab(hour='*/12') → cada 12h   |   crontab(hour='*/6') → cada 6h
WORKSHOP_SCORE_RECALCULATE_SCHEDULE = crontab(hour='*/12', minute=0)
SYNC_STOCK_INTERVAL_MINUTES = max(1, int(getattr(settings, 'SYNC_STOCK_INTERVAL_MINUTES', 60)))
SYNC_CATALOG_SCHEDULE_HOUR = int(getattr(settings, 'SYNC_CATALOG_SCHEDULE_HOUR', 1))
SYNC_CATALOG_SCHEDULE_MINUTE = int(getattr(settings, 'SYNC_CATALOG_SCHEDULE_MINUTE', 0))
SYNC_COMPATIBILITY_SCHEDULE_HOUR = int(getattr(settings, 'SYNC_COMPATIBILITY_SCHEDULE_HOUR', 2))
SYNC_COMPATIBILITY_SCHEDULE_MINUTE = int(getattr(settings, 'SYNC_COMPATIBILITY_SCHEDULE_MINUTE', 10))

app.conf.beat_schedule = {
    **getattr(app.conf, 'beat_schedule', {}),
    # Snapshot de catálogo e imágenes en ventana de baja carga.
    'sync-odoo-products-nightly': {
        'task': 'apps.sync.tasks.sync_all_active_providers',
        'schedule': crontab(
            hour=SYNC_CATALOG_SCHEDULE_HOUR,
            minute=SYNC_CATALOG_SCHEDULE_MINUTE,
        ),
    },
    # Compatibilidades separadas y nocturnas para desacoplar carga y reintentos.
    'sync-odoo-compatibility-nightly': {
        'task': 'apps.sync.tasks.sync_all_compatibility',
        'schedule': crontab(
            hour=SYNC_COMPATIBILITY_SCHEDULE_HOUR,
            minute=SYNC_COMPATIBILITY_SCHEDULE_MINUTE,
        ),
    },
    # Sincronización solo de stock con frecuencia configurable.
    'sync-odoo-stock-interval': {
        'task': 'apps.sync.tasks.sync_all_stock',
        'schedule': timedelta(minutes=SYNC_STOCK_INTERVAL_MINUTES),
    },
    # Recálculo de scores de talleres (configurable via WORKSHOP_SCORE_RECALCULATE_SCHEDULE)
    'recalculate-workshop-scores': {
        'task': 'apps.services.tasks.recalculate_workshop_scores',
        'schedule': WORKSHOP_SCORE_RECALCULATE_SCHEDULE,
    },
}
