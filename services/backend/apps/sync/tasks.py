"""
Tareas Celery de sincronización — capas delgadas sobre apps/sync/services/.

Cada tarea solo:
  1. Deserializa los argumentos de Celery.
  2. Delega al módulo de servicio correspondiente.
  3. Devuelve el resultado.

La lógica de negocio vive exclusivamente en apps/sync/services/*.
"""
from celery import shared_task
from apps.marketplace.models import Provider
import logging

logger = logging.getLogger(__name__)


# ── Registro automático de vendor ────────────────────────────────────────────

@shared_task
def create_provider_with_odoo_setup(user_id, provider_data, odoo_password):
    """Crea un Provider completo con su Company y Usuario en Odoo."""
    from apps.sync.services.provisioning import create_provider_with_odoo_setup as _svc
    return _svc(user_id, provider_data, odoo_password)


# ── Sincronización de providers ──────────────────────────────────────────────

@shared_task
def sync_provider_products(provider_id, include_compatibility=True):
    """Sincroniza categorías, productos y stock; compatibilidades opcionalmente."""
    from apps.sync.services.products import sync_provider_products as _svc
    return _svc(provider_id, include_compatibility=include_compatibility)


@shared_task
def sync_all_active_providers():
    """Dispara la sync de catálogo base sin compatibilidades para todos los providers."""
    providers = Provider.objects.filter(is_active=True, is_approved=True)
    logger.info("Iniciando sincronización de %d providers", providers.count())
    results = []
    for provider in providers:
        result = sync_provider_products.delay(
            provider.id,
            include_compatibility=False,
        )
        results.append({
            'provider_id': provider.id,
            'provider_name': provider.name,
            'task_id': result.id,
        })
    return {'total_providers': providers.count(), 'tasks_launched': results}


@shared_task
def sync_all_compatibility():
    """Dispara la sync de compatibilidades para todos los providers activos y aprobados."""
    providers = Provider.objects.filter(
        is_active=True,
        is_approved=True,
        odoo_company_id__isnull=False,
    )
    logger.info("Iniciando sync de compatibilidades para %d providers", providers.count())
    results = []
    for provider in providers:
        result = sync_provider_compatibility.delay(provider.id)
        results.append({'provider_id': provider.id, 'task_id': result.id})
    return {'total_providers': providers.count(), 'tasks_launched': results}


@shared_task
def sync_all_stock():
    """
    Dispara sync_provider_stock para todos los providers activos.
    Se ejecuta con una frecuencia configurable vía Celery Beat.
    Solo actualiza total_stock_cached.
    """
    providers = Provider.objects.filter(
        is_active=True,
        is_approved=True,
        odoo_company_id__isnull=False,
    )
    logger.info("Iniciando sync de stock para %d providers", providers.count())
    results = []
    for provider in providers:
        result = sync_provider_stock.delay(provider.id)
        results.append({'provider_id': provider.id, 'task_id': result.id})
    return {'total_providers': providers.count(), 'tasks_launched': results}


@shared_task
def sync_provider_compatibility(provider_id):
    """Sincroniza compatibilidades producto↔vehículo de un provider."""
    from apps.sync.services.compatibility import sync_provider_compatibility as _svc
    return _svc(provider_id)


@shared_task
def sync_provider_stock(provider_id):
    """Actualiza total_stock_cached de todos los productos del provider."""
    from apps.sync.services.products import sync_provider_stock as _svc
    return _svc(provider_id)


@shared_task
def check_providers_for_upgrade():
    """Verifica si algún provider necesita upgrade de tier. Corre diariamente."""
    providers = Provider.objects.filter(is_active=True, is_approved=True)
    upgrade_suggestions = []
    for provider in providers:
        suggested_tier = provider.check_upgrade_needed()
        if suggested_tier:
            upgrade_suggestions.append({
                'provider_id': provider.id,
                'provider_name': provider.name,
                'current_tier': provider.tier,
                'suggested_tier': suggested_tier,
                'usage': provider.get_usage_percentage(),
            })
            logger.info(
                "Provider %s necesita upgrade: %s → %s",
                provider.name, provider.tier, suggested_tier,
            )
            # TODO: send_upgrade_notification.delay(provider.id, suggested_tier)
    return {
        'total_checked': providers.count(),
        'upgrades_needed': len(upgrade_suggestions),
        'suggestions': upgrade_suggestions,
    }


@shared_task
def create_order_in_odoo(marketplace_order_id):
    """Crea una orden de venta en el Odoo del provider correspondiente."""
    # TODO: Implementar cuando órdenes estén totalmente migradas
    pass


# ── Mantenimiento ─────────────────────────────────────────────────────────────

@shared_task
def verify_provider_odoo_connection(provider_id):
    """Verifica que la conexión a Odoo del provider funcione correctamente."""
    from apps.sync.services.provisioning import verify_provider_odoo_connection as _svc
    return _svc(provider_id)
