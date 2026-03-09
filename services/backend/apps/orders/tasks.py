"""
Tareas Celery para Orders - Integración con Odoo
"""
import xmlrpc.client

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
    Opcionalmente se vuelve a encolar en 'pagado' (proveedor confirma) para sincronizar
    el estado de pago; la tarea es idempotente via odoo_sale_id.

    Idempotencia de doble capa:
      1. select_for_update(): serializa tareas concurrentes para la misma SubOrder en Django.
         Si otra tarea ya guardó odoo_sale_id, esta sale temprano sin llamar a Odoo.
      2. UNIQUE(x_marketplace_suborder_id) en Odoo: última línea de defensa en la BD de Odoo.
         Si se viola el constraint (xmlrpc.Fault), se trata como éxito idempotente.
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

            # Llamada XML-RPC + guarda odoo_sale_id en Django (dentro del lock)
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

        logger.error("❌ No se pudo crear Sale Order en Odoo (sync retornó None)")
        return {'success': False, 'error': 'Error al sincronizar con Odoo'}

    except xmlrpc.client.Fault as fault:
        msg = fault.faultString
        # Idempotencia nivel Odoo: constraint UNIQUE(x_marketplace_suborder_id) disparado.
        if 'unique' in msg.lower() or 'duplicate' in msg.lower():
            logger.warning(
                f"⚠️  SubOrder {sub_order_id} ya existe en Odoo (constraint). "
                f"Se trata como éxito idempotente."
            )
            return {'success': True, 'skipped': True, 'reason': 'duplicate_in_odoo'}
        # Otro Fault de Odoo (datos inválidos, permisos, etc.) → marcar error, no reintentar.
        logger.error(f"❌ Odoo Fault SubOrder {sub_order_id}: {msg}")
        _mark_odoo_sync_error(sub_order_id, msg[:2000])
        return {'success': False, 'error': msg}

    except ValueError as e:
        # Error de datos Django (ej: ningún producto tiene odoo_product_id) — no reintentar.
        logger.error(f"❌ Error de datos en SubOrder {sub_order_id}: {e}")
        _mark_odoo_sync_error(sub_order_id, str(e))
        return {'success': False, 'error': str(e)}

    except Exception as e:
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
    Solo aplica a SubOrders que ya tienen odoo_sale_id (status >= 'pagado').
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
        else:
            logger.warning(f"⚠️  No se pudo sincronizar estado de pago para SubOrder {sub_order_id}")
            return {'success': False, 'error': 'update_odoo_payment_status retornó False'}

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

    expired_qs = SubOrder.objects.filter(
        status__in=['pendiente_pago', 'pago_en_revision'],
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
def send_order_confirmation_email(sub_order_id):
    """
    Enviar email de confirmación
    TODO: Implementar cuando tengamos email configurado
    """
    pass