# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    autopart_oem_code = fields.Char(
        string='Código OEM',
        help='Código OEM del fabricante para esta autoparte'
    )
    # falta asignar un default
    autopart_side = fields.Selection(
        selection=[
            ('left', 'Izquierda'),
            ('right', 'Derecha'),
            ('front', 'Delantera'),
            ('rear', 'Posterior'),
            ('both', 'Ambos lados'),
            ('na', 'No aplica'),
        ],
        string='Lado del vehículo',
        help='Lado del vehículo al que aplica la autoparte'
    )
    # falta asignar un default
    autopart_quality = fields.Selection(
        selection=[
            ('original', 'Original'),
            ('oem', 'OEM'),
            ('aftermarket_premium', 'Alternativo Premium'),
            ('aftermarket_standard', 'Alternativo Estándar'),
        ],
        string='Calidad del repuesto',
    )

    autopart_notes = fields.Text(
        string='Notas técnicas de autoparte',
        help='Notas de instalación o consideraciones especiales para esta autoparte'
    )

    autopart_universal = fields.Boolean(
        string='Universal',
        help='Marcar si la autoparte es universal y no depende de un vehículo específico'
    )

    compatibility_ids = fields.One2many(
        'autopart.compatibility',
        'product_tmpl_id',
        string='Compatibilidades de vehículos'
    )
