"""
Tareas Celery para Orders - Integración con Odoo
"""
from celery import shared_task
from django.db import transaction as db_transaction
from django.utils import timezone
import logging

from .models import SubOrder
from .signals import sync_suborder_to_odoo, update_odoo_payment_status

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def create_odoo_sale_order(self, sub_order_id):
    """
    Crear Sale Order en Odoo.
    Se encola cuando SubOrder.status = 'pago_en_revision' (cliente sube comprobante).
    La tarea es idempotente via odoo_sale_id: si ya existe, se omite silenciosamente.

    Idempotencia de doble capa:
      1. select_for_update(): serializa tareas concurrentes para la misma SubOrder en Django.
         Si otra tarea ya guardó odoo_sale_id, esta sale temprano sin llamar a Odoo.
      2. UNIQUE(x_marketplace_suborder_id) en Odoo: última línea de defensa en la BD de Odoo.
            Si se viola el constraint en JSON-RPC, se trata como éxito idempotente.
    """
    logger.info(f"🚀 Iniciando creación de Sale Order en Odoo para SubOrder {sub_order_id}")

    try:
        # select_for_update dentro de atomic() serializa tareas concurrentes para la misma SubOrder.
        with db_transaction.atomic():
            try:
                sub_order = SubOrder.objects.select_for_update().select_related(
                    'order__customer__user',
                    'provider'
                ).prefetch_related('items__product', 'payments').get(id=sub_order_id)
            except SubOrder.DoesNotExist:
                logger.error(f"❌ SubOrder {sub_order_id} no encontrada")
                return {'success': False, 'error': 'SubOrder no encontrada'}

            # Idempotencia nivel Django: ¿otra tarea concurrente ya la sincronizó?
            if sub_order.odoo_sale_id:
                logger.info(
                    f"⏩ SubOrder {sub_order_id} ya tiene odoo_sale_id={sub_order.odoo_sale_id}, "
                    f"se omite."
                )
                return {
                    'success': True,
                    'sale_order_id': sub_order.odoo_sale_id,
                    'sub_order_number': sub_order.sub_order_number,
                    'skipped': True,
                }

            # Llamada JSON-RPC + guarda odoo_sale_id en Django (dentro del lock)
            sale_order_id = sync_suborder_to_odoo(sub_order)

        # Fuera del atomic: limpiar error previo si hubo
        if sale_order_id:
            if sub_order.odoo_sync_error:
                sub_order.odoo_sync_error = False
                sub_order.odoo_sync_error_detail = ''
                sub_order.save(update_fields=['odoo_sync_error', 'odoo_sync_error_detail'])
            logger.info(f"🎉 Sale Order creada exitosamente en Odoo: {sale_order_id}")
            return {
                'success': True,
                'sale_order_id': sale_order_id,
                'sub_order_number': sub_order.sub_order_number,
            }

        raise ConnectionError(
            'sync_suborder_to_odoo retornó None; Odoo no disponible o error de sincronización'
        )

    except ValueError as e:
        # Error de datos Django (ej: ningún producto tiene odoo_product_id) — no reintentar.
        logger.error(f"❌ Error de datos en SubOrder {sub_order_id}: {e}")
        _mark_odoo_sync_error(sub_order_id, str(e))
        return {'success': False, 'error': str(e)}

    except Exception as e:
        msg = str(e).lower()
        # Idempotencia: constraint UNIQUE disparado en Odoo (JSON-RPC devuelve Exception).
        if 'unique' in msg or 'duplicate' in msg:
            logger.warning(
                f"⚠️  SubOrder {sub_order_id} ya existe en Odoo (constraint). "
                f"Se trata como éxito idempotente."
            )
            return {'success': True, 'skipped': True, 'reason': 'duplicate_in_odoo'}

        logger.error(f"❌ Error creando Sale Order en Odoo: {str(e)}")
        if self.request.retries >= self.max_retries - 1:
            # Último intento agotado → marcar error definitivo
            _mark_odoo_sync_error(sub_order_id, str(e))
        raise self.retry(exc=e, countdown=300)


def _mark_odoo_sync_error(sub_order_id: int, detail: str):
    """Marca odoo_sync_error=True en la SubOrder para que el admin pueda reintentar."""
    try:
        SubOrder.objects.filter(pk=sub_order_id).update(
            odoo_sync_error=True,
            odoo_sync_error_detail=detail[:2000],  # truncar para no explotar el campo
        )
        logger.error(f"🚩 SubOrder {sub_order_id} marcada con odoo_sync_error=True")
    except Exception as ex:
        logger.error(f"No se pudo marcar odoo_sync_error en SubOrder {sub_order_id}: {ex}")


@shared_task(bind=True, max_retries=3)
def update_suborder_payment_status(self, sub_order_id):
    """
    Sincroniza los campos de pago (x_payment_status, flags booleanos) de la sale.order
    en Odoo cuando el estado de la SubOrder cambia en Django.
    Solo aplica a SubOrders que ya tienen odoo_sale_id (status = 'pago_en_revision' en adelante).
    """
    try:
        sub_order = SubOrder.objects.select_related(
            'order__customer__user',
            'provider'
        ).prefetch_related('payments').get(id=sub_order_id)

        success = update_odoo_payment_status(sub_order)

        if success:
            logger.info(f"✅ Estado de pago sincronizado en Odoo para SubOrder {sub_order_id}")
            return {'success': True, 'sub_order_id': sub_order_id}

        raise ConnectionError(
            f'update_odoo_payment_status retornó False para SubOrder {sub_order_id}'
        )

    except SubOrder.DoesNotExist:
        logger.error(f"❌ SubOrder {sub_order_id} no encontrada")
        return {'success': False, 'error': 'SubOrder no encontrada'}

    except Exception as e:
        logger.error(f"❌ Error actualizando estado de pago en Odoo: {str(e)}")
        raise self.retry(exc=e, countdown=300)


@shared_task
def update_order_status_from_odoo(sub_order_id):
    """
    Actualizar estado de SubOrder desde Odoo
    TODO: Implementar webhook o polling (Odoo → Django)
    """
    pass


@shared_task
def expire_pending_suborders():
    """
    Expirar SubOrders que llevan demasiado tiempo en 'pendiente_pago' o 'pago_en_revision'
    sin que el cliente haya completado el pago.

    La ventana de expiración se controla por Order.payment_deadline (default: 3h desde creación).
    La expiración es POR SubOrder, no por Order completa.

    Celery Beat la ejecuta cada 15 minutos.
    Se activa: status in (pendiente_pago, pago_en_revision) + payment_deadline < now() + expired=False
    Resultado: status='cancelado', expired=True → el signal recalculate_order_status actualiza Order.
    """
    now = timezone.now()

    # Solo expira SubOrders que NUNCA enviaron un comprobante (pendiente_pago).
    # 'pago_en_revision' y estados posteriores significan que el cliente ya actuó
    # → NO se cancelan por TTL, independientemente del deadline.
    expired_qs = SubOrder.objects.filter(
        status='pendiente_pago',
        order__payment_deadline__lt=now,
        expired=False,
    ).select_related('order')

    count = expired_qs.count()
    if count == 0:
        logger.info('⏰ expire_pending_suborders: ninguna SubOrder por expirar.')
        return {'expired': 0}

    logger.info(f'⏰ expire_pending_suborders: expirando {count} SubOrder(s)...')

    expired_ids = []
    for sub_order in expired_qs:
        sub_order.status  = 'cancelado'
        sub_order.expired = True
        sub_order.save(update_fields=['status', 'expired', 'updated_at'])
        # El post_save signal recalculate_order_status se dispara aquí automáticamente.
        expired_ids.append(sub_order.id)
        logger.info(
            f'  ↳ SubOrder {sub_order.sub_order_number} expirada '
            f'(deadline={sub_order.order.payment_deadline.isoformat()})'
        )

    logger.info(f'✅ expire_pending_suborders: {count} SubOrder(s) expiradas: {expired_ids}')
    return {'expired': count, 'sub_order_ids': expired_ids}


@shared_task
def reconcile_suborders_pending_odoo():
    """Reencola SubOrders que deberían existir en Odoo pero aún no tienen `odoo_sale_id`.

    Sirve como red de seguridad ante reinicios, caídas temporales de Odoo o ventanas
    en las que la tarea original se ejecutó antes de que Odoo estuviera disponible.
    La tarea `create_odoo_sale_order` ya es idempotente, por lo que reencolar es seguro.
    """
    pending_ids = list(
        SubOrder.objects.filter(
            status__in=['pago_en_revision', 'confirmado', 'enviado', 'entregado'],
            odoo_sale_id__isnull=True,
        )
        .order_by('id')
        .values_list('id', flat=True)[:200]
    )

    if not pending_ids:
        logger.info('🔎 reconcile_suborders_pending_odoo: ninguna SubOrder pendiente.')
        return {'requeued': 0, 'sub_order_ids': []}

    for sub_order_id in pending_ids:
        create_odoo_sale_order.delay(sub_order_id)

    logger.warning(
        '🔁 reconcile_suborders_pending_odoo: %s SubOrder(s) reencoladas: %s',
        len(pending_ids),
        pending_ids,
    )
    return {'requeued': len(pending_ids), 'sub_order_ids': pending_ids}


@shared_task
def send_order_confirmation_email(sub_order_id):
    """
    Enviar email de confirmación
    TODO: Implementar cuando tengamos email configurado
    """
    pass