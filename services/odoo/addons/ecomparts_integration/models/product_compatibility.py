# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CompatibilidadProductoVehiculo(models.Model):
    """
    Tabla intermedia para compatibilidad Producto ↔ Vehículo
    """
    _name = 'producto.vehiculo.compatibilidad'
    _description = 'Compatibilidad Producto - Vehículo'
    _order = 'producto_id, variante_id'
    _rec_name = 'nombre'

    # ============================================
    # CAMPOS PRINCIPALES
    # ============================================

    producto_id = fields.Many2one(
        comodel_name='product.template',
        string='Producto',
        required=True,
        ondelete='cascade',
        index=True
    )

    variante_id = fields.Many2one(
        comodel_name='vehiculo.variante',
        string='Variante de Vehículo',
        required=True,
        ondelete='cascade',
        index=True
    )

    notas = fields.Text(
        string='Notas',
        help='Observaciones de compatibilidad (adaptadores, versiones, etc.)'
    )

    # ============================================
    # CAMPOS RELACIONADOS (FILTROS RÁPIDOS)
    # ============================================

    marca_id = fields.Many2one(
        related='variante_id.modelo_id.marca_id',
        string='Marca',
        store=True,
        index=True
    )

    modelo_id = fields.Many2one(
        related='variante_id.modelo_id',
        string='Modelo',
        store=True,
        index=True
    )

    anio_desde = fields.Integer(
        related='variante_id.anio_desde',
        string='Año Desde',
        store=True,
        index=True
    )

    anio_hasta = fields.Integer(
        related='variante_id.anio_hasta',
        string='Año Hasta',
        store=True,
        index=True
    )

    # ============================================
    # CAMPOS COMPUTADOS
    # ============================================

    nombre = fields.Char(
        string='Nombre',
        compute='_compute_nombre',
        store=True,
        index=True
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

    # ============================================
    # CONSTRAINTS
    # ============================================

    _sql_constraints = [
        (
            'producto_variante_unique',
            'unique(producto_id, variante_id)',
            'Esta compatibilidad ya existe'
        ),
    ]

    # ============================================
    # MÉTODOS COMPUTADOS
    # ============================================

    @api.depends('producto_id.name', 'variante_id.nombre')
    def _compute_nombre(self):
        for r in self:
            if r.producto_id and r.variante_id:
                r.nombre = f"{r.producto_id.name} → {r.variante_id.nombre}"
            else:
                r.nombre = 'Nueva compatibilidad'

    # ============================================
    # VALIDACIONES
    # ============================================

    @api.constrains('variante_id')
    def _check_anios_variante(self):
        for r in self:
            if not r.variante_id.anio_desde:
                raise ValidationError(
                    _('La variante debe tener un año de inicio válido')
                )

    # ============================================
    # MÉTODOS PARA DJANGO / API
    # ============================================

    def to_django_dict(self):
        self.ensure_one()
        return {
            'producto_id': self.producto_id.id,
            'variante_id': self.variante_id.id,
            'marca': self.marca_id.nombre if self.marca_id else '',
            'modelo': self.modelo_id.nombre if self.modelo_id else '',
            'anio_desde': self.anio_desde,
            'anio_hasta': self.anio_hasta,
            'notas': self.notas or '',
        }

    @api.model
    def buscar_productos_por_vehiculo(
        self,
        marca_id=None,
        modelo_id=None,
        variante_id=None,
        anio=None
    ):
        domain = []

        if marca_id:
            domain.append(('marca_id', '=', marca_id))
        if modelo_id:
            domain.append(('modelo_id', '=', modelo_id))
        if variante_id:
            domain.append(('variante_id', '=', variante_id))
        if anio:
            domain.extend([
                ('anio_desde', '<=', anio),
                '|',
                ('anio_hasta', '>=', anio),
                ('anio_hasta', '=', False)
            ])

        compat = self.search(domain)
        productos_especificos = compat.mapped('producto_id')

        productos_universales = self.env['product.template'].search([
            ('es_universal', '=', True)
        ])

        return productos_especificos | productos_universales
