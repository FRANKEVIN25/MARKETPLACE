# -*- coding: utf-8 -*-
import requests
import logging
import threading
from odoo import models, api

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    def _send_webhook_async(self, sale_order_id, state, invoice_status):
        """
        Enviar webhook en un thread separado para no bloquear Odoo
        """
        webhook_url = 'http://backend:8000/api/v1/orders/odoo-webhook/sale-order-update/'
        webhook_token = 'dev-webhook-secret-token-2026'
        
        payload = {
            'token': webhook_token,
            'sale_order_id': sale_order_id,
            'state': state,
            'invoice_status': invoice_status,
        }
        
        try:
            _logger.info(f"📤 Enviando webhook a Django: Sale Order {sale_order_id}, Estado: {state}")
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=3  # Timeout corto de 3 segundos
            )
            
            if response.status_code == 200:
                _logger.info(f"✅ Webhook enviado: {response.json()}")
            else:
                _logger.warning(f"⚠️ Webhook respondió con: {response.status_code}")
                
        except requests.Timeout:
            _logger.warning(f"⏱️ Webhook timeout (Django tardó >3s)")
        except Exception as e:
            _logger.error(f"❌ Error webhook: {str(e)}")
    
    def _send_webhook_to_django(self):
        """
        Lanzar webhook en thread separado
        """
        # Ejecutar en thread separado para no bloquear
        thread = threading.Thread(
            target=self._send_webhook_async,
            args=(self.id, self.state, self.invoice_status)
        )
        thread.daemon = True
        thread.start()
    
    def action_confirm(self):
        """
        Override: Enviar webhook cuando se confirma la orden
        """
        result = super(SaleOrder, self).action_confirm()
        
        if self.state == 'sale':
            self._send_webhook_to_django()
        
        return result
    
    def action_cancel(self):
        """
        Override: Enviar webhook cuando se cancela la orden
        """
        result = super(SaleOrder, self).action_cancel()
        self._send_webhook_to_django()
        return result
