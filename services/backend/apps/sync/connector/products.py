"""
connector/products.py
=====================
Lectura de productos, categorias, almacenes y stock en Odoo.
"""
import logging

logger = logging.getLogger(__name__)


class OdooProductsMixin:
    """Mixin con operaciones sobre product.*, product.category, stock.warehouse y stock.quant."""

    def _get_category_fields_info(self) -> dict:
        """
        Retorna el metadata de campos de product.category cacheado por instancia.

        Evita repetir fields_get en cada categoria durante push_categories().
        """
        cached_fields = getattr(self, '_category_fields_info_cache', None)
        if cached_fields is not None:
            return cached_fields

        fields_info = self.execute_kw(
            'product.category',
            'fields_get',
            [],
            {'attributes': ['string']},
        )
        self._category_fields_info_cache = fields_info
        return fields_info

    def _get_res_id_by_xmlid(self, xmlid: str) -> int | None:
        """Resuelve el ID numérico de un registro Odoo a partir de su XML ID."""
        try:
            module, name = xmlid.split('.')
            result = self.execute_kw(
                'ir.model.data', 'search_read',
                [[['module', '=', module], ['name', '=', name]]],
                {'fields': ['res_id'], 'limit': 1},
            )
            return result[0]['res_id'] if result else None
        except Exception as e:
            logger.error("Error resolviendo XML ID %s: %s", xmlid, e)
            return None

    # ── Productos ─────────────────────────────────────────────────────────────

    def get_products(
        self,
        company_id: int = None,
        limit: int = None,
        fields: list | None = None,
        include_inactive: bool = False,
    ) -> list:
        """
        Obtiene productos de Odoo (product.product).

        Args:
            company_id: Filtrar por Company (opcional)
            limit:      Límite de resultados (None = sin límite)
            fields:     Lista de campos a leer; si es None usa el set completo
            include_inactive: Si es True incluye archivados en Odoo

        Returns:
            list[dict]: Productos con campos de catálogo, stock e imagen
        """
        try:
            domain = []
            if company_id:
                domain.append(('company_id', '=', company_id))

            default_fields = [
                'id', 'name', 'default_code', 'description_sale',
                'list_price', 'standard_price', 'qty_available',
                'barcode', 'weight', 'active', 'image_1920',
                'categ_id',
                'type',
                'product_tmpl_id',
                'autopart_oem_code',
                'autopart_side',
                'autopart_quality',
                'autopart_universal',
            ]
            kwargs = {
                'fields': fields or default_fields,
            }
            if include_inactive:
                kwargs['context'] = {'active_test': False}
            if limit:
                kwargs['limit'] = limit

            return self.execute_kw('product.product', 'search_read', [domain], kwargs)

        except Exception as e:
            logger.error("Error obteniendo productos de Odoo: %s", e)
            return []

    def get_products_by_ids(
        self,
        product_ids: list[int],
        *,
        fields: list | None = None,
        include_inactive: bool = False,
    ) -> list:
        """Obtiene productos concretos de Odoo por lista de IDs."""
        if not product_ids:
            return []

        try:
            kwargs = {
                'fields': fields or ['id', 'name'],
            }
            if include_inactive:
                kwargs['context'] = {'active_test': False}

            return self.execute_kw(
                'product.product',
                'search_read',
                [[['id', 'in', product_ids]]],
                kwargs,
            )
        except Exception as e:
            logger.error("Error obteniendo productos por IDs desde Odoo: %s", e)
            return []

    def get_product_stock(self, product_id: int) -> dict | None:
        """
        Obtiene el stock disponible y proyectado de un producto específico.

        Args:
            product_id: ID de product.product en Odoo

        Returns:
            dict con qty_available y virtual_available, o None
        """
        try:
            products = self.execute_kw(
                'product.product', 'search_read',
                [[['id', '=', product_id]]],
                {'fields': ['qty_available', 'virtual_available'], 'limit': 1},
            )
            return products[0] if products else None
        except Exception as e:
            logger.error("Error obteniendo stock de producto %s: %s", product_id, e)
            return None


    # ── Categorías ────────────────────────────────────────────────────────────

    def get_categories(self, company_id: int = None, fields: list | None = None) -> list:
        """
        Obtiene todas las categorías de producto de Odoo (product.category).

        Las categorías son globales en Odoo (no por company). El parámetro
        company_id se acepta para mantener una interfaz consistente pero no filtra.

        Returns:
            list[dict]: Categorías con id, name, parent_id, complete_name
        """
        default_fields = fields or [
            'id', 'name', 'parent_id', 'complete_name', 'active', 'django_sync_key', 'django_import_code',
        ]
        try:
            return self.execute_kw(
                'product.category', 'search_read',
                [[]],
                {'fields': default_fields},
            )
        except Exception as e:
            if 'django_sync_key' in default_fields or 'django_import_code' in default_fields:
                fallback_fields = [
                    f for f in default_fields
                    if f not in {'django_sync_key', 'django_import_code'}
                ]
                try:
                    logger.warning(
                        "Odoo aún no expone campos Django en product.category; reintentando sin ellos."
                    )
                    return self.execute_kw(
                        'product.category', 'search_read',
                        [[]],
                        {'fields': fallback_fields},
                    )
                except Exception as fallback_error:
                    logger.error("Error obteniendo categorias de Odoo: %s", fallback_error)
                    return []
            logger.error("Error obteniendo categorias de Odoo: %s", e)
            return []

    def get_category_root_id(self) -> int | None:
        """Retorna el ID de la categoría raíz nativa `All` en Odoo."""
        return self._get_res_id_by_xmlid('product.product_category_all')

    def category_supports_sync_key(self) -> bool:
        """Indica si `product.category` en Odoo expone el campo django_sync_key."""
        try:
            fields_info = self._get_category_fields_info()
            return 'django_sync_key' in fields_info
        except Exception as e:
            logger.error("Error consultando fields_get de product.category: %s", e)
            return False

    def get_category_supported_fields(self) -> set[str]:
        """Retorna el conjunto de campos disponibles actualmente en product.category."""
        try:
            fields_info = self._get_category_fields_info()
            return set(fields_info.keys())
        except Exception as e:
            logger.error("Error consultando fields_get de product.category: %s", e)
            return set()

    def push_category(
        self,
        *,
        name: str,
        django_sync_key: str,
        django_import_code: str | None,
        parent_odoo_id: int,
        is_active: bool,
        odoo_category_id: int | None = None,
    ) -> tuple[int, bool, bool]:
        """
        Crea o vincula una categoría en Odoo usando django_sync_key como ancla.

        Orden:
          1. django_sync_key
          2. odoo_category_id legado
          3. clave natural (name + parent_id)
          4. create

        Returns:
            tuple(odoo_id, created, updated)
        """
        supported_fields = self.get_category_supported_fields()
        if 'django_sync_key' not in supported_fields:
            raise RuntimeError(
                "Odoo no expone product.category.django_sync_key. "
                "Actualiza el módulo ecomp antes de ejecutar push_categories."
            )

        supports_active = 'active' in supported_fields

        supports_import_code = 'django_import_code' in supported_fields

        fields = ['id', 'name', 'parent_id', 'django_sync_key']
        if supports_import_code:
            fields.append('django_import_code')
        if supports_active:
            fields.append('active')
        target_parent_id = parent_odoo_id or False
        existing = self.execute_kw(
            'product.category', 'search_read',
            [[['django_sync_key', '=', django_sync_key]]],
            {'fields': fields, 'limit': 1},
        )

        if not existing and odoo_category_id:
            existing = self.execute_kw(
                'product.category', 'search_read',
                [[['id', '=', odoo_category_id]]],
                {'fields': fields, 'limit': 1},
            )

        if not existing:
            existing = self.execute_kw(
                'product.category', 'search_read',
                [[['name', '=', name], ['parent_id', '=', target_parent_id]]],
                {'fields': fields, 'limit': 1},
            )

        if existing:
            record = existing[0]
            update_vals = {}
            current_parent_raw = record.get('parent_id')
            current_parent_id = current_parent_raw[0] if current_parent_raw else False

            if record.get('name') != name:
                update_vals['name'] = name
            if current_parent_id != target_parent_id:
                update_vals['parent_id'] = target_parent_id
            if supports_active and bool(record.get('active', True)) != bool(is_active):
                update_vals['active'] = bool(is_active)
            if record.get('django_sync_key') != django_sync_key:
                update_vals['django_sync_key'] = django_sync_key
            if supports_import_code and record.get('django_import_code') != django_import_code:
                update_vals['django_import_code'] = django_import_code

            if update_vals:
                self.execute_kw(
                    'product.category', 'write',
                    [[record['id']], update_vals],
                )
            return record['id'], False, bool(update_vals)

        create_vals = {
            'name': name,
            'parent_id': target_parent_id,
            'django_sync_key': django_sync_key,
        }
        if supports_import_code:
            create_vals['django_import_code'] = django_import_code
        if supports_active:
            create_vals['active'] = bool(is_active)
        odoo_id = self.execute_kw('product.category', 'create', [create_vals])
        return odoo_id, True, False
