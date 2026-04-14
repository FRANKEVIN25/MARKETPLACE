# odoo_django_webhooks/models/stock_picking.py
import logging
import threading

import requests
from odoo import models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_webhook_config(self):
        icp = self.env['ir.config_parameter'].sudo()
        base_url = icp.get_param('ecomparts.django_api_url', default='http://backend:8000')
        token = icp.get_param(
            'ecomparts.django_webhook_token',
            default='dev-webhook-secret-token-2026',
        )
        return base_url.rstrip('/'), token

    def _get_related_sale_order(self):
        self.ensure_one()

        sale_order = False

        if 'sale_id' in self._fields and self.sale_id:
            sale_order = self.sale_id
        elif self.origin:
            sale_order = self.env['sale.order'].search([('name', '=', self.origin)], limit=1)

        return sale_order

    def _send_delivery_webhook_async(
        self,
        webhook_url,
        webhook_token,
        sale_order_id,
        picking_id,
        picking_name,
        state,
        picking_type_code,
    ):
        """Enviar webhook de despacho a Django en segundo plano."""
        payload = {
            'token': webhook_token,
            'sale_order_id': sale_order_id,
            'picking_id': picking_id,
            'picking_name': picking_name,
            'state': state,
            'picking_type_code': picking_type_code,
        }

        try:
            _logger.info(
                "📤 Enviando webhook de despacho a Django: sale_order_id=%s, picking=%s, state=%s",
                sale_order_id,
                picking_name or picking_id,
                state,
            )
            response = requests.post(webhook_url, json=payload, timeout=3)
            if response.status_code == 200:
                _logger.info(" Webhook de despacho enviado: %s", response.json())
            else:
                _logger.warning(
                    " Webhook de despacho respondió con: %s - %s",
                    response.status_code,
                    response.text[:300],
                )
        except requests.Timeout:
            _logger.warning("⏱️ Webhook de despacho timeout (Django tardó >3s)")
        except Exception as e:
            _logger.error("❌ Error webhook de despacho: %s", str(e))

    def _send_delivery_webhook_to_django(self):
        webhook_base_url, webhook_token = self._get_webhook_config()
        webhook_url = f'{webhook_base_url}/api/v1/orders/odoo-webhook/delivery-update/'

        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue

            sale_order = picking._get_related_sale_order()
            if not sale_order:
                _logger.info(
                    "ℹ Picking %s sin sale.order asociada; no se envía webhook",
                    picking.name,
                )
                continue

            if not getattr(sale_order, 'x_marketplace_suborder_id', False):
                _logger.info(
                    "ℹ Sale Order %s no pertenece al marketplace; se omite webhook de despacho",
                    sale_order.name,
                )
                continue

            thread = threading.Thread(
                target=picking._send_delivery_webhook_async,
                args=(
                    webhook_url,
                    webhook_token,
                    sale_order.id,
                    picking.id,
                    picking.name,
                    picking.state,
                    picking.picking_type_code,
                ),
            )
            thread.daemon = True
            thread.start()

    def _action_done(self):
        result = super()._action_done()
        # In some Odoo versions _action_done returns True instead of a recordset;
        # filter self (which is always a recordset) to find completed outgoing pickings.
        pickings_to_notify = self if isinstance(result, bool) else result
        done_pickings = pickings_to_notify.filtered(
            lambda picking: picking.state == 'done' and picking.picking_type_code == 'outgoing'
        )
        done_pickings._send_delivery_webhook_to_django()
        return result
