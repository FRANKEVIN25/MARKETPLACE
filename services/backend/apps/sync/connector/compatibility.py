"""
connector/compatibility.py
===========================
Lectura de compatibilidades autoparte↔vehículo y variantes vehiculares en Odoo.

Estos métodos son de solo lectura — la escritura de compatibilidades
ocurre desde la UI de Odoo (el proveedor asigna qué variantes aplican
a sus productos). Django solo consume esa información.
"""
import logging

logger = logging.getLogger(__name__)


class OdooCompatibilityMixin:
    """Mixin con operaciones de lectura sobre autopart.compatibility y vehiculo.variante."""

    def get_compatibilities(self, product_tmpl_ids: list) -> list:
        """
        Obtiene registros de autopart.compatibility para un conjunto de templates.

        Cada registro vincula un product.template con un vehiculo.variante
        y puede incluir notas de montaje (fitment_notes).

        Args:
            product_tmpl_ids: IDs de product.template a consultar

        Returns:
            list[dict]: Compatibilidades con product_tmpl_id, variant_id,
                        fitment_notes y active
        """
        if not product_tmpl_ids:
            return []
        try:
            return self.execute_kw(
                'autopart.compatibility', 'search_read',
                [[
                    ['product_tmpl_id', 'in', product_tmpl_ids],
                    ['active', '=', True],
                ]],
                {
                    'fields': [
                        'id',
                        'product_tmpl_id',
                        'variant_id',
                        'fitment_notes',
                        'active',
                    ],
                },
            )
        except Exception as e:
            logger.error(f"Error obteniendo autopart.compatibility: {e}")
            return []

    def get_vehicle_variants(self, variant_ids: list) -> dict:
        """
        Obtiene registros de vehiculo.variante por sus IDs en Odoo.

        Incluye django_external_id para resolver el PK de Django sin queries
        adicionales durante la sync de compatibilidades.

        Args:
            variant_ids: IDs de vehiculo.variante en Odoo

        Returns:
            dict {odoo_variant_id: record} donde cada record incluye:
              id, nombre, django_external_id, modelo_id, motor_id,
              transmision_id, traccion_id, anio_desde, anio_hasta
              (los many2one se devuelven como (id, nombre))
        """
        if not variant_ids:
            return {}
        try:
            records = self.execute_kw(
                'vehiculo.variante', 'search_read',
                [[['id', 'in', variant_ids]]],
                {
                    'fields': [
                        'id',
                        'nombre',
                        'django_external_id',
                        'modelo_id',
                        'motor_id',
                        'transmision_id',
                        'traccion_id',
                        'anio_desde',
                        'anio_hasta',
                    ],
                },
            )
            return {r['id']: r for r in records}
        except Exception as e:
            logger.error(f"Error obteniendo vehiculo.variante: {e}")
            return {}
