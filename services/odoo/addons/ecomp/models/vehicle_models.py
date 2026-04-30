# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


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

    # readonly=True se aplica solo en las vistas (vehicle_views.xml), NO aquí.
    # A nivel de campo en el modelo, readonly bloquearía también las escrituras
    # vía RPC (push desde Django), lo cual rompe el comando push_vehicles.
    django_external_id = fields.Char(
        string='ID Externo Django',
        index=True,
        copy=False,
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
    _rec_name = 'display_name'    

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
    )

    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    @api.depends('tipo', 'velocidades')
    def _compute_display_name(self):
        for rec in self:
            label = dict(self._fields['tipo'].selection).get(rec.tipo, '')
            if rec.velocidades:
                rec.display_name = f"{label} {rec.velocidades}V"
            else:
                rec.display_name = label

    _sql_constraints = [
        ('transmision_unique', 'unique(tipo, velocidades)',
         'La transmisión ya existe'),
    ]

class TraccionVehiculo(models.Model):
    _name = 'vehiculo.traccion'
    _description = 'Tracción de Vehículo'
    _order = 'tipo'
    _rec_name = 'display_name'

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
    )

    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    @api.depends('tipo')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = dict(
                self._fields['tipo'].selection
            ).get(rec.tipo)

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

    IMPORT_XMLID_MODULE = 'ecomp'
    IMPORT_XMLID_PREFIX = 'var_'

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
        string='ID Externo',
        index=True,
        copy=False,
    )

    django_import_code = fields.Char(
        string='Código importación',
        index=True,
        copy=False,
        help='Código corto y estable enviado desde Django para importaciones operativas.',
    )

    import_xmlid = fields.Char(
        string='Código importación',
        compute='_compute_import_xmlid',
        help='External ID completo listo para copiar y usar en importaciones.',
    )

    # ── Scope por proveedor ──────────────────────────────────────────────────
    # Controla qué tenants (compañías/proveedores) pueden ver y usar esta variante
    # en el selector de compatibilidades.
    # - Gestionado exclusivamente por push_vehicles vía RPC (admin bypasea record rules).
    # - Usuarios de Odoo no ven ni editan este campo (oculto en vistas).
    # - Una variante con company_ids vacío es visible para TODOS (fallback seguro
    #   durante la migración y para la puesta en marcha inicial).
    company_ids = fields.Many2many(
        'res.company',
        'vehiculo_variante_company_rel',
        'variante_id',
        'company_id',
        string='Compañías habilitadas',
        help=(
            'Proveedores (compañías de Odoo) con acceso a esta variante. '
            'Gestionado automáticamente desde Django vía push_vehicles --provider-id. '
            'No modificar manualmente.'
        ),
        copy=False,
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
        (
            'vehiculo_variante_django_import_code_unique',
            'unique(django_import_code)',
            'El código de importación Django debe ser único por variante.',
        ),
    ]

    @api.model
    def _get_import_identifier(self, django_import_code=None):
        if django_import_code:
            normalized_code = django_import_code.strip().lower()
            if normalized_code:
                return normalized_code
        return False

    @api.model
    def _build_import_xmlid_name(self, django_import_code=None):
        import_identifier = self._get_import_identifier(django_import_code)
        if not import_identifier:
            return False
        return f'{self.IMPORT_XMLID_PREFIX}{import_identifier}'

    @api.depends('django_import_code')
    def _compute_import_xmlid(self):
        for variant in self:
            xmlid_name = variant._build_import_xmlid_name(variant.django_import_code)
            if xmlid_name:
                variant.import_xmlid = f'{self.IMPORT_XMLID_MODULE}.{xmlid_name}'
            else:
                variant.import_xmlid = False

    def _sync_import_external_ids_with_database(self):
        self._cr.execute(
            """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            SELECT
                %s,
                CONCAT(%s, LOWER(BTRIM(django_import_code))),
                %s,
                id,
                %s
            FROM vehiculo_variante
            WHERE NULLIF(LOWER(BTRIM(django_import_code)), '') IS NOT NULL
            ON CONFLICT (module, name)
            DO UPDATE SET
                model = EXCLUDED.model,
                res_id = EXCLUDED.res_id,
                noupdate = EXCLUDED.noupdate
            """,
            (self.IMPORT_XMLID_MODULE, self.IMPORT_XMLID_PREFIX, self._name, True),
        )

    def _cleanup_stale_import_external_ids(self, previous_xmlid_names):
        stale_names = []
        current_names = {
            variant.id: variant._build_import_xmlid_name(variant.django_import_code)
            for variant in self
        }

        for variant_id, previous_name in previous_xmlid_names.items():
            if previous_name and previous_name != current_names.get(variant_id):
                stale_names.append(previous_name)

        if not stale_names:
            return

        self.env['ir.model.data'].sudo().search([
            ('module', '=', self.IMPORT_XMLID_MODULE),
            ('model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('name', 'in', stale_names),
        ]).unlink()

    def _ensure_import_external_ids(self):
        variants = self.filtered(lambda variant: variant.django_import_code)
        if not variants:
            return

        xmlid_names = [
            variant._build_import_xmlid_name(variant.django_import_code)
            for variant in variants
        ]
        model_data = self.env['ir.model.data'].sudo()
        existing_xmlids = model_data.search([
            ('module', '=', self.IMPORT_XMLID_MODULE),
            ('name', 'in', xmlid_names),
        ])
        existing_by_name = {xmlid.name: xmlid for xmlid in existing_xmlids}
        xmlids_to_create = []

        for variant in variants:
            xmlid_name = variant._build_import_xmlid_name(variant.django_import_code)
            xmlid_record = existing_by_name.get(xmlid_name)
            if xmlid_record:
                update_vals = {}
                if xmlid_record.model != self._name:
                    update_vals['model'] = self._name
                if xmlid_record.res_id != variant.id:
                    update_vals['res_id'] = variant.id
                if not xmlid_record.noupdate:
                    update_vals['noupdate'] = True
                if update_vals:
                    xmlid_record.write(update_vals)
                continue

            xmlids_to_create.append({
                'module': self.IMPORT_XMLID_MODULE,
                'name': xmlid_name,
                'model': self._name,
                'res_id': variant.id,
                'noupdate': True,
            })

        if xmlids_to_create:
            model_data.create(xmlids_to_create)

    @api.model_create_multi
    def create(self, vals_list):
        variants = super().create(vals_list)
        variants._ensure_import_external_ids()
        return variants

    def write(self, vals):
        previous_xmlid_names = {}
        if 'django_import_code' in vals:
            previous_xmlid_names = {
                variant.id: variant._build_import_xmlid_name(variant.django_import_code)
                for variant in self
                if variant.django_import_code
            }

        result = super().write(vals)

        if 'django_import_code' in vals:
            self._cleanup_stale_import_external_ids(previous_xmlid_names)
            self._ensure_import_external_ids()

        return result

    def init(self):
        self._sync_import_external_ids_with_database()

    def _register_hook(self):
        result = super()._register_hook()
        self._sync_import_external_ids_with_database()
        return result

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
                f"{v.transmision_id.display_name} | "
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
