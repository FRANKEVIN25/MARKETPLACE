"""
connector/vehicles.py
=====================
Push del catálogo vehicular Django → Odoo y gestión de scope multi-company.

Patrón de 3 vías (idempotente para todos los métodos push_*):
  1. Buscar por django_external_id   → ya vinculado, retornar odoo_id
  2. Buscar por clave natural        → existe sin vincular, vincular y retornar
  3. Crear en Odoo                   → nuevo registro, vincular y retornar

Esto permite correr push_vehicles múltiples veces sin duplicar datos,
y sirve de bootstrap cuando Odoo y Django parten de cero.
"""
import logging

logger = logging.getLogger(__name__)


class OdooVehiclesMixin:
    """
    Mixin con operaciones de push hacia vehiculo.* en Odoo y
    gestión de scope (company_ids) en vehiculo.variante.
    """

    # ── Lógica común de push ──────────────────────────────────────────────────

    def _push_or_link(
        self,
        model: str,
        domain_by_ext_id: list,
        domain_by_natural_key: list,
        create_vals: dict,
        django_id: int,
        sync_vals: dict | None = None,
    ) -> int:
        """
        Lógica de 3 vías compartida por todos los métodos push_*.

        Args:
            model:                 Nombre del modelo Odoo (ej: 'vehiculo.marca')
            domain_by_ext_id:      Dominio para buscar por django_external_id
            domain_by_natural_key: Dominio para buscar por clave de negocio
            create_vals:           Valores para crear si no existe
            django_id:             PK del registro en Django (se guarda como str)

        Returns:
            int: ID del registro en Odoo
        """
        str_django_id = str(django_id)
        sync_vals = sync_vals or {}

        def _build_update_vals(record: dict, ensure_external_id: bool) -> dict:
            update_vals = {}
            if ensure_external_id and not record.get('django_external_id'):
                update_vals['django_external_id'] = str_django_id
            for field_name, field_value in sync_vals.items():
                if record.get(field_name) != field_value:
                    update_vals[field_name] = field_value
            return update_vals

        read_fields = ['id', 'django_external_id', *sync_vals.keys()]

        # 1. Buscar por django_external_id (sync previa)
        existing = self.execute_kw(
            model, 'search_read',
            [domain_by_ext_id],
            {'fields': read_fields, 'limit': 1},
        )
        if existing:
            record = existing[0]
            update_vals = _build_update_vals(record, ensure_external_id=False)
            if update_vals:
                self.execute_kw(model, 'write', [[record['id']], update_vals])
            return record['id']

        # 2. Buscar por clave natural (registro sin vincular)
        existing = self.execute_kw(
            model, 'search_read',
            [domain_by_natural_key],
            {'fields': read_fields, 'limit': 1},
        )
        if existing:
            record = existing[0]
            odoo_id = record['id']
            update_vals = _build_update_vals(record, ensure_external_id=True)
            if update_vals:
                self.execute_kw(
                    model, 'write',
                    [[odoo_id], update_vals],
                )
            return odoo_id

        # 3. Crear nuevo registro en Odoo
        create_vals = dict(create_vals)
        create_vals['django_external_id'] = str_django_id
        create_vals.update(sync_vals)
        return self.execute_kw(model, 'create', [create_vals])

    # ── Push de entidades vehiculares ─────────────────────────────────────────

    def push_marca(self, nombre: str, slug: str, django_id: int) -> int:
        """Empuja o vincula una Marca. Retorna el odoo_id."""
        from django.utils.text import slugify
        return self._push_or_link(
            'vehiculo.marca',
            [['django_external_id', '=', str(django_id)]],
            [['nombre', '=', nombre]],
            {'nombre': nombre, 'slug': slug or slugify(nombre), 'activo': True},
            django_id,
        )

    def push_modelo(
        self,
        nombre: str,
        slug: str,
        marca_odoo_id: int,
        django_id: int,
    ) -> int:
        """Empuja o vincula un ModeloVehiculo. Retorna el odoo_id."""
        from django.utils.text import slugify
        return self._push_or_link(
            'vehiculo.modelo',
            [['django_external_id', '=', str(django_id)]],
            [['nombre', '=', nombre], ['marca_id', '=', marca_odoo_id]],
            {
                'nombre': nombre,
                'slug': slug or slugify(f"{marca_odoo_id}-{nombre}"),
                'marca_id': marca_odoo_id,
                'activo': True,
            },
            django_id,
        )

    def push_transmision(
        self,
        tipo: str,
        velocidades: int | None,
        django_id: int,
    ) -> int:
        """Empuja o vincula una Transmision. Retorna el odoo_id."""
        domain_natural = [['tipo', '=', tipo]]
        domain_natural.append(
            ['velocidades', '=', velocidades] if velocidades
            else ['velocidades', '=', False]
        )
        return self._push_or_link(
            'vehiculo.transmision',
            [['django_external_id', '=', str(django_id)]],
            domain_natural,
            {'tipo': tipo, 'velocidades': velocidades or False},
            django_id,
        )

    def push_traccion(self, tipo: str, django_id: int) -> int:
        """Empuja o vincula una Traccion. Retorna el odoo_id."""
        return self._push_or_link(
            'vehiculo.traccion',
            [['django_external_id', '=', str(django_id)]],
            [['tipo', '=', tipo]],
            {'tipo': tipo},
            django_id,
        )

    def push_motor(
        self,
        combustible: str | None,
        cilindrada_cc: int | None,
        codigo_motor: str | None,
        tecnologia: str | None,
        django_id: int,
    ) -> int:
        """Empuja o vincula un Motor. Retorna el odoo_id."""
        domain_natural = []
        if combustible:
            domain_natural.append(['combustible', '=', combustible])
        if cilindrada_cc:
            domain_natural.append(['cilindrada_cc', '=', cilindrada_cc])
        if codigo_motor:
            domain_natural.append(['codigo_motor', '=', codigo_motor])
        if tecnologia:
            domain_natural.append(['tecnologia', '=', tecnologia])
        if not domain_natural:
            domain_natural = [['id', '!=', 0]]  # fallback seguro

        return self._push_or_link(
            'vehiculo.motor',
            [['django_external_id', '=', str(django_id)]],
            domain_natural,
            {
                'combustible': combustible or False,
                'cilindrada_cc': cilindrada_cc or False,
                'codigo_motor': codigo_motor or False,
                'tecnologia': tecnologia or False,
            },
            django_id,
        )

    def push_variante(
        self,
        modelo_odoo_id: int,
        motor_odoo_id: int | None,
        trans_odoo_id: int | None,
        trac_odoo_id: int | None,
        anio_desde: int,
        anio_hasta: int | None,
        django_id: int,
        django_import_code: str | None = None,
    ) -> int:
        """
        Empuja o vincula una VariantVehiculo completa.

        Args:
            modelo_odoo_id: odoo_id del ModeloVehiculo
            motor_odoo_id:  odoo_id del Motor (None si no aplica)
            trans_odoo_id:  odoo_id de la Transmision (None si no aplica)
            trac_odoo_id:   odoo_id de la Traccion (None si no aplica)
            anio_desde:     Año de inicio del rango de aplicación
            anio_hasta:     Año de fin del rango (None = modelo en producción)
            django_id:      PK de VariantVehiculo en Django

        Returns:
            int: odoo_id de vehiculo.variante
        """
        domain_natural = [
            ['modelo_id', '=', modelo_odoo_id],
            ['anio_desde', '=', anio_desde],
        ]
        if anio_hasta:
            domain_natural.append(['anio_hasta', '=', anio_hasta])
        if motor_odoo_id:
            domain_natural.append(['motor_id', '=', motor_odoo_id])
        if trans_odoo_id:
            domain_natural.append(['transmision_id', '=', trans_odoo_id])
        if trac_odoo_id:
            domain_natural.append(['traccion_id', '=', trac_odoo_id])

        return self._push_or_link(
            'vehiculo.variante',
            [['django_external_id', '=', str(django_id)]],
            domain_natural,
            {
                'modelo_id': modelo_odoo_id,
                'motor_id': motor_odoo_id or False,
                'transmision_id': trans_odoo_id or False,
                'traccion_id': trac_odoo_id or False,
                'anio_desde': anio_desde,
                'anio_hasta': anio_hasta or False,
            },
            django_id,
            sync_vals={'django_import_code': django_import_code or False},
        )

    # ── Scope multi-company ───────────────────────────────────────────────────

    def scope_variante_for_company(
        self,
        odoo_variante_id: int,
        company_id: int,
    ) -> None:
        """
        Añade company_id a vehiculo.variante.company_ids, otorgando visibilidad
        de esa variante al tenant del proveedor en Odoo.

        Usa ORM command (4, id) = link-if-not-linked → idempotente.

        Args:
            odoo_variante_id: ID de vehiculo.variante en Odoo
            company_id:       ID de res.company del proveedor
        """
        self.execute_kw(
            'vehiculo.variante', 'write',
            [[odoo_variante_id], {'company_ids': [(4, company_id)]}],
            {'context': {'active_test': False}},
        )
        logger.debug(
            f"scope_variante_for_company: variante={odoo_variante_id} → company={company_id}"
        )

    def unscope_variante_from_company(
        self,
        odoo_variante_id: int,
        company_id: int,
    ) -> None:
        """
        Quita company_id de vehiculo.variante.company_ids, revocando la
        visibilidad de esa variante para el proveedor.

        Usa ORM command (3, id) = unlink. Si ya no estaba vinculado, Odoo lo ignora.

        Args:
            odoo_variante_id: ID de vehiculo.variante en Odoo
            company_id:       ID de res.company del proveedor
        """
        self.execute_kw(
            'vehiculo.variante', 'write',
            [[odoo_variante_id], {'company_ids': [(3, company_id)]}],
            {'context': {'active_test': False}},
        )
        logger.debug(
            f"unscope_variante_from_company: variante={odoo_variante_id} → company={company_id}"
        )

    def sync_full_scope_for_company(
        self,
        odoo_variante_ids: list[int],
        company_id: int,
    ) -> dict:
        """
        Sincroniza el scope completo de un proveedor en una sola pasada:
          - Añade company_id a las variantes del scope que aún no lo tienen.
          - Quita company_id de las variantes que Odoo tiene pero ya no están en el scope.

        Diseñado para push_vehicles --provider-id. Garantiza consistencia total
        en una sola llamada por dirección (add / remove), sin loops.

        Args:
            odoo_variante_ids: IDs de vehiculo.variante que deben estar en el scope
            company_id:        ID de res.company del proveedor

        Returns:
            dict: {'added': int, 'removed': int}
        """
        existing_ids = self.execute_kw(
            'vehiculo.variante', 'search',
            [[['company_ids', 'in', [company_id]]]],
            {'context': {'active_test': False}, 'limit': 0},
        ) or []

        scope_set    = set(odoo_variante_ids)
        existing_set = set(existing_ids)

        to_add    = list(scope_set - existing_set)
        to_remove = list(existing_set - scope_set)

        if to_add:
            self.execute_kw(
                'vehiculo.variante', 'write',
                [to_add, {'company_ids': [(4, company_id)]}],
                {'context': {'active_test': False}},
            )

        if to_remove:
            self.execute_kw(
                'vehiculo.variante', 'write',
                [to_remove, {'company_ids': [(3, company_id)]}],
                {'context': {'active_test': False}},
            )

        logger.info(
            f"sync_full_scope_for_company company={company_id}: "
            f"+{len(to_add)} variantes, -{len(to_remove)} variantes"
        )
        return {'added': len(to_add), 'removed': len(to_remove)}
