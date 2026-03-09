{
    'name': 'Orders Odoo — ECOMPARTS Marketplace',
    'version': '18.0.2.0.0',
    'category': 'Sales',
    'summary': 'Extiende sale.order con datos del marketplace ECOMPARTS (entrega, pago, estado SubOrder)',
    'description': """
        Módulo personalizado que extiende sale.order con:
        - Referencia cruzada con SubOrder de Django (visible al proveedor).
        - Datos de entrega del marketplace (método, dirección, notas).
        - Comprobante de pago (método, N° operación, monto, motivo de rechazo).
        - Estado del pedido: espejo exacto de SubOrder.status en Django (7 estados).
        - Origen del pedido via source_id (utm.source = ECOMPARTS Marketplace).
        - Django es la fuente de verdad; estados sincronizados vía XML-RPC/Celery.
    """,
    'author': 'ECOMPARTS',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
