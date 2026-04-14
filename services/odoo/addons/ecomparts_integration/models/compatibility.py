# -*- coding: utf-8 -*-

from odoo import models, fields


class AutopartCompatibility(models.Model):
    _name = 'autopart.compatibility'
    _description = 'Compatibilidad de Autoparte por Vehículo'
    _order = 'product_tmpl_id, variant_id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
        index=True,
    )

    variant_id = fields.Many2one(
        'vehiculo.variante',
        string='Variante de Vehículo',
        required=True,
        ondelete='cascade',
        index=True,
    )

    marca_id = fields.Many2one(
        'vehiculo.marca',
        string='Marca',
        related='variant_id.modelo_id.marca_id',
        store=False,
        readonly=True,
    )

    modelo_id = fields.Many2one(
        'vehiculo.modelo',
        string='Modelo',
        related='variant_id.modelo_id',
        store=False,
        readonly=True,
    )

    motor_id = fields.Many2one(
        'vehiculo.motor',
        string='Motor',
        related='variant_id.motor_id',
        store=False,
        readonly=True,
    )

    fitment_notes = fields.Text(
        string='Notas de compatibilidad',
        help='Detalles de montaje o restricciones de compatibilidad (ej: solo 4x4, requiere kit adicional, etc.)'
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Permite desactivar una compatibilidad sin eliminarla'
    )

    _sql_constraints = [
        (
            'autopart_compatibility_unique',
            'unique(product_tmpl_id, variant_id)',
            'La compatibilidad entre este producto y esta variante de vehículo ya existe.'
        ),
    ]
