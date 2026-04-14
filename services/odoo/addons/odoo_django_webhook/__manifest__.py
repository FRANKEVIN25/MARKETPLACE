# -*- coding: utf-8 -*-
{
    'name': 'Odoo Django Webhook',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Send webhooks to Django for sales and deliveries',
    'description': """
        Automatically sends webhooks to Django backend when:
        - Sale Order is confirmed
        - Sale Order is cancelled
        - Stock Picking is validated (delivery dispatched)
        
        This enables real-time synchronization between Odoo and Django.
    """,
    'author': 'ECOMPARTS',
    'license': 'LGPL-3',
    'depends': ['sale', 'sale_management', 'stock'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
