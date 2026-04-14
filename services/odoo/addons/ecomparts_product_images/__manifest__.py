# -*- coding: utf-8 -*-
{
    'name': 'ECOMPARTS - Galería de Imágenes de Productos',
    'version': '18.0.2.0.0',
    'category': 'Inventory',
    'summary': 'Galería de imágenes adicionales para productos del marketplace',
    'description': """
        Permite al vendor subir múltiples imágenes por producto:
        - Imagen principal (nativa de Odoo)
        - Galería adicional con orden personalizable
        - Sincronización automática con Cloudinary
        - Vista profesional tipo Amazon/Shopify
    """,
    'author': 'ECOMPARTS PERÚ',
    'license': 'LGPL-3',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
