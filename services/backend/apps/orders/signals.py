"""
Señales de órdenes — capas delgadas + lógica pura de Django.

Las funciones que tocan Odoo viven en apps/sync/services/orders.py.
Este módulo re-exporta esas funciones para mantener compatibilidad con todos
los imports existentes (management commands, views, tasks).

Contiene directamente:
  - recalculate_order_status   — deriva Order.status desde sus SubOrders
  - update_customer_provider_stats — actualiza stats de fidelización

Delega a apps.sync.services.orders:
  - get_odoo_connection, sync_suborder_to_odoo
  - update_odoo_payment_status, update_odoo_delivery_status
  - _PAYMENT_STATUS_MAP, _DELIVERY_STATUS_MAP
  - (demás helpers privados opcionales)
"""
import logging

logger = logging.getLogger(__name__)

# ── Re-exportaciones de apps.sync.services.orders ────────────────────────────
# (garantiza compatibilidad con cualquier código que importe desde aquí)
from apps.sync.services.orders import (  # noqa: F401, E402
    get_odoo_connection,
    sync_suborder_to_odoo,
    update_odoo_payment_status,
    update_odoo_delivery_status,
    _PAYMENT_STATUS_MAP,
    _DELIVERY_STATUS_MAP,
    _company_context,
    _format_delivery_address,
    _get_utm_source_id,
    _get_provider_user_id,
    _get_or_create_partner,
)


# ─────────────────────────────────────────────────────────────────────────────
# Signal: recalculate_order_status
# ─────────────────────────────────────────────────────────────────────────────

def recalculate_order_status(sender, instance, **kwargs):
    """Recalcula Order.status cada vez que una SubOrder es guardada.
    Order.status NUNCA se escribe manualmente — siempre es derivado de sus
    SubOrders.

    Lógica de derivación (prioridad descendente):
      cancelado      — todas las SubOrders activas están canceladas
      completado     — todas las SubOrders activas fueron entregadas
      enviado        — al menos una SubOrder está en tránsito
      procesando     — al menos una SubOrder fue confirmada en Odoo
      pagado         — todas las SubOrders activas tienen pago en revisión
      pendiente_pago — caso base

    Se conecta en OrdersConfig.ready() para evitar importaciones circulares.
    """
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and 'status' not in update_fields:
        return

    order = instance.order
    sub_orders = list(order.sub_orders.all())

    if not sub_orders:
        return

    active = [so for so in sub_orders if so.status != 'cancelado']
    active_statuses = {so.status for so in active}

    if not active:
        new_status = 'cancelado'
    elif active_statuses <= {'entregado'}:
        new_status = 'completado'
    elif active_statuses & {'enviado', 'entregado'}:
        new_status = 'enviado'
    elif 'confirmado' in active_statuses:
        new_status = 'procesando'
    elif active_statuses <= {'pago_en_revision'}:
        new_status = 'pagado'
    else:
        new_status = 'pendiente_pago'

    if order.status != new_status:
        from .models import Order as OrderModel
        OrderModel.objects.filter(pk=order.pk).update(status=new_status)
        logger.info(
            'Order %s: status "%s" → "%s"',
            order.order_number, order.status, new_status,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Signal: update_customer_provider_stats
# ─────────────────────────────────────────────────────────────────────────────

from apps.orders.pricing.customer_discount import ESTADOS_VALIDOS as ESTADOS_VALIDOS_STATS  # noqa: E402


def update_customer_provider_stats(sender, instance, **kwargs):
    """
    Recalcula CustomerProviderStats cuando una SubOrder entra en un estado
    válido (confirmado / enviado / entregado).

    Se conecta en OrdersConfig.ready().
    """
    if instance.status not in ESTADOS_VALIDOS_STATS:
        return

    try:
        from decimal import Decimal
        from django.db.models import Sum, Count
        from apps.customer.models import CustomerProviderStats
        from apps.discounts.models import DiscountRule
        from apps.orders.pricing.customer_discount import (
            _historial_ponderado, _esquema_ponderacion, _buscar_regla,
        )

        customer = instance.order.customer
        provider = instance.provider

        # ── Acumulados brutos ────────────────────────────────────────────
        agg = (
            sender.objects.filter(
                order__customer=customer,
                provider=provider,
                status__in=list(ESTADOS_VALIDOS_STATS),
            ).aggregate(total=Sum('total'), orders=Count('id'))
        )
        total_spent  = agg['total'] or Decimal('0.00')
        total_orders = agg['orders'] or 0

        # ── Historial ponderado ──────────────────────────────────────────
        esquema  = _esquema_ponderacion(customer.customer_type)
        weighted = _historial_ponderado(customer, provider, esquema)

        # ── Descuento actual ─────────────────────────────────────────────
        current_pct = _buscar_regla(customer.customer_type, provider, weighted)

        # ── Siguiente tier ────────────────────────────────────────────────
        siguiente = (
            DiscountRule.objects
            .filter(
                customer_type=customer.customer_type,
                provider=provider,
                min_amount__gt=weighted,
                is_active=True,
            )
            .order_by('min_amount')
            .first()
        )
        if siguiente is None:
            siguiente = (
                DiscountRule.objects
                .filter(
                    customer_type=customer.customer_type,
                    provider__isnull=True,
                    min_amount__gt=weighted,
                    is_active=True,
                )
                .order_by('min_amount')
                .first()
            )
        next_tier_amount = (
            max(Decimal('0.00'), siguiente.min_amount - weighted)
            if siguiente else Decimal('0.00')
        )

        # ── Upsert ────────────────────────────────────────────────────────
        CustomerProviderStats.objects.update_or_create(
            customer=customer,
            provider=provider,
            defaults={
                'total_spent': total_spent,
                'total_orders': total_orders,
                'weighted_history': weighted,
                'current_discount_percent': current_pct,
                'next_tier_amount': next_tier_amount,
            },
        )
        logger.info(
            "CustomerProviderStats actualizado: %s → %s | "
            "gastado=%.2f ponderado=%.2f descuento=%s%% falta=%.2f",
            customer, provider.name,
            total_spent, weighted, current_pct, next_tier_amount,
        )

        # ── CustomerStats global ──────────────────────────────────────────
        from apps.customer.models import CustomerStats

        global_agg = customer.provider_stats.aggregate(
            total_sum=Sum('total_spent'),
            orders=Sum('total_orders'),
        )
        g_total  = global_agg['total_sum'] or Decimal('0.00')
        g_orders = global_agg['orders'] or 0
        g_avg = (
            (g_total / g_orders).quantize(Decimal('0.01')) if g_orders else Decimal('0.00')
        )
        CustomerStats.objects.update_or_create(
            customer=customer,
            defaults={
                'total_spent': g_total,
                'total_orders': g_orders,
                'average_order_value': g_avg,
            },
        )
    except Exception:
        logger.exception(
            "Error actualizando CustomerProviderStats para SubOrder %s",
            instance.pk,
        )
