# -*- coding: utf-8 -*-

from odoo import models, fields


class EcompProductImage(models.Model):
    _name = 'ecomp.product.image'
    _description = 'Imagen de Producto para Marketplace'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Imagen')
    sequence = fields.Integer(default=10)
    image_1920 = fields.Image(string='Imagen', max_width=1920, max_height=1920)
    image_128 = fields.Image(
        string='Miniatura',
        related='image_1920',
        max_width=128,
        max_height=128,
        store=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
        index=True,
    )
