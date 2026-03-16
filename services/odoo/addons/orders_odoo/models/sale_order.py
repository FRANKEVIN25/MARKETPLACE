# orders_odoo/models/sale_order.py
"""
Extensión de sale.order para el marketplace ECOMPARTS — v4

Añade a cada sale.order:
  - Referencia cruzada con SubOrder de Django (x_marketplace_suborder_id).
  - Datos de entrega (método, dirección, notas del cliente).
  - Información de pago (método, N° operación, monto declarado, motivo de rechazo).
  - Estado de pago reducido: solo 3 valores (pendiente_revision, aprobado, rechazado).
  - Tracking de sincronización.

Diseño v4:
  - La sale.order se crea en estado DRAFT cuando el cliente sube el comprobante.
  - El proveedor revisa el comprobante directamente en Odoo (pestaña Marketplace).
  - "Rechazar pago"  → Odoo notifica a Django → PaymentProof.rejected + SubOrder.pendiente_pago
  - "Confirmar"      → Odoo notifica a Django → PaymentProof.approved + SubOrder.confirmado
  - Django es la fuente de verdad del estado de la SubOrder.
"""

import logging
import requests

from odoo import models, fields, api
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)


class SaleOrderMarketplace(models.Model):
    _inherit = 'sale.order'

    # Idempotencia: impide duplicados si Django envía la misma SubOrder dos veces.
    # NULL (campo vacío) no cuenta como duplicado → permite órdenes no-marketplace.
    _sql_constraints = [
        (
            'unique_marketplace_suborder_id',
            'UNIQUE(x_marketplace_suborder_id)',
            'Ya existe una sale.order para esta SubOrder del marketplace.',
        ),
    ]

    # ─────────────────────────────────────────────
    # 1. Referencia cruzada Django ↔ Odoo
    # ─────────────────────────────────────────────

    x_marketplace_order_id = fields.Char(
        string="Order Marketplace",
        help="Número de orden principal en Django (ej: ORD-2026-00001). "
             "Campo interno — no visible al proveedor en las vistas. "
             "Una Order puede generar varias sale.order (una por proveedor).",
        copy=False,
        index=True,
    )

    x_marketplace_suborder_id = fields.Char(
        string="SubOrder Marketplace",
        help="Número de SubOrder en Django (ej: ORD-2026-00001-A). "
             "Coincide con client_order_ref.",
        copy=False,
        index=True,
    )

    # ─────────────────────────────────────────────
    # 2. Datos de entrega
    # ─────────────────────────────────────────────

    x_delivery_method = fields.Selection(
        selection=[
            ('domicilio', 'Envío a Domicilio'),
            ('agencia',   'Envío a Agencia de Transporte'),
            ('tienda',    'Recojo en Tienda'),
        ],
        string="Método de Entrega",
        help="Método de entrega elegido por el cliente en el checkout.",
    )

    x_delivery_address = fields.Text(
        string="Dirección de Entrega",
        help="Dirección completa de envío tal como fue registrada en Django "
             "(calle, ciudad, provincia, departamento).",
    )

    x_customer_notes = fields.Text(
        string="Notas del Cliente",
        help="Instrucciones adicionales ingresadas por el cliente "
             "(ej: 'Portón azul, segundo piso.').",
    )

    # ─────────────────────────────────────────────
    # 3. Información de pago
    # ─────────────────────────────────────────────

    x_payment_method = fields.Selection(
        selection=[
            ('transferencia',          'Transferencia Bancaria'),
            ('yape',                   'Yape'),
            ('plin',                   'Plin'),
            ('efectivo_contraentrega', 'Efectivo Contraentrega'),
            ('efectivo_tienda',        'Efectivo en Tienda'),
        ],
        string="Método de Pago",
        help="Método de pago del comprobante subido por el cliente.",
    )

    x_payment_reference = fields.Char(
        string="N° Operación / Referencia",
        help="Número de operación del comprobante de pago subido por el cliente.",
        copy=False,
    )

    x_payment_amount_declared = fields.Monetary(
        string="Monto Declarado",
        currency_field='currency_id',
        help="Monto indicado por el cliente en el comprobante de pago.",
    )

    # ─────────────────────────────────────────────
    # 4. Estado de pago del Marketplace (v4 — reducido)
    #
    # NO duplica los estados de sale.order.state.
    # Solo refleja el estado de la revisión del comprobante:
    #   pendiente_revision → comprobante subido, proveedor aún no revisa
    #   aprobado           → proveedor confirmó cotización (pago implícitamente OK)
    #   rechazado          → proveedor rechazó el comprobante
    #
    # Siempre readonly para el proveedor; se actualiza vía las acciones del módulo.
    # ─────────────────────────────────────────────

    x_payment_status = fields.Selection(
        selection=[
            ('pendiente_revision', 'Pendiente de Revisión'),
            ('aprobado',           'Pago Aprobado'),
            ('rechazado',          'Pago Rechazado'),
        ],
        string="Estado de Pago Marketplace",
        help="Estado del comprobante de pago reviseado por el proveedor. "
             "Se actualiza automáticamente al aprobar/rechazar.",
        index=True,
    )

    x_payment_rejection_reason = fields.Text(
        string="Motivo de Rechazo de Pago",
        help="Razón por la que el proveedor rechazó el comprobante. "
             "El cliente recibirá este motivo y podrá subir un nuevo comprobante.",
    )

    # ─────────────────────────────────────────────
    # 5. Tracking de sincronización
    # ─────────────────────────────────────────────

    x_last_sync_at = fields.Datetime(
        string="Última sincronización",
        help="Fecha/hora de la última actualización recibida desde Django vía XML-RPC.",
        copy=False,
        readonly=True,
    )

    x_tracking_number = fields.Char(
        string="Número de Seguimiento (Envío)",
        help="Número de tracking del envío (courier / agencia).",
        copy=False,
    )

    x_delivery_status = fields.Selection(
        selection=[
            ('pendiente', 'Pendiente'),
            ('enviado',   'Enviado'),
            ('recibido',  'Recibido'),
            ('cancelado', 'Cancelado'),
        ],
        string="Estado de Entrega Marketplace",
        help="Estado logístico informado por Django para la SubOrder del marketplace. "
             "'Enviado' indica despacho confirmado en Odoo; 'Recibido' indica "
             "confirmación de recepción por el cliente.",
        index=True,
        copy=False,
    )

    x_received_at = fields.Datetime(
        string="Fecha de Recepción",
        help="Fecha/hora en la que el cliente confirmó la recepción en el marketplace.",
        copy=False,
        readonly=True,
    )

    # ─────────────────────────────────────────────
    # 6. Acciones del proveedor
    # ─────────────────────────────────────────────

    def action_confirm(self):
        """
        Override del botón 'Confirmar' de Odoo.

        Flujo v4:
          1. Ejecuta la confirmación estándar de Odoo (cotización → sale.order).
          2. Marca x_payment_status = 'aprobado'.
          3. Notifica a Django para aprobar el PaymentProof y poner SubOrder = 'confirmado'.

        Solo notifica a Django si la sale.order pertenece al marketplace
        (x_marketplace_suborder_id presente).
        """
        result = super().action_confirm()

        for order in self:
            if order.x_marketplace_suborder_id:
                order.x_payment_status = 'aprobado'
                success = order._notify_django_payment_action('approve')
                if not success:
                    logger.warning(
                        f"⚠️  No se pudo notificar a Django (approve) "
                        f"para SubOrder {order.x_marketplace_suborder_id}. "
                        f"La sale.order queda confirmada en Odoo pero Django debe "
                        f"actualizarse manualmente."
                    )

        return result

    def action_reject_payment(self):
        """
        Abre el wizard para capturar el motivo de rechazo del comprobante.
        Solo disponible cuando state = 'draft' y es una orden del marketplace.
        """
        self.ensure_one()
        if not self.x_marketplace_suborder_id:
            raise UserError(
                "Este pedido no está vinculado a una SubOrder del marketplace."
            )
        if self.state != 'draft':
            raise UserError(
                "Solo se puede rechazar el pago en cotizaciones (estado draft). "
                "Si ya confirmaste el pedido, contacta a soporte."
            )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rechazar Pago',
            'res_model': 'marketplace.reject.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sale_order_id': self.id},
        }

    def action_mark_received(self):
        """Marca manualmente la SubOrder del marketplace como recibida."""
        self.ensure_one()

        if not self.x_marketplace_suborder_id:
            raise UserError(
                "Este pedido no está vinculado a una SubOrder del marketplace."
            )

        if self.x_delivery_status not in ['enviado', 'recibido']:
            raise UserError(
                "Solo se puede marcar como recibido un pedido que ya fue enviado."
            )

        success = self._notify_django_delivery_received()
        if not success:
            raise UserError(
                "No se pudo notificar a Django para marcar la SubOrder como recibida. "
                "Revisa la conectividad e inténtalo nuevamente."
            )

        now = fields.Datetime.now()
        self.write({
            'x_delivery_status': 'recibido',
            'x_received_at': self.x_received_at or now,
            'x_last_sync_at': now,
        })

        return True

    # ─────────────────────────────────────────────
    # 7. Comunicación Django ← Odoo
    # ─────────────────────────────────────────────

    def _notify_django_payment_action(self, action, rejection_reason=''):
        """
        Llama al endpoint Django /api/orders/odoo-webhook/review-payment/
        para aprobar o rechazar el pago de una SubOrder.

        Parámetros de configuración (ir.config_parameter):
          ecomparts.django_api_url      — URL base de Django (ej: http://backend:8000)
          ecomparts.django_webhook_token — Token compartido (debe coincidir con
                                           settings.ODOO_WEBHOOK_TOKEN en Django)

        Returns:
            bool: True si Django respondió con éxito, False en caso de error.
        """
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        django_url = ICP.get_param('ecomparts.django_api_url', default='http://backend:8000')
        token = ICP.get_param('ecomparts.django_webhook_token', default='change-me-in-production')

        endpoint = f"{django_url.rstrip('/')}/api/v1/orders/odoo-webhook/review-payment/"
        payload = {
            'token': token,
            'suborder_number': self.x_marketplace_suborder_id,
            'action': action,
            'rejection_reason': rejection_reason,
        }

        try:
            resp = requests.post(endpoint, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info(
                    f"✅ Django notificado [{action}] para "
                    f"SubOrder {self.x_marketplace_suborder_id}"
                )
                return True
            else:
                logger.error(
                    f"❌ Django respondió {resp.status_code} para "
                    f"SubOrder {self.x_marketplace_suborder_id}: {resp.text[:300]}"
                )
                return False
        except requests.exceptions.RequestException as e:
            logger.error(
                f"❌ Error de conexión notificando a Django para "
                f"SubOrder {self.x_marketplace_suborder_id}: {e}"
            )
            return False

    def _notify_django_delivery_received(self):
        """Notifica a Django que la SubOrder fue marcada como recibida desde Odoo."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        django_url = ICP.get_param('ecomparts.django_api_url', default='http://backend:8000')
        token = ICP.get_param('ecomparts.django_webhook_token', default='change-me-in-production')

        endpoint = f"{django_url.rstrip('/')}/api/v1/orders/odoo-webhook/mark-received/"
        payload = {
            'token': token,
            'suborder_number': self.x_marketplace_suborder_id,
        }

        try:
            resp = requests.post(endpoint, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info(
                    f"✅ Django notificado [mark_received] para "
                    f"SubOrder {self.x_marketplace_suborder_id}"
                )
                return True

            logger.error(
                f"❌ Django respondió {resp.status_code} para "
                f"SubOrder {self.x_marketplace_suborder_id}: {resp.text[:300]}"
            )
            return False
        except requests.exceptions.RequestException as e:
            logger.error(
                f"❌ Error de conexión notificando recepción a Django para "
                f"SubOrder {self.x_marketplace_suborder_id}: {e}"
            )
            return False



