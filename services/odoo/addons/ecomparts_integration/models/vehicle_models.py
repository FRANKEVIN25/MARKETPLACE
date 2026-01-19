# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import uuid


class MarcaVehiculo(models.Model):
    _name = 'vehiculo.marca'
    _description = 'Marca de Vehículo'
    _order = 'nombre'
    _rec_name = 'nombre'

    nombre = fields.Char(
        string='Nombre',
        required=True,
        index=True
    )
    slug = fields.Char(
        string='Slug',
        required=True,
        index=True
    )
    activo = fields.Boolean(
        string='Activo',
        default=True,
        index=True
    )

    django_external_id = fields.Char(
        string='ID Externo Django',
        index=True,
        copy=False,
        readonly=True
    )

    modelo_ids = fields.One2many(
        'vehiculo.modelo',
        'marca_id',
        string='Modelos'
    )

    _sql_constraints = [
        ('marca_slug_unique', 'unique(slug)', 'El slug de la marca debe ser único'),
    ]



class ModeloVehiculo(models.Model):
    _name = 'vehiculo.modelo'
    _description = 'Modelo de Vehículo'
    _order = 'marca_id, nombre'
    _rec_name = 'nombre_mostrar'

    nombre = fields.Char(
        string='Nombre',
        required=True,
        index=True
    )
    slug = fields.Char(
        string='Slug',
        required=True,
        index=True
    )
    activo = fields.Boolean(
        string='Activo',
        default=True,
        index=True
    )

    marca_id = fields.Many2one(
        'vehiculo.marca',
        string='Marca',
        required=True,
        ondelete='cascade',
        index=True
    )

    django_external_id = fields.Char(
        string='ID Externo Django',
        index=True,
        copy=False,
        readonly=True
    )

    nombre_mostrar = fields.Char(
        string='Nombre Completo',
        compute='_compute_nombre_mostrar',
        store=True,
        index=True
    )

    variante_ids = fields.One2many(
        'vehiculo.variante',
        'modelo_id',
        string='Variantes'
    )

    _sql_constraints = [
        ('marca_modelo_unique', 'unique(marca_id, nombre)',
         'El modelo ya existe para esta marca'),
        ('modelo_slug_unique', 'unique(slug)', 'El slug del modelo debe ser único'),
    ]

    @api.depends('marca_id.nombre', 'nombre')
    def _compute_nombre_mostrar(self):
        for r in self:
            r.nombre_mostrar = f"{r.marca_id.nombre} {r.nombre}"


class TransmisionVehiculo(models.Model):
    _name = 'vehiculo.transmision'
    _description = 'Transmisión de Vehículo'
    _order = 'tipo, velocidades'

    tipo = fields.Selection(
        selection=[
            ('MT', 'Manual'),
            ('AT', 'Automática'),
            ('CVT', 'CVT'),
            ('DCT', 'DCT'),
            ('RED', 'Reducción fija (EV)'),
            ('NA', 'No aplica'),
        ],
        string='Tipo',
        required=True,
        index=True
    )

    velocidades = fields.Integer(
        string='Velocidades',
        index=True
    )

    django_external_id = fields.Char(
        string='ID Externo Django',
        index=True,
        copy=False,
        readonly=True
    )

    _sql_constraints = [
        ('transmision_unique', 'unique(tipo, velocidades)',
         'La transmisión ya existe'),
    ]

class TraccionVehiculo(models.Model):
    _name = 'vehiculo.traccion'
    _description = 'Tracción de Vehículo'
    _order = 'tipo'

    tipo = fields.Selection(
        selection=[
            ('4x2', '4x2'),
            ('4x4', '4x4'),
            ('AWD', 'AWD'),
        ],
        string='Tipo',
        required=True,
        index=True
    )

    django_external_id = fields.Char(
        string='ID Externo Django',
        index=True,
        copy=False,
        readonly=True
    )

    _sql_constraints = [
        ('traccion_unique', 'unique(tipo)',
         'La tracción ya existe'),
    ]
   

class MotorVehiculo(models.Model):
    _name = 'vehiculo.motor'
    _description = 'Motor de Vehículo'
    _order = 'cilindrada_cc'
    _rec_name = 'nombre'

    combustible = fields.Selection(
        selection=[
            ('GSL', 'Gasolina'),
            ('Hib', 'Híbrido'),
            ('Ele', 'Eléctrico'),
            ('Dis', 'Diésel'),
        ],
        string='Combustible',
        index=True
    )

    cilindrada_cc = fields.Integer(
        string='Cilindrada (cc)',
        index=True
    )

    codigo_motor = fields.Char(
        string='Código de Motor',
        index=True
    )

    tecnologia = fields.Char(
        string='Tecnología',
        index=True,
        help='VVT-i, TSI, Turbo, DVVT, etc.'
    )

    django_external_id = fields.Char(
        string='ID Externo Django',
        index=True,
        copy=False,
        readonly=True
    )

    nombre = fields.Char(
        string='Descripción',
        compute='_compute_nombre',
        store=True,
        index=True
    )

    _sql_constraints = [
        ('motor_unique',
         'unique(combustible, cilindrada_cc, codigo_motor, tecnologia)',
         'El motor ya existe'),
    ]

    @api.depends('combustible', 'cilindrada_cc', 'codigo_motor', 'tecnologia')
    def _compute_nombre(self):
        for m in self:
            partes = []
            if m.cilindrada_cc:
                partes.append(f"{m.cilindrada_cc / 1000:.1f}L")
            elif m.combustible == 'Ele':
                partes.append("Eléctrico")
            if m.codigo_motor:
                partes.append(f"({m.codigo_motor})")
            if m.tecnologia:
                partes.append(m.tecnologia)
            m.nombre = " ".join(partes) or f"Motor {m.id}"



class VarianteVehiculo(models.Model):
    _name = 'vehiculo.variante'
    _description = 'Variante de Vehículo'
    _order = 'modelo_id, anio_desde desc'
    _rec_name = 'nombre'

    modelo_id = fields.Many2one(
        'vehiculo.modelo',
        string='Modelo',
        required=True,
        index=True,
        ondelete='cascade'
    )
    motor_id = fields.Many2one(
        'vehiculo.motor',
        string='Motor',
        required=False,
        index=True,
        ondelete='restrict'
    )
    transmision_id = fields.Many2one(
        'vehiculo.transmision',
        string='Transmisión',
        required=False,
        index=True,
        ondelete='restrict'
    )
    traccion_id = fields.Many2one(
        'vehiculo.traccion',
        string='Tracción',
        required=False,
        index=True,
        ondelete='restrict'
    )

    anio_desde = fields.Integer(
        string='Año Desde',
        required=True,
        index=True
    )
    anio_hasta = fields.Integer(
        string='Año Hasta',
        index=True
    )

    django_external_id = fields.Char(
        string='ID Externo Django',
        index=True,
        copy=False,
        readonly=True
    )

    nombre = fields.Char(
        string='Descripción',
        compute='_compute_nombre',
        store=True,
        index=True
    )

    _sql_constraints = [
        ('variante_unique',
         'unique(modelo_id, motor_id, transmision_id, traccion_id, anio_desde, anio_hasta)',
         'La variante ya existe'),
    ]

    @api.depends(
        'modelo_id.nombre_mostrar',
        'anio_desde',
        'anio_hasta'
    )
    def _compute_nombre(self):
        for v in self:
            hasta = v.anio_hasta or '…'
            v.nombre = (
                f"{v.modelo_id.nombre_mostrar} | "
                f"{v.motor_id.nombre} | "
                f"{v.transmision_id.tipo} | "
                f"{v.traccion_id.tipo} "
                f"({v.anio_desde}-{hasta})"
            )

    @api.constrains('anio_desde', 'anio_hasta')
    def _check_anios(self):
        for v in self:
            if v.anio_hasta and v.anio_hasta < v.anio_desde:
                raise ValidationError(
                    'El año hasta no puede ser menor al año desde'
                )
