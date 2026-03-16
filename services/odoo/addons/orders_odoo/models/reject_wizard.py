# orders_odoo/models/reject_wizard.py
"""
Wizard para capturar el motivo de rechazo del comprobante de pago.

Se invoca desde el botón "Rechazar pago" de la pestaña Marketplace
de una sale.order en estado draft.

Flujo:
  1. Proveedor hace clic en "Rechazar pago".
  2. Se abre este wizard (ventana modal).
  3. Proveedor escribe el motivo.
  4. Al confirmar:
       - Se guarda x_payment_rejection_reason en la sale.order.
       - Se pone x_payment_status = 'rechazado'.
       - Se llama a Django para marcar PaymentProof.rejected y
         volver SubOrder a 'pendiente_pago'.
"""

import logging
from odoo import models, fields
from odoo.exceptions import ValidationError

logger = logging.getLogger(__name__)


class MarketplaceRejectPaymentWizard(models.TransientModel):
    _name = 'marketplace.reject.payment.wizard'
    _description = 'Rechazar Comprobante de Pago — ECOMPARTS Marketplace'

    sale_order_id = fields.Many2one(
        'sale.order',
        string="Pedido",
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    rejection_reason = fields.Text(
        string="Motivo de Rechazo",
        required=True,
        help="Explica al cliente qué debe corregir en el comprobante "
             "(ej: 'El monto es incorrecto', 'El número de operación no coincide').",
    )

    def action_confirm_reject(self):
        """
        Confirma el rechazo:
          1. Guarda el motivo en la sale.order.
          2. Pone x_payment_status = 'rechazado'.
          3. Notifica a Django para marcar PaymentProof.rejected y
             volver SubOrder a 'pendiente_pago'.
        """
        self.ensure_one()

        if not self.rejection_reason or not self.rejection_reason.strip():
            raise ValidationError("El motivo de rechazo no puede estar vacío.")

        order = self.sale_order_id
        order.x_payment_rejection_reason = self.rejection_reason.strip()
        order.x_payment_status = 'rechazado'

        success = order._notify_django_payment_action(
            action='reject',
            rejection_reason=self.rejection_reason.strip(),
        )

        if not success:
            logger.warning(
                f"⚠️  No se pudo notificar a Django (reject) para "
                f"SubOrder {order.x_marketplace_suborder_id}. "
                f"El rechazo queda registrado en Odoo pero Django debe "
                f"actualizarse manualmente."
            )

        return {'type': 'ir.actions.act_window_close'}
