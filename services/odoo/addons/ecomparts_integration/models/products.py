# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_image_version = fields.Char(
        string='Image Version',
        copy=False,
        index=True,
        help=(
            'Se actualiza únicamente cuando image_1920 cambia. '
            'Señal liviana para sync diferencial de imágenes en Django; '
            'evita falsos positivos por cambios de precio, descripción u otros campos.'
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('image_1920'):
                vals['x_image_version'] = fields.Datetime.now().strftime('%Y%m%d%H%M%S%f')
        return super().create(vals_list)

    def write(self, vals):
        if 'image_1920' in vals:
            vals['x_image_version'] = fields.Datetime.now().strftime('%Y%m%d%H%M%S%f')
        return super().write(vals)

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


class ProductCategory(models.Model):
    _inherit = 'product.category'

    active = fields.Boolean(
        string='Activo',
        default=True,
        index=True,
        help='Permite archivar categorías sincronizadas desde Django.',
    )

    django_sync_key = fields.Char(
        string='Sync Key Django',
        index=True,
        copy=False,
        help='Clave estable de sincronización desde Django.',
    )

    _sql_constraints = [
        (
            'product_category_django_sync_key_unique',
            'unique(django_sync_key)',
            'La sync key de Django debe ser única por categoría.',
        ),
    ]
