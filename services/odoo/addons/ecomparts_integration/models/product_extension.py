# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ============================================
    # CAMPOS ESPECÍFICOS DE AUTOPARTES
    # ============================================

    lado = fields.Selection(
        [
            ('rh', 'Derecho'),
            ('lh', 'Izquierdo'),
            ('ambos', 'Ambos'),
            ('sin_lado', 'Sin lado'),
        ],
        string='Lado',
        default='sin_lado'
    )

    calidad = fields.Selection(
        [
            ('original', 'Original'),
            ('genuine', 'Genuino'),
            ('oem', 'OEM'),
            ('alternativo', 'alternativo'),
            ('economy', 'Económico'),
        ],
        string='Calidad',
        default='original'
    )

    codigo_fabricacion = fields.Char(
        string='Código de Fabricación'
    )

    # ============================================
    # COMPATIBILIDAD VEHICULAR
    # ============================================

    compatibilidad_vehiculo_ids = fields.One2many(
        comodel_name='producto.vehiculo.compatibilidad',
        inverse_name='producto_id',
        string='Compatibilidad Vehicular'
    )

    cantidad_vehiculos_compatibles = fields.Integer(
        string='Vehículos Compatibles',
        compute='_compute_cantidad_vehiculos',
        store=True
    )

    es_universal = fields.Boolean(
        string='¿Producto Universal?',
        default=False
    )

    # ============================================
    # SINCRONIZACIÓN DJANGO
    # ============================================

    django_external_id = fields.Char(
        string='ID Externo Django',
        copy=False,
        readonly=True,
        index=True
    )

    django_short_id = fields.Char(
        string='ID Corto Django',
        copy=False,
        readonly=True,
        index=True
    )

    # ============================================
    # MÉTODOS COMPUTADOS
    # ============================================

    @api.depends('compatibilidad_vehiculo_ids')
    def _compute_cantidad_vehiculos(self):
        for p in self:
            p.cantidad_vehiculos_compatibles = len(p.compatibilidad_vehiculo_ids)

    # ============================================
    # ACCIONES
    # ============================================

    def action_ver_vehiculos_compatibles(self):
        self.ensure_one()
        return {
            'name': f'Vehículos compatibles: {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'producto.vehiculo.compatibilidad',
            'view_mode': 'tree,form',
            'domain': [('producto_id', '=', self.id)],
            'context': {'default_producto_id': self.id},
        }

    # ============================================
    # API / DJANGO
    # ============================================

    def to_django_dict(self):
        self.ensure_one()
        return {
            'nombre': self.name,
            'sku': self.default_code or '',
            'precio': float(self.list_price),
            'descripcion': self.description_sale or '',
            'tipo_producto': self.type,
            'categoria_id': self.categ_id.id if self.categ_id else False,
            'codigo_fabricacion': self.codigo_fabricacion or '',
            'lado': self.lado,
            'calidad': self.calidad,
            'odoo_template_id': self.id,
            'odoo_product_id': self.product_variant_id.id if self.product_variant_id else False,
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    django_external_id = fields.Char(
        related='product_tmpl_id.django_external_id',
        readonly=True
    )

    django_short_id = fields.Char(
        related='product_tmpl_id.django_short_id',
        readonly=True
    )
