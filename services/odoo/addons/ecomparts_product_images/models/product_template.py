# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ecomparts_image_ids = fields.One2many(
        'ecomparts.product.image',
        'product_tmpl_id',
        string='Imágenes del Marketplace',
        help='Imágenes adicionales que se muestran en el marketplace ECOMPARTS'
    )
    ecomparts_image_count = fields.Integer(
        string='Nº Imágenes',
        compute='_compute_image_count'
    )

    def _compute_image_count(self):
        for record in self:
            record.ecomparts_image_count = len(record.ecomparts_image_ids)
