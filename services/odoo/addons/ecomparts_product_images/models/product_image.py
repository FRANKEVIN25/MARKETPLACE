# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductImage(models.Model):
    _name = 'ecomparts.product.image'
    _description = 'Imagen adicional del producto para el Marketplace'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True, default='Imagen')
    sequence = fields.Integer(string='Orden', default=10)
    image = fields.Image(
        string='Imagen',
        max_width=1920,
        max_height=1920,
        required=True
    )
    image_url = fields.Char(
        string='URL Cloudinary',
        help='URL de la imagen sincronizada en Cloudinary'
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        ondelete='cascade',
        index=True
    )
