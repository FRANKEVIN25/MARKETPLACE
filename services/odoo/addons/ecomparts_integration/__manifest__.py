# -*- coding: utf-8 -*-
{
    'name': 'AutoParts Integration - MyAutoCore',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Integración de vehículos y compatibilidad de autopartes para marketplace',
    'description': """
        AutoParts Integration Module
        ============================
        
        Funcionalidades:
        ----------------
        * Gestión de marcas, modelos y variantes de vehículos
        * Compatibilidad producto-vehículo
        * Campos adicionales en productos (lado, calidad)
        * Sincronización bidireccional con Django REST API
        * Protección de categorías de marketplace
        
        Requisitos:
        -----------
        * Odoo 18.0+
        * Python 3.10+
        * Módulos base: product, stock
    """,
    'author': 'Ecomparts Team',
    'website': 'https://ecomparts.pe',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        
        # Data — categorías primero (productos las referencian),
        # luego variantes de vehículos
        'data/categories_seed.xml',
        #'data/vehicle_variants_seed.xml',
        
        # Views
        'views/actions.xml',
        'views/vehicle_views.xml',
        'views/product_views.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'python': '>=3.10',
}