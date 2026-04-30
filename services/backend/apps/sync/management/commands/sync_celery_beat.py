import json
from datetime import timedelta

from celery.schedules import crontab, schedule
from django.conf import settings
from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask, PeriodicTasks

from ecomparts.beat_schedule import get_periodic_schedule


LEGACY_TASK_NAMES = (
    'sync-odoo-products-every-hour',
    'sync-odoo-stock-every-15min',
)


class Command(BaseCommand):
    help = 'Sincroniza el beat_schedule definido en código hacia django-celery-beat'

    def handle(self, *args, **options):
        beat_schedule = get_periodic_schedule(getattr(settings, 'CELERY_BEAT_SCHEDULE', {}))
        timezone = getattr(settings, 'CELERY_TIMEZONE', settings.TIME_ZONE)

        synced_names = []
        for name, entry in beat_schedule.items():
            defaults = {
                'task': entry['task'],
                'enabled': entry.get('enabled', True),
                'one_off': entry.get('one_off', False),
                'args': json.dumps(entry.get('args', [])),
                'kwargs': json.dumps(entry.get('kwargs', {})),
                'description': entry.get('description', 'Sincronizada automáticamente desde ecomparts.celery'),
                'queue': entry.get('options', {}).get('queue'),
                'exchange': entry.get('options', {}).get('exchange'),
                'routing_key': entry.get('options', {}).get('routing_key'),
                'headers': json.dumps(entry.get('options', {}).get('headers', {})),
                'expire_seconds': entry.get('options', {}).get('expire_seconds'),
                'start_time': entry.get('start_time'),
            }

            schedule_definition = entry['schedule']
            if isinstance(schedule_definition, crontab):
                defaults.update(self._build_crontab_defaults(schedule_definition, timezone))
            elif isinstance(schedule_definition, (schedule, timedelta)):
                defaults.update(self._build_interval_defaults(schedule_definition))
            else:
                raise TypeError(
                    f"Schedule no soportado para '{name}': {type(schedule_definition).__name__}"
                )

            PeriodicTask.objects.update_or_create(name=name, defaults=defaults)
            synced_names.append(name)

        deleted_count, _ = PeriodicTask.objects.filter(name__in=LEGACY_TASK_NAMES).delete()
        PeriodicTasks.update_changed()

        self.stdout.write(
            self.style.SUCCESS(
                f'Se sincronizaron {len(synced_names)} tarea(s) periódicas.'
            )
        )
        if deleted_count:
            self.stdout.write(
                self.style.WARNING(
                    f'Se eliminaron {deleted_count} tarea(s) legacy de django-celery-beat.'
                )
            )

    def _build_crontab_defaults(self, schedule_definition, timezone):
        crontab_schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=str(schedule_definition._orig_minute),
            hour=str(schedule_definition._orig_hour),
            day_of_week=str(schedule_definition._orig_day_of_week),
            day_of_month=str(schedule_definition._orig_day_of_month),
            month_of_year=str(schedule_definition._orig_month_of_year),
            timezone=timezone,
        )
        return {
            'crontab': crontab_schedule,
            'interval': None,
            'solar': None,
            'clocked': None,
        }

    def _build_interval_defaults(self, schedule_definition):
        run_every = schedule_definition
        if isinstance(schedule_definition, schedule):
            run_every = schedule_definition.run_every
        total_seconds = max(1, int(run_every.total_seconds()))
        interval_schedule, _ = IntervalSchedule.objects.get_or_create(
            every=total_seconds,
            period=IntervalSchedule.SECONDS,
        )
        return {
            'crontab': None,
            'interval': interval_schedule,
            'solar': None,
            'clocked': None,
        }