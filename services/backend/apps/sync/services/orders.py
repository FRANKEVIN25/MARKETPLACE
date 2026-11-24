"""
services/orders.py
==================
Lógica de sincronización de órdenes Django → Odoo (sale.order).

Funciones exportadas:
  - sync_suborder_to_odoo(suborder)
  - update_odoo_payment_status(suborder)
  - update_odoo_delivery_status(suborder)

Helpers internos:
  - get_odoo_connection(), _company_context(), _format_delivery_address()
  - _get_utm_source_id(), _get_provider_user_id(), _get_or_create_partner()

Constantes exportadas (para uso en otros módulos):
  - _PAYMENT_STATUS_MAP
  - _DELIVERY_STATUS_MAP

Nota: recalculate_order_status y update_customer_provider_stats son lógica
pura de Django y permanecen en apps/orders/signals.py.
"""
import logging

from django.utils import timezone
from apps.sync.odoo_connector import OdooConnector

logger = logging.getLogger(__name__)


def _single_created_id(result):
    """A create with a list of values returns [id] over Odoo JSON-RPC."""
    if isinstance(result, (list, tuple)):
        if len(result) != 1:
            raise ValueError('Se esperaba exactamente un registro creado en Odoo')
        result = result[0]
    if isinstance(result, bool) or not isinstance(result, int) or result <= 0:
        raise ValueError('Odoo no devolvio un identificador valido')
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Mapas de estado Django → campo Odoo
# ─────────────────────────────────────────────────────────────────────────────

# SubOrder.status → x_payment_status.
# x_payment_status en Odoo acepta: 'pendiente_revision', 'aprobado', 'rechazado'.
# False limpia el campo (cancelado: no es estado de pago válido).
_PAYMENT_STATUS_MAP = {
    'pago_en_revision': 'pendiente_revision',
    'pago_rechazado':   'rechazado',
    'confirmado':       'aprobado',
    'enviado':          'aprobado',
    'entregado':        'aprobado',
    'cancelado':        False,
}

# SubOrder.status → x_delivery_status en Odoo.
_DELIVERY_STATUS_MAP = {
    'pendiente_pago':   'pendiente',
    'pago_en_revision': 'pendiente',
    'pago_rechazado':   'pendiente',
    'confirmado':       'pendiente',
    'enviado':          'enviado',
    'entregado':        'recibido',
    'cancelado':        'cancelado',
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers privados
# ─────────────────────────────────────────────────────────────────────────────

def _company_context(company_id):
    """Construye contexto Odoo explícito para operaciones multi-company."""
    if not company_id:
        return {'tz': 'America/Lima'}
    return {
        'tz': 'America/Lima',
        'company_id': company_id,
        'force_company': company_id,
        'allowed_company_ids': [company_id],
    }


def get_odoo_connection():
    """
    Retorna un OdooConnector autenticado con las credenciales del settings.

    Returns:
        OdooConnector | None: Conector listo para usar, o None si falla la auth.
    """
    try:
        connector = OdooConnector()
        if connector.uid:
            return connector
        logger.error("Falló la autenticación con Odoo")
        return None
    except Exception as e:
        logger.error("Error conectando a Odoo: %s", e)
        return None


def _format_delivery_address(order) -> str:
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
    Retorna el ID del registro, o None si falla.
    """
    try:
        source_ids = odoo.execute_kw('utm.source', 'search', [[['name', '=', name]]])
        if source_ids:
            return source_ids[0]
        source_id = _single_created_id(odoo.execute_kw('utm.source', 'create', [[{'name': name}]]))
        logger.info("utm.source '%s' creado en Odoo: ID %s", name, source_id)
        return source_id
    except Exception as e:
        logger.warning("No se pudo obtener utm.source '%s': %s", name, e)
        return None


def _get_provider_user_id(odoo, provider):
    """Retorna el user_id de Odoo del proveedor."""
    try:
        return provider.odoo_user_id if provider.odoo_user_id else False
    except Exception:
        return False


def _get_or_create_partner(odoo: OdooConnector, customer):
    """Busca o crea un partner en Odoo para el customer dado.

    Estrategia:
      1. Buscar por email.
      2. Buscar por vat (DNI/RUC).
      3. Crear nuevo partner.

    Returns:
        int: partner_id en Odoo.
    Raises:
        Exception: si el create falla.
    """
    email = customer.user.email or ''

    try:
        partner_ids = []
        if email:
            partner_ids = odoo.execute_kw(
                'res.partner', 'search', [[['email', '=', email]]]
            )
        if partner_ids:
            logger.info("Partner encontrado por email: ID %s", partner_ids[0])
            return partner_ids[0]

        if customer.document_number:
            partner_ids = odoo.execute_kw(
                'res.partner', 'search', [[['vat', '=', customer.document_number]]]
            )
            if partner_ids:
                logger.info(
                    "Partner encontrado por vat (%s): ID %s",
                    customer.document_number, partner_ids[0],
                )
                return partner_ids[0]

        full_name = f"{customer.user.first_name} {customer.user.last_name}".strip()
        partner_data = {
            'name': full_name or customer.user.username,
            'email': email,
            'phone': customer.phone or '',
            'vat': customer.document_number or '',
            'customer_rank': 1,
        }
        partner_id = _single_created_id(odoo.execute_kw('res.partner', 'create', [[partner_data]]))
        logger.info("Partner creado: ID %s", partner_id)
        return partner_id

    except Exception as e:
        logger.error("Error obteniendo/creando partner en Odoo: %s", e)
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Funciones públicas
# ─────────────────────────────────────────────────────────────────────────────

def sync_suborder_to_odoo(suborder):
    """Crea la Sale Order en Odoo para una SubOrder de Django (estado draft).
    Debe llamarse DESPUÉS de que los OrderItems estén guardados.

    - Idempotente: si odoo_sale_id ya existe, retorna ese ID sin duplicar.
    - Incluye todos los campos del módulo orders_odoo.
    - Busca el partner por email y, como fallback, por vat (DNI/RUC).
    - Verifica duplicados por x_marketplace_suborder_id antes de crear.

    Returns:
        int: ID de la Sale Order en Odoo, o None si falla la conexión.
    Raises:
        ValueError: si no hay líneas de orden válidas para sincronizar.
    """
    from apps.orders.models import OrderItem

    if suborder.odoo_sale_id:
        logger.info(
            "SubOrder %s ya sincronizada (odoo_sale_id=%s)",
            suborder.sub_order_number, suborder.odoo_sale_id,
        )
        return suborder.odoo_sale_id

    logger.info("Sincronizando SubOrder %s con Odoo...", suborder.sub_order_number)

    try:
        odoo = get_odoo_connection()
        if not odoo:
            logger.error("No se pudo conectar a Odoo")
            return None

        order    = suborder.order # order es necesario? sub_order_number es con el que debe sincronizar...
        provider = suborder.provider
        customer = order.customer

        # 1. Partner
        partner_id = _get_or_create_partner(odoo, customer)

        # 2. Líneas de orden
        order_lines = []
        missing_odoo_id = []
        for item in OrderItem.objects.filter(sub_order=suborder):
            if not item.product.odoo_product_id:
                missing_odoo_id.append(item.product_name)
                continue
            order_lines.append((0, 0, {
                'product_id': item.product.odoo_product_id,
                'name': item.product_name,
                'product_uom_qty': item.quantity,
                'price_unit': float(item.unit_price),
            }))

        if missing_odoo_id:
            logger.warning(
                "Productos sin odoo_product_id omitidos: %s", missing_odoo_id
            )

        if not order_lines:
            raise ValueError(
                f"SubOrder {suborder.sub_order_number}: ningún item tiene "
                f"odoo_product_id. Productos afectados: {missing_odoo_id}"
            )

        # 3. Comprobante de pago más reciente (para campos x_payment_*)
        approved_proof = suborder.payments.filter(status='approved').first()
        latest_proof   = approved_proof or suborder.payments.order_by('-uploaded_at').first()

        source_id = _get_utm_source_id(odoo)

        sale_order_data = {
            'partner_id': partner_id,
            'company_id': provider.odoo_company_id,
            'order_line': order_lines,
            'client_order_ref': suborder.sub_order_number,
            'origin': order.order_number,
            'user_id': _get_provider_user_id(odoo, provider),
            'x_marketplace_order_id': order.order_number,  # inecesario, order es lo para logica marketplace
            'x_marketplace_suborder_id': suborder.sub_order_number,
            'x_delivery_method': order.delivery_method,
            'x_delivery_address': _format_delivery_address(order),
            'x_customer_notes': order.customer_notes or '',
            'x_delivery_status': _DELIVERY_STATUS_MAP.get(suborder.status, 'pendiente'),
            'x_payment_method': latest_proof.payment_method if latest_proof else False,
            'x_payment_reference': latest_proof.operation_number if latest_proof else '',
            'x_payment_amount_declared': float(latest_proof.amount) if latest_proof else 0.0,
            'x_payment_status': _PAYMENT_STATUS_MAP.get(suborder.status, 'pendiente_revision'),
            'x_last_sync_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            **({'source_id': source_id} if source_id else {}),
        }

        # 4. Idempotencia: buscar si ya existe en Odoo antes de crear
        existing_ids = odoo.execute_kw(
            'sale.order',
            'search',
            [[['x_marketplace_suborder_id', '=', suborder.sub_order_number]]],
        )
        if existing_ids:
            sale_order_id = existing_ids[0]
            logger.warning(
                "SubOrder %s ya existe en Odoo (ID %s). Usando existente.",
                suborder.sub_order_number, sale_order_id,
            )
        else:
            result = odoo.execute_kw(
                'sale.order',
                'create',
                [[sale_order_data]],
                {'context': _company_context(provider.odoo_company_id)},
            )
            # JSON-RPC create multi → [id]; create simple → id
            sale_order_id = _single_created_id(result)

        # 5. Guardar ID en Django
        suborder.odoo_sale_id = sale_order_id
        suborder.save(update_fields=['odoo_sale_id']) 

        logger.info(
            "Sale Order creada en Odoo: ID %s → SubOrder %s",
            sale_order_id, suborder.sub_order_number,
        )
        return sale_order_id

    except ValueError:
        raise
    except Exception as e:
        err = str(e).lower()
        # Idempotencia: UNIQUE constraint por x_marketplace_suborder_id disparado en Odoo
        if 'unique' in err or 'duplicate' in err:
            logger.warning(
                "SubOrder %s ya existe en Odoo (constraint). Buscando ID...",
                suborder.sub_order_number,
            )
            try:
                existing = odoo.execute_kw(
                    'sale.order',
                    'search',
                    [[['x_marketplace_suborder_id', '=', suborder.sub_order_number]]],
                )
                if existing:
                    suborder.odoo_sale_id = existing[0]
                    suborder.save(update_fields=['odoo_sale_id'])
                    logger.info(
                        "ID recuperado de Odoo: %s → SubOrder %s",
                        existing[0], suborder.sub_order_number,
                    )
                    return existing[0]
            except Exception as inner_e:
                logger.error("No se pudo recuperar ID de Odoo: %s", inner_e)

        logger.error(
            "Error sincronizando SubOrder %s: %s",
            suborder.sub_order_number, e,
        )
        return None


def update_odoo_payment_status(suborder) -> bool:
    """Actualiza el estado de pago en la sale.order de Odoo.
    Solo aplica a SubOrders que ya tienen odoo_sale_id.

    Returns:
        bool: True si la actualización fue exitosa.
    """
    if not suborder.odoo_sale_id:
        logger.warning(
            "update_odoo_payment_status: SubOrder %s no tiene odoo_sale_id, se omite.",
            suborder.sub_order_number,
        )
        return False

    logger.info(
        "Actualizando estado de pago en Odoo para SubOrder %s (sale.order ID=%s, status='%s')...",
        suborder.sub_order_number, suborder.odoo_sale_id, suborder.status,
    )

    try:
        odoo = get_odoo_connection()
        if not odoo:
            logger.error("No se pudo conectar a Odoo")
            return False

        latest_proof = (
            suborder.payments.filter(status='approved').first()
            or suborder.payments.order_by('-uploaded_at').first()
        )

        mapped_status = _PAYMENT_STATUS_MAP.get(suborder.status, 'pendiente_revision')
        update_data = {
            'x_last_sync_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        if mapped_status is not False:
            update_data['x_payment_status'] = mapped_status

        if latest_proof:
            update_data.update({
                'x_payment_method': latest_proof.payment_method,
                'x_payment_reference': latest_proof.operation_number or '',
            })

        odoo.execute_kw(
            'sale.order',
            'write',
            [[suborder.odoo_sale_id], update_data],
        )
        logger.info(
            "Estado de pago actualizado en Odoo: sale.order ID=%s", suborder.odoo_sale_id
        )
        return True

    except Exception as e:
        logger.error(
            "Error actualizando estado de pago en Odoo para SubOrder %s: %s",
            suborder.sub_order_number, e,
        )
        return False


def update_odoo_delivery_status(suborder) -> bool:
    """Actualiza el estado logístico en la sale.order de Odoo.

    Returns:
        bool: True si la actualización fue exitosa.
    """
    if not suborder.odoo_sale_id:
        logger.warning(
            "update_odoo_delivery_status: SubOrder %s no tiene odoo_sale_id, se omite.",
            suborder.sub_order_number,
        )
        return False

    logger.info(
        "Actualizando estado logístico en Odoo para SubOrder %s (sale.order ID=%s, status='%s')...",
        suborder.sub_order_number, suborder.odoo_sale_id, suborder.status,
    )

    try:
        odoo = get_odoo_connection()
        if not odoo:
            logger.error("No se pudo conectar a Odoo")
            return False

        update_data = {
            'x_delivery_status': _DELIVERY_STATUS_MAP.get(suborder.status, 'pendiente'),
            'x_last_sync_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        if suborder.tracking_number:    
            update_data['x_tracking_number'] = suborder.tracking_number
        if suborder.delivered_at:
            update_data['x_received_at'] = suborder.delivered_at.strftime('%Y-%m-%d %H:%M:%S')

        odoo.execute_kw('sale.order', 'write', [[suborder.odoo_sale_id], update_data])

        logger.info(
            "Estado logístico actualizado en Odoo: sale.order ID=%s", suborder.odoo_sale_id
        )
        return True

    except Exception as e:
        logger.error(
            "Error actualizando estado logístico en Odoo para SubOrder %s: %s",
            suborder.sub_order_number, e,
        )
        return False
