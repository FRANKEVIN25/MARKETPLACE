{
    'name': 'Orders Odoo — ECOMPARTS Marketplace',
    'version': '18.0.4.0.0',
    'category': 'Sales',
    'summary': 'Extiende sale.order con datos del marketplace ECOMPARTS (entrega, pago, estado SubOrder)',
    'description': """
        Módulo personalizado que extiende sale.order con:
        - Referencia cruzada con SubOrder de Django (visible al proveedor).
        - Datos de entrega del marketplace (método, dirección, notas).
        - Comprobante de pago (método, N° operación, monto, motivo de rechazo).
        - Estado de pago reducido (pendiente_revision, aprobado, rechazado). v4
        - Botón "Rechazar pago" + wizard de motivo de rechazo.
        - Override de action_confirm para notificar a Django (pago aprobado).
        - Origen del pedido via source_id (utm.source = ECOMPARTS Marketplace).
        - Django es la fuente de verdad; la sale.order nunca tiene estados duplicados.
    """,
    'author': 'ECOMPARTS',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/config_parameters.xml',
        'views/reject_payment_wizard.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
