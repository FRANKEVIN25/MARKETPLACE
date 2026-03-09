# orders_odoo/models/sale_order.py
"""
Extensión de sale.order para el marketplace ECOMPARTS.

Añade a cada sale.order:
  - Referencia cruzada con SubOrder de Django (x_marketplace_suborder_id).
  - Datos de entrega (método, dirección, notas del cliente).
  - Información de pago (método, N° operación, monto declarado, motivo de rechazo).
  - Estado del pedido: espejo exacto de SubOrder.status en Django (7 estados).
  - Tracking de sincronización.

Diseño: Django es la fuente de verdad (source of truth).
Los estados y datos de Odoo se sincronizan desde Django vía XML-RPC (Celery).
El proveedor opera en Odoo; Django refleja los cambios resultantes.
"""

from odoo import models, fields


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
        help="Método de pago del comprobante aprobado. "
             "Se sincroniza desde Django al confirmar el pago.",
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
    # 4. Estado del pedido (espejo exacto de SubOrder.status en Django)
    #
    # Django es la fuente de verdad. Este campo se sincroniza vía XML-RPC
    # cada vez que SubOrder.status cambia en Django.
    #
    # Ciclo lineal:
    #   pendiente_pago → pago_en_revision → pagado → confirmado → enviado → entregado
    #                         ↑ rechazo ──────────────┘
    #   cancelado (en cualquier etapa hasta 'confirmado')
    # ─────────────────────────────────────────────

    x_payment_status = fields.Selection(
        selection=[
            ('pendiente_pago',   'Pendiente de Pago'),
            ('pago_en_revision', 'Pago en Revisión'),
            ('pagado',           'Pagado'),
            ('confirmado',       'Confirmado'),
            ('enviado',          'Enviado'),
            ('entregado',        'Entregado'),
            ('cancelado',        'Cancelado'),
        ],
        string="Estado del Pedido",
        default='pendiente_pago',
        help="Estado sincronizado desde Django (SubOrder.status). "
             "Django es la fuente de verdad — no editar manualmente.",
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
