"""
Utilidades para sincronización con Odoo
"""
import xmlrpc.client
import logging

logger = logging.getLogger(__name__)

# Configuración de Odoo
ODOO_URL = "http://odoo:8069"
ODOO_DB = "ecomparts_odoo_shared"
ODOO_ADMIN = "admin"
ODOO_PASSWORD = "admin"


def get_odoo_connection():
    """Obtener conexión con Odoo"""
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_ADMIN, ODOO_PASSWORD, {})
        if uid:
            models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            return uid, models
        return None, None
    except Exception as e:
        logger.error(f"Error conectando a Odoo: {e}")
        return None, None


def sync_suborder_to_odoo(suborder):
    """
    Sincronizar una SubOrder con Odoo.
    Debe llamarse DESPUÉS de crear los OrderItems.
    
    Returns:
        int: ID de la Sale Order en Odoo, o None si falla
    """
    from .models import OrderItem
    
    # Verificar si ya está sincronizado
    if suborder.odoo_sale_id:
        logger.info(f"SubOrder {suborder.sub_order_number} ya está sincronizada")
        return suborder.odoo_sale_id
    
    logger.info(f"📤 Sincronizando SubOrder {suborder.sub_order_number} con Odoo...")
    
    try:
        # Conectar a Odoo
        uid, models = get_odoo_connection()
        if not uid:
            logger.error("No se pudo conectar a Odoo")
            return None
        
        provider = suborder.provider
        customer = suborder.order.customer
        
        # 1. Buscar o crear Partner (cliente) en Odoo
        partner_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'search',
            [[('email', '=', customer.user.email)]])
        
        if partner_ids:
            partner_id = partner_ids[0]
            logger.info(f"✅ Partner existente: ID {partner_id}")
        else:
            # Crear partner
            partner_data = {
                'name': f"{customer.user.first_name} {customer.user.last_name}",
                'email': customer.user.email,
                'phone': customer.phone or '',
                'customer_rank': 1,
            }
            partner_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                'res.partner', 'create', [partner_data])
            logger.info(f"✅ Partner creado: ID {partner_id}")
        
        # 2. Preparar líneas de la orden
        order_lines = []
        items = OrderItem.objects.filter(sub_order=suborder)
        
        for item in items:
            if not item.product.odoo_product_id:
                logger.warning(f"⚠️  Producto {item.product.name} no tiene odoo_product_id")
                continue
            
            order_lines.append((0, 0, {
                'product_id': item.product.odoo_product_id,
                'name': item.product_name,
                'product_uom_qty': item.quantity,
                'price_unit': float(item.unit_price),
            }))
        
        if not order_lines:
            logger.error("No hay líneas de orden válidas para sincronizar")
            return None
        
        # 3. Crear Sale Order en Odoo
        sale_order_data = {
            'partner_id': partner_id,
            'company_id': provider.odoo_company_id,
            'order_line': order_lines,
            'client_order_ref': suborder.sub_order_number,
        }
        
        sale_order_id = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
            'sale.order', 'create', [sale_order_data])
        
        # 4. Actualizar SubOrder con el ID de Odoo
        suborder.odoo_sale_id = sale_order_id
        suborder.save(update_fields=['odoo_sale_id'])
        
        logger.info(f"🎉 Sale Order creada en Odoo: ID {sale_order_id} para SubOrder {suborder.sub_order_number}")
        
        return sale_order_id
        
    except Exception as e:
        logger.error(f"❌ Error sincronizando SubOrder {suborder.sub_order_number}: {e}")
        return None