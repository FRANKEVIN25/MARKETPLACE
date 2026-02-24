"""
Tareas Celery para Orders - Integración con Odoo
"""
from celery import shared_task
from django.utils import timezone
import logging

from .models import SubOrder
from .signals import sync_suborder_to_odoo

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def create_odoo_sale_order(self, sub_order_id):
    """
    Crear Sale Order en Odoo
    
    Args:
        sub_order_id: ID de la SubOrder
    """
    try:
        logger.info(f"🚀 Iniciando creación de Sale Order en Odoo para SubOrder {sub_order_id}")
        
        sub_order = SubOrder.objects.select_related(
            'order__customer__user',
            'provider'
        ).prefetch_related('items__product').get(id=sub_order_id)
        
        # Sincronizar con Odoo usando la función del módulo signals
        sale_order_id = sync_suborder_to_odoo(sub_order)
        
        if sale_order_id:
            logger.info(f"🎉 Sale Order creada exitosamente en Odoo: {sale_order_id}")
            
            return {
                'success': True,
                'sale_order_id': sale_order_id,
                'sub_order_number': sub_order.sub_order_number
            }
        else:
            logger.error(f"❌ No se pudo crear Sale Order en Odoo")
            return {
                'success': False,
                'error': 'Error al sincronizar con Odoo'
            }
        
    except SubOrder.DoesNotExist:
        logger.error(f"❌ SubOrder {sub_order_id} no encontrada")
        return {
            'success': False,
            'error': 'SubOrder no encontrada'
        }
        
    except Exception as e:
        logger.error(f"❌ Error creando Sale Order en Odoo: {str(e)}")
        # Reintentar en 5 minutos
        raise self.retry(exc=e, countdown=300)


@shared_task
def update_order_status_from_odoo(sub_order_id):
    """
    Actualizar estado de SubOrder desde Odoo
    TODO: Implementar webhook o polling
    """
    pass


@shared_task
def send_order_confirmation_email(sub_order_id):
    """
    Enviar email de confirmación
    TODO: Implementar cuando tengamos email configurado
    """
    pass