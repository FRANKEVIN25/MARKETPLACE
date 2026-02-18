"""
Tareas Celery para Orders - Integración con Odoo
"""
from celery import shared_task
from django.utils import timezone
from decimal import Decimal
import logging

from .models import SubOrder
from apps.sync.odoo_connector import OdooConnector

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def create_odoo_sale_order(self, sub_order_id):
    """
    Crear Sale Order en Odoo cuando el pago es confirmado
    
    Args:
        sub_order_id: ID de la SubOrder confirmada
        
    Flow:
        1. Obtener SubOrder y datos
        2. Conectar a Odoo del proveedor
        3. Crear/obtener partner (cliente)
        4. Crear Sale Order
        5. Crear Order Lines (productos)
        6. Actualizar SubOrder con odoo_sale_id
    """
    try:
        logger.info(f"🚀 Iniciando creación de Sale Order en Odoo para SubOrder {sub_order_id}")
        
        # 1. Obtener SubOrder
        sub_order = SubOrder.objects.select_related(
            'order__customer__user',
            'order__shipping_address',
            'provider'
        ).prefetch_related('items__product').get(id=sub_order_id)
        
        # Validar estado
        if sub_order.status != 'pagado_confirmado':
            logger.warning(f"SubOrder {sub_order_id} no está en estado pagado_confirmado")
            return {
                'success': False,
                'error': 'SubOrder no está confirmada'
            }
        
        # 2. Conectar a Odoo del proveedor
        provider = sub_order.provider
        connection_info = provider.get_odoo_connection_info()
        
        odoo = OdooConnector(
            url=connection_info['url'],
            db_name=connection_info['db'],
            username='admin',  # TODO: Usar credenciales del proveedor
            password='admin'
        )
        
        logger.info(f"✅ Conectado a Odoo: {connection_info['url']}")
        
        # 3. Obtener o crear Partner (cliente) en Odoo
        customer = sub_order.order.customer
        user = customer.user
        
        # Buscar partner por email
        partner_ids = odoo.execute_kw(
            'res.partner',
            'search',
            [[('email', '=', user.email)]]
        )
        
        if partner_ids:
            partner_id = partner_ids[0]
            logger.info(f"✅ Partner existente encontrado: {partner_id}")
        else:
            # Crear nuevo partner
            address = sub_order.order.shipping_address
            
            partner_data = {
                'name': customer.get_full_name(),
                'email': user.email,
                'phone': customer.phone or address.contact_phone if address else '',
                'customer_rank': 1,
                'company_id': False,
            }
            
            # Agregar dirección si existe
            if address:
                partner_data.update({
                    'street': f"{address.street} {address.street_number}".strip(),
                    'street2': address.apartment,
                    'city': address.city,
                    'state_id': False,  # TODO: Mapear estados
                    'zip': address.postal_code,
                    'country_id': False,  # TODO: Mapear país
                })
            
            # Agregar documento si es empresa
            if customer.customer_type == 'company' and customer.document_number:
                partner_data['vat'] = customer.document_number
                partner_data['company_type'] = 'company'
            else:
                partner_data['company_type'] = 'person'
            
            partner_id = odoo.execute_kw('res.partner', 'create', [partner_data])
            logger.info(f"✅ Partner creado: {partner_id}")
        
        # 4. Crear Sale Order
        sale_order_data = {
            'partner_id': partner_id,
            'company_id': connection_info.get('company_id'),
            'user_id': provider.odoo_user_id,  # Asignar a usuario del proveedor
            'date_order': sub_order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'state': 'draft',
            'note': sub_order.order.customer_notes or '',
        }
        
        sale_order_id = odoo.execute_kw('sale.order', 'create', [sale_order_data])
        logger.info(f"✅ Sale Order creada en Odoo: {sale_order_id}")
        
        # 5. Crear Order Lines (productos)
        for item in sub_order.items.all():
            product = item.product
            
            # Buscar producto en Odoo
            if not product.odoo_product_id:
                logger.warning(f"⚠️ Producto {product.id} no tiene odoo_product_id, saltando...")
                continue
            
            order_line_data = {
                'order_id': sale_order_id,
                'product_id': product.odoo_product_id,
                'product_uom_qty': item.quantity,
                'price_unit': float(item.unit_price),
                'tax_id': False,  # TODO: Mapear impuestos
            }
            
            line_id = odoo.execute_kw('sale.order.line', 'create', [order_line_data])
            logger.info(f"  ✅ Order Line creada: Producto {product.name} x{item.quantity}")
        
        # 6. Confirmar Sale Order (opcional, según configuración)
        # odoo.execute_kw('sale.order', 'action_confirm', [[sale_order_id]])
        
        # 7. Actualizar SubOrder
        sub_order.odoo_sale_id = sale_order_id
        sub_order.status = 'procesando'
        sub_order.save()
        
        logger.info(f"🎉 Sale Order creada exitosamente en Odoo: {sale_order_id}")
        
        return {
            'success': True,
            'sale_order_id': sale_order_id,
            'partner_id': partner_id,
            'sub_order_number': sub_order.sub_order_number
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
    Actualizar estado de SubOrder desde Odoo (polling/webhook)
    
    TODO: Implementar cuando Odoo tenga webhooks configurados
    o como tarea periódica de polling
    """
    try:
        sub_order = SubOrder.objects.get(id=sub_order_id)
        
        if not sub_order.odoo_sale_id:
            return {'success': False, 'error': 'No tiene Sale Order en Odoo'}
        
        # Conectar a Odoo
        provider = sub_order.provider
        connection_info = provider.get_odoo_connection_info()
        
        odoo = OdooConnector(
            url=connection_info['url'],
            db_name=connection_info['db'],
            username='admin',
            password='admin'
        )
        
        # Obtener estado de Sale Order
        sale_order = odoo.execute_kw(
            'sale.order',
            'read',
            [[sub_order.odoo_sale_id]],
            {'fields': ['state', 'delivery_status', 'invoice_status']}
        )
        
        if sale_order:
            odoo_state = sale_order[0]['state']
            
            # Mapear estados de Odoo a estados de SubOrder
            status_mapping = {
                'draft': 'procesando',
                'sent': 'procesando',
                'sale': 'procesando',
                'done': 'entregado',
                'cancel': 'cancelado',
            }
            
            new_status = status_mapping.get(odoo_state, sub_order.status)
            
            if new_status != sub_order.status:
                sub_order.status = new_status
                sub_order.save()
                
                logger.info(f"✅ Estado actualizado: {sub_order.sub_order_number} → {new_status}")
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"❌ Error actualizando estado desde Odoo: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def send_order_confirmation_email(sub_order_id):
    """
    Enviar email de confirmación cuando pago es confirmado
    
    TODO: Implementar cuando tengamos configuración de email
    """
    pass

