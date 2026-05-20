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

    marketplace_image_ids = fields.One2many(
        'ecomp.product.image',
        'product_tmpl_id',
        string='Imágenes del Marketplace'
    )


class ProductCategory(models.Model):
    _inherit = 'product.category'

    IMPORT_XMLID_MODULE = 'ecomp'
    IMPORT_XMLID_PREFIX = 'cat_'

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

    django_import_code = fields.Char(
        string='Código importación',
        index=True,
        copy=False,
        help='Código corto y estable definido en Django para construir el External ID de importación.',
    )

    import_xmlid = fields.Char(
        string='Código importación',
        compute='_compute_import_xmlid',
        help='External ID completo listo para copiar y usar en importaciones.',
    )

    _sql_constraints = [
        (
            'product_category_django_sync_key_unique',
            'unique(django_sync_key)',
            'La sync key de Django debe ser única por categoría.',
        ),
        (
            'product_category_django_import_code_unique',
            'unique(django_import_code)',
            'El código de importación Django debe ser único por categoría.',
        ),
    ]

    @api.model
    def _get_import_identifier(self, django_import_code=None, django_sync_key=None):
        if django_import_code:
            normalized_code = django_import_code.strip().lower()
            if normalized_code:
                return normalized_code
        if django_sync_key:
            normalized_sync_key = django_sync_key.strip().lower().replace('-', '_')
            if normalized_sync_key:
                return normalized_sync_key
        return False

    @api.model
    def _build_import_xmlid_name(self, django_import_code=None, django_sync_key=None):
        import_identifier = self._get_import_identifier(django_import_code, django_sync_key)
        if not import_identifier:
            return False
        return f'{self.IMPORT_XMLID_PREFIX}{import_identifier}'

    @api.depends('django_import_code', 'django_sync_key')
    def _compute_import_xmlid(self):
        for category in self:
            xmlid_name = category._build_import_xmlid_name(
                category.django_import_code,
                category.django_sync_key,
            )
            if xmlid_name:
                category.import_xmlid = f'{self.IMPORT_XMLID_MODULE}.{xmlid_name}'
            else:
                category.import_xmlid = False

    def _sync_import_external_ids_with_database(self):
        self._cr.execute(
            """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            SELECT
                %s,
                CONCAT(
                    %s,
                    COALESCE(
                        NULLIF(LOWER(BTRIM(django_import_code)), ''),
                        NULLIF(REPLACE(LOWER(BTRIM(django_sync_key)), '-', '_'), '')
                    )
                ),
                %s,
                id,
                %s
            FROM product_category
            WHERE COALESCE(
                NULLIF(LOWER(BTRIM(django_import_code)), ''),
                NULLIF(REPLACE(LOWER(BTRIM(django_sync_key)), '-', '_'), '')
            ) IS NOT NULL
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
            category.id: category._build_import_xmlid_name(category.django_import_code, category.django_sync_key)
            for category in self
        }

        for category_id, previous_name in previous_xmlid_names.items():
            if previous_name and previous_name != current_names.get(category_id):
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
        categories = self.filtered(lambda category: category.django_import_code or category.django_sync_key)
        if not categories:
            return

        xmlid_names = [
            category._build_import_xmlid_name(category.django_import_code, category.django_sync_key)
            for category in categories
        ]
        model_data = self.env['ir.model.data'].sudo()
        existing_xmlids = model_data.search([
            ('module', '=', self.IMPORT_XMLID_MODULE),
            ('name', 'in', xmlid_names),
        ])
        existing_by_name = {xmlid.name: xmlid for xmlid in existing_xmlids}
        xmlids_to_create = []

        for category in categories:
            xmlid_name = category._build_import_xmlid_name(category.django_import_code, category.django_sync_key)
            xmlid_record = existing_by_name.get(xmlid_name)
            if xmlid_record:
                update_vals = {}
                if xmlid_record.model != self._name:
                    update_vals['model'] = self._name
                if xmlid_record.res_id != category.id:
                    update_vals['res_id'] = category.id
                if not xmlid_record.noupdate:
                    update_vals['noupdate'] = True
                if update_vals:
                    xmlid_record.write(update_vals)
                continue

            xmlids_to_create.append({
                'module': self.IMPORT_XMLID_MODULE,
                'name': xmlid_name,
                'model': self._name,
                'res_id': category.id,
                'noupdate': True,
            })

        if xmlids_to_create:
            model_data.create(xmlids_to_create)

    @api.model_create_multi
    def create(self, vals_list):
        categories = super().create(vals_list)
        categories._ensure_import_external_ids()
        return categories

    def write(self, vals):
        previous_xmlid_names = {}
        if 'django_sync_key' in vals or 'django_import_code' in vals:
            previous_xmlid_names = {
                category.id: category._build_import_xmlid_name(category.django_import_code, category.django_sync_key)
                for category in self
                if category.django_import_code or category.django_sync_key
            }

        result = super().write(vals)

        if 'django_sync_key' in vals or 'django_import_code' in vals:
            self._cleanup_stale_import_external_ids(previous_xmlid_names)
            self._ensure_import_external_ids()

        return result

    def init(self):
        self._sync_import_external_ids_with_database()

    def _register_hook(self):
        result = super()._register_hook()
        self._sync_import_external_ids_with_database()
        return result
