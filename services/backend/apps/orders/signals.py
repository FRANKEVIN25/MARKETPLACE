"""
Utilidades para sincronización con Odoo
Migrado de XML-RPC → JSON-RPC el 9 Mar 2026
"""
import logging
from django.utils import timezone
from apps.sync.odoo_connector import OdooConnector

logger = logging.getLogger(__name__)

# Mapa SubOrder.status → x_payment_status (espejo exacto de SubOrder.STATUS_CHOICES).
# Solo los estados que efectivamente llegan a Odoo (pagado en adelante).
_PAYMENT_STATUS_MAP = {
    'pagado': 'pagado',
    'confirmado': 'confirmado',
    'enviado': 'enviado',
    'entregado': 'entregado',
    'cancelado': 'cancelado',
}

def get_odoo_connection():
    """
    Retorna un OdooConnector autenticado usando las credenciales del settings.

    Returns:
        OdooConnector | None: Conector listo para usar, o None si falla la auth
    """
    try:
        connector = OdooConnector()
        if connector.uid:
            return connector
        logger.error("❌ Falló la autenticación con Odoo")
        return None
    except Exception as e:
        logger.error(f"Error conectando a Odoo: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# Helpers privados
# ─────────────────────────────────────────────────────────────

def _format_delivery_address(order):
    """Construye una cadena legible con la dirección de envío del pedido.
    Retorna cadena vacía si no hay dirección (ej: recojo en tienda).
    """
    addr = order.shipping_address
    if not addr:
        return ''

    line = f"{addr.street} {addr.street_number}".strip()
    if addr.apartment:
        line += f", {addr.apartment}"

    parts = [line, addr.district, addr.city, addr.state, addr.country]
    if addr.postal_code:
        parts[-1] += f" {addr.postal_code}"
    if addr.reference:
        parts.append(f"Ref: {addr.reference}")
    if addr.agency_name:
        parts.append(f"Agencia: {addr.agency_name}")

    return ' | '.join(p for p in parts if p)


def _get_utm_source_id(odoo: OdooConnector, name: str = 'ECOMPARTS Marketplace'):
    """Busca (o crea) el utm.source con el nombre indicado en Odoo.
    Retorna el ID del registro, o None si falla. Se usa para poblar source_id
    en la sale.order y así identificar las órdenes provenientes del marketplace.
    """
    try:
        source_ids = odoo.execute_kw(
            'utm.source',
            'search',
            [[['name', '=', name]]],
        )
        if source_ids:
            return source_ids[0]

        source_id = odoo.execute_kw(
            'utm.source',
            'create',
            [[{'name': name}]],
        )
        logger.info(f"✨ utm.source '{name}' creado en Odoo: ID {source_id}")
        return source_id
    except Exception as e:
        logger.warning(f"⚠️  No se pudo obtener utm.source '{name}': {e}")
        return None

def _get_provider_user_id(odoo, provider):
    """Retorna el user_id de Odoo del proveedor"""
    try:
        if provider.odoo_user_id:
            return provider.odoo_user_id
        return False
    except Exception:
        return False

def _get_or_create_partner(odoo: OdooConnector, customer):
    """Busca o crea un partner en Odoo para el customer dado.
    Estrategia:
      1. Buscar por email
      2. Si no existe, buscar por vat (DNI/RUC)
      3. Si no existe, crear nuevo partner

    Retorna partner_id (int).
    """
    email = customer.user.email or ''

    # 1. Búsqueda por email
    try:
        partner_ids = []
        if email:
            partner_ids = odoo.execute_kw(
                'res.partner',
                'search',
                [[['email', '=', email]]],
            )
        if partner_ids:
            logger.info(f"✅ Partner encontrado por email: ID {partner_ids[0]}")
            return partner_ids[0]

        # 2. Búsqueda por vat (document_number → DNI / RUC)
        if customer.document_number:
            partner_ids = odoo.execute_kw(
                'res.partner',
                'search',
                [[['vat', '=', customer.document_number]]],
            )
            if partner_ids:
                logger.info(
                    f"✅ Partner encontrado por vat ({customer.document_number}): "
                    f"ID {partner_ids[0]}"
                )
                return partner_ids[0]

        # 3. Crear nuevo partner
        full_name = f"{customer.user.first_name} {customer.user.last_name}".strip()
        partner_data = {
            'name': full_name or customer.user.username,
            'email': email,
            'phone': customer.phone or '',
            'vat': customer.document_number or '',
            'customer_rank': 1,
        }
        partner_id = odoo.execute_kw(
            'res.partner',
            'create',
            [[partner_data]],
        )
        logger.info(f"✅ Partner creado: ID {partner_id}")
        return partner_id
    except Exception as e:
        logger.error(f"❌ Error obteniendo/creando partner en Odoo: {e}")
        raise

# ─────────────────────────────────────────────────────────────
# Funciones públicas
# ─────────────────────────────────────────────────────────────

def _get_warehouse_id(odoo, company_id):
    """Obtiene el warehouse_id de Odoo para una company"""
    try:
        wh = odoo.execute_kw(
            'stock.warehouse', 'search_read',
            [[['company_id', '=', company_id]]],
            {'fields': ['id'], 'limit': 1, 'context': {'allowed_company_ids': [company_id]}}
        )
        return wh[0]['id'] if wh else False
    except Exception:
        return False

def sync_suborder_to_odoo(suborder):
    """Crea la Sale Order en Odoo para una SubOrder de Django (estado draft).
    Debe llamarse DESPUÉS de que los OrderItems estén guardados.

    - Idempotente: si odoo_sale_id ya existe, retorna ese ID sin duplicar.
    - Incluye todos los campos del módulo orders_odoo (entrega, pago, estados).
    - Busca el partner por email y, como fallback, por vat (DNI/RUC).
    - Lanza ValueError si ningún item tiene odoo_product_id (error explícito).

    Returns:
        int: ID de la Sale Order en Odoo, o None si falla la conexión.
    Raises:
        ValueError: si no hay líneas de orden válidas para sincronizar.
    """
    from .models import OrderItem

    # Idempotencia: no duplicar órdenes en Odoo
    if suborder.odoo_sale_id:
        logger.info(
            f"SubOrder {suborder.sub_order_number} ya sincronizada "
            f"(odoo_sale_id={suborder.odoo_sale_id})"
        )
        return suborder.odoo_sale_id

    logger.info(f"📤 Sincronizando SubOrder {suborder.sub_order_number} con Odoo...")

    try:
        odoo = get_odoo_connection()
        if not odoo:
            logger.error("No se pudo conectar a Odoo")
            return None

        order = suborder.order
        provider = suborder.provider
        customer = order.customer

        # 1. Partner
        partner_id = _get_or_create_partner(odoo, customer)

        # 2. Líneas de orden
        order_lines = []
        missing_odoo_id = []
        items = OrderItem.objects.filter(sub_order=suborder)

        for item in items:
            if not item.product.odoo_product_id:
                missing_odoo_id.append(item.product_name)
                continue

            order_lines.append(
                (
                    0,
                    0,
                    {
                        'product_id': item.product.odoo_product_id,
                        'name': item.product_name,
                        'product_uom_qty': item.quantity,
                        'price_unit': float(item.unit_price),
                    },
                )
            )

        if missing_odoo_id:
            logger.warning(
                f"⚠️  Productos sin odoo_product_id omitidos: {missing_odoo_id}"
            )

        if not order_lines:
            raise ValueError(
                f"SubOrder {suborder.sub_order_number}: ningún item tiene "
                f"odoo_product_id. Productos afectados: {missing_odoo_id}"
            )

        # 3. Crear Sale Order con campos del módulo orders_odoo
        # Obtener el comprobante de pago aprobado para incluir método y referencia
        approved_proof = suborder.payments.filter(status='approved').first()
        latest_proof = approved_proof or suborder.payments.order_by('-uploaded_at').first()

        # Obtener utm.source para marcar el origen como marketplace
        source_id = _get_utm_source_id(odoo)

        sale_order_data = {
            # Campos estándar
            'partner_id': partner_id,
            'company_id': provider.odoo_company_id,
            'order_line': order_lines,
            'client_order_ref': suborder.sub_order_number,
            'origin': order.order_number,
            'user_id': _get_provider_user_id(odoo, provider),

            # Referencia cruzada Django ↔ Odoo
            'x_marketplace_order_id': order.order_number,
            'x_marketplace_suborder_id': suborder.sub_order_number,

            # Datos de entrega
            'x_delivery_method': order.delivery_method,
            'x_delivery_address': _format_delivery_address(order),
            'x_customer_notes': order.customer_notes or '',

            # Información de pago del comprobante aprobado
            'x_payment_method': latest_proof.payment_method if latest_proof else False,
            'x_payment_reference': latest_proof.operation_number if latest_proof else '',
            'x_payment_amount_declared': float(latest_proof.amount) if latest_proof else 0.0,

            # Estado del pedido (espejo de SubOrder.status — Django es la verdad)
            'x_payment_status': _PAYMENT_STATUS_MAP.get(suborder.status, 'pagado'),

            # Origen: marketplace ECOMPARTS
            **({'source_id': source_id} if source_id else {}),

            # Sincronización
            'x_last_sync_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        result = odoo.execute_kw(
            'sale.order',
            'create',
            [[sale_order_data]],
        )
        sale_order_id = result[0] if isinstance(result, list) else result

        # 4. Guardar ID en Django
        suborder.odoo_sale_id = sale_order_id
        suborder.save(update_fields=['odoo_sale_id'])

        logger.info(
            f"🎉 Sale Order creada en Odoo: ID {sale_order_id} "
            f"→ SubOrder {suborder.sub_order_number}"
        )
        return sale_order_id

    except ValueError:
        # Error de negocio explícito: no reintentar en Celery
        raise
    except Exception as e:
        logger.error(
            f"❌ Error sincronizando SubOrder {suborder.sub_order_number}: {e}"
        )
        return None

# ─────────────────────────────────────────────────────────────
# Signal: recalculate_order_status
# ─────────────────────────────────────────────────────────────

def recalculate_order_status(sender, instance, **kwargs):
    """Recalcula Order.status cada vez que una SubOrder es guardada.
    Order.status NUNCA se escribe manualmente — siempre es derivado de sus
    SubOrders.

    Lógica de derivación (prioridad descendente):
      cancelado      — todas las SubOrders activas están canceladas
      completado     — todas las SubOrders activas fueron entregadas
      enviado        — al menos una SubOrder está en tránsito (enviado)
      procesando     — al menos una SubOrder fue confirmada en Odoo
      pagado         — todas las SubOrders activas tienen pago subido
                        (pago_en_revision) o confirmado
      pendiente_pago — caso base: al menos una SubOrder sin pago confirmado

    Se conecta en OrdersConfig.ready() para evitar importaciones circulares.
    """
    order = instance.order
    sub_orders = list(order.sub_orders.all())

    if not sub_orders:
        return

    active = [so for so in sub_orders if so.status != 'cancelado']
    active_statuses = {so.status for so in active}

    if not active:
        # Todos cancelados
        new_status = 'cancelado'
    elif active_statuses <= {'entregado'}:
        # Todas las activas fueron entregadas
        new_status = 'completado'
    elif active_statuses & {'enviado', 'entregado'}:
        # Al menos una en tránsito o entregada
        new_status = 'enviado'
    elif 'confirmado' in active_statuses:
        # Al menos una procesándose en Odoo
        new_status = 'procesando'
    elif active_statuses <= {'pago_en_revision', 'pagado'}:
        # Todas las activas con pago subido por el cliente (pago_en_revision)
        # o ya confirmado por el proveedor (pagado).
        # «pagado» en Order = el cliente pagó su parte; no requiere aprobación
        # del proveedor.
        new_status = 'pagado'
    else:
        # Caso base: alguna SubOrder sin pago
        new_status = 'pendiente_pago'

    if order.status != new_status:
        # Usar .update() para NO disparar el post_save de Order (evita cascadas).
        from .models import Order as OrderModel

        OrderModel.objects.filter(pk=order.pk).update(status=new_status)
        logger.info(
            f'📊 Order {order.order_number}: status '
            f'"{order.status}" → "{new_status}"'
        )

def update_odoo_payment_status(suborder):
    """Actualiza estado de pago en Odoo cuando avanza la SubOrder.
    Solo se llama para SubOrders en status >= 'pagado' (con odoo_sale_id).

    Returns:
        bool: True si la actualización fue exitosa, False en caso contrario.
    """
    if not suborder.odoo_sale_id:
        logger.warning(
            "update_odoo_payment_status: SubOrder "
            f"{suborder.sub_order_number} no tiene odoo_sale_id, se omite."
        )
        return False

    logger.info(
        "🔄 Actualizando estado de pago en Odoo para SubOrder "
        f"{suborder.sub_order_number} (sale.order ID={suborder.odoo_sale_id}, "
        f"nuevo status='{suborder.status}')..."
    )

    try:
        odoo = get_odoo_connection()
        if not odoo:
            logger.error("No se pudo conectar a Odoo")
            return False

        # Obtener el último comprobante aprobado (o el más reciente si no hay aprobado)
        latest_proof = (
            suborder.payments.filter(status='approved').first()
            or suborder.payments.order_by('-uploaded_at').first()
        )

        update_data = {
            'x_payment_status': _PAYMENT_STATUS_MAP.get(suborder.status, 'pagado'),
            'warehouse_id': _get_warehouse_id(odoo, provider.odoo_company_id),
        }

        if latest_proof:
            update_data.update(
                {
                    'x_payment_method': latest_proof.payment_method,
                    'x_payment_reference': latest_proof.operation_number or '',
                }
            )

        odoo.execute_kw(
            'sale.order',
            'write',
            [[[suborder.odoo_sale_id], update_data]],
        )

        logger.info(
            f"✅ Estado de pago actualizado en Odoo para "
            f"sale.order ID={suborder.odoo_sale_id}"
        )
        return True

    except Exception as e:
        logger.error(
            "❌ Error actualizando estado de pago en Odoo "
            f"para SubOrder {suborder.sub_order_number}: {e}"
        )
        return False