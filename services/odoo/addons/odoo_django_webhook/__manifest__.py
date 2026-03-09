# -*- coding: utf-8 -*-
{
    'name': 'Odoo Django Webhook',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Send webhooks to Django when Sale Order status changes',
    'description': """
        Automatically sends webhooks to Django backend when:
        - Sale Order is confirmed
        - Sale Order is cancelled
        - Sale Order is delivered
        
        This enables real-time synchronization between Odoo and Django.
    """,
    'author': 'ECOMPARTS',
    'depends': ['sale', 'sale_management'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
