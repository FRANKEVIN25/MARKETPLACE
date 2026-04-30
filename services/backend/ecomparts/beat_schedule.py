from datetime import timedelta

from celery.schedules import crontab
from django.conf import settings


def get_periodic_schedule(base_schedule=None):
    base_schedule = dict(base_schedule or {})

    workshop_score_recalculate_schedule = crontab(hour='*/12', minute=0)
    sync_stock_interval_minutes = max(1, int(getattr(settings, 'SYNC_STOCK_INTERVAL_MINUTES', 60)))
    sync_catalog_schedule_hour = int(getattr(settings, 'SYNC_CATALOG_SCHEDULE_HOUR', 1))
    sync_catalog_schedule_minute = int(getattr(settings, 'SYNC_CATALOG_SCHEDULE_MINUTE', 0))
    sync_compatibility_schedule_hour = int(getattr(settings, 'SYNC_COMPATIBILITY_SCHEDULE_HOUR', 2))
    sync_compatibility_schedule_minute = int(getattr(settings, 'SYNC_COMPATIBILITY_SCHEDULE_MINUTE', 30))

    base_schedule.update({
        'sync-odoo-products-nightly': {
            'task': 'apps.sync.tasks.sync_all_active_providers',
            'schedule': crontab(
                hour=sync_catalog_schedule_hour,
                minute=sync_catalog_schedule_minute,
            ),
        },
        'sync-odoo-compatibility-nightly': {
            'task': 'apps.sync.tasks.sync_all_compatibility',
            'schedule': crontab(
                hour=sync_compatibility_schedule_hour,
                minute=sync_compatibility_schedule_minute,
            ),
        },
        'sync-odoo-stock-interval': {
            'task': 'apps.sync.tasks.sync_all_stock',
            'schedule': timedelta(minutes=sync_stock_interval_minutes),
        },
        'recalculate-workshop-scores': {
            'task': 'apps.services.tasks.recalculate_workshop_scores',
            'schedule': workshop_score_recalculate_schedule,
        },
    })
    return base_schedule