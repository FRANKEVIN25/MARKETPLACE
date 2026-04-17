from django.utils import timezone

from apps.sync.models import ProviderSyncState


def mark_sync_started(provider, sync_type: str):
    """Marca el inicio de una fase de sync para un provider."""
    started_at = timezone.now()
    ProviderSyncState.objects.update_or_create(
        provider=provider,
        sync_type=sync_type,
        defaults={
            'last_status': 'running',
            'last_started_at': started_at,
            'last_error': '',
        },
    )
    return started_at


def mark_sync_finished(
    provider,
    sync_type: str,
    started_at,
    *,
    status: str,
    metrics: dict | None = None,
    error_message: str = '',
):
    """Persiste el último estado conocido de una fase de sync."""
    finished_at = timezone.now()
    duration = None
    if started_at is not None:
        duration = max(0.0, (finished_at - started_at).total_seconds())

    defaults = {
        'last_status': status,
        'last_started_at': started_at,
        'last_finished_at': finished_at,
        'last_duration_seconds': duration,
        'last_error': error_message or '',
        'last_metrics': metrics or {},
    }
    if status == 'success':
        defaults['last_success_at'] = finished_at

    ProviderSyncState.objects.update_or_create(
        provider=provider,
        sync_type=sync_type,
        defaults=defaults,
    )