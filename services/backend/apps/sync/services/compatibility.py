"""
services/compatibility.py
=========================
Sincronización de compatibilidades producto ↔ vehículo desde Odoo.

Incluye:
  - sync_provider_compatibility(): consulta autopart.compatibility en Odoo
    y crea/actualiza CompatibilidadProducto en Django.
  - _resolve_django_variant(): 3-estrategias para mapear odoo_variante_id
    a un VariantVehiculo de Django.
"""
import logging

from apps.marketplace.models import Provider
from apps.products.models import Product, CompatibilidadProducto
from apps.sync.connector import get_odoo_connector_for_provider
from apps.vehicles.models import VariantVehiculo
from .observability import mark_sync_finished, mark_sync_started

logger = logging.getLogger(__name__)


def sync_provider_compatibility(provider_id: int) -> dict:
    """
    Sincroniza las compatibilidades de producto↔vehículo desde Odoo.

    Flujo:
      1. Obtiene todos los productos del provider que tienen odoo_template_id.
      2. Consulta autopart.compatibility en Odoo para esos templates (en lote).
      3. Para cada registro de compatibilidad:
           - Resuelve el Product Django por odoo_template_id.
           - Resuelve el VariantVehiculo Django (ver _resolve_django_variant).
      4. Crea o actualiza CompatibilidadProducto con las notas de montaje.

    Returns:
        dict con estadísticas
    """
    try:
        provider = Provider.objects.get(id=provider_id, is_active=True)
    except Provider.DoesNotExist:
        return {'error': 'Provider no encontrado'}

    started_at = mark_sync_started(provider, 'compatibility')

    try:
        odoo = get_odoo_connector_for_provider(provider)
    except Exception as e:
        logger.error("Error conectando a Odoo para %s: %s", provider_id, e)
        mark_sync_finished(
            provider,
            'compatibility',
            started_at,
            status='failed',
            error_message=str(e),
        )
        return {'error': str(e)}

    stats = {
        'provider': provider.name,
        'compat_created': 0,
        'compat_updated': 0,
        'compat_removed': 0,
        'skipped_no_product': 0,
        'skipped_no_variant': 0,
        'errors': 0,
    }

    # ── 1. Templates del provider ────────────────────────────────────────────
    provider_products = list(
        Product.objects
        .filter(provider=provider, odoo_template_id__isnull=False)
        .values('id', 'odoo_template_id')
    )
    tmpl_to_product_id = {p['odoo_template_id']: p['id'] for p in provider_products}
    tmpl_ids = list(tmpl_to_product_id.keys())

    if not tmpl_ids:
        logger.info(
            "%s: sin productos con odoo_template_id, omitiendo compatibilidades",
            provider.name,
        )
        mark_sync_finished(provider, 'compatibility', started_at, status='success', metrics=stats)
        return stats

    # ── 2. Compatibilidades desde Odoo (una sola query en lote) ─────────────
    compat_records = odoo.get_compatibilities(tmpl_ids)
    logger.info(
        "%s: %d compatibilidad(es) encontradas en Odoo",
        provider.name, len(compat_records),
    )

    # ── 3. Prefetch variantes de Odoo (una sola query) ───────────────────────
    odoo_variant_ids = [
        r['variant_id'][0] for r in compat_records
        if r.get('variant_id')
    ]
    odoo_variant_map = odoo.get_vehicle_variants(list(set(odoo_variant_ids)))
    variant_maps = _build_variant_maps(odoo_variant_ids, odoo_variant_map)

    # ── 4. Construir estado deseado desde Odoo ──────────────────────────────
    desired_compatibilities = {}
    variants_to_persist = {}

    for record in compat_records:
        try:
            tmpl_id = record['product_tmpl_id'][0] if record.get('product_tmpl_id') else None
            product_id = tmpl_to_product_id.get(tmpl_id)
            if not product_id:
                stats['skipped_no_product'] += 1
                continue

            odoo_variant_id = record['variant_id'][0] if record.get('variant_id') else None
            variant = _resolve_django_variant(
                odoo_variant_id,
                odoo_variant_map,
                variant_maps=variant_maps,
            )
            if not variant:
                stats['skipped_no_variant'] += 1
                logger.warning(
                    "No se encontró VariantVehiculo para odoo_variante_id=%s "
                    "(product_tmpl_id=%s)",
                    odoo_variant_id, tmpl_id,
                )
                continue

            if variant.odoo_variante_id != odoo_variant_id:
                variant.odoo_variante_id = odoo_variant_id
                variants_to_persist[variant.pk] = variant

            notes = record.get('fitment_notes') or ''
            desired_compatibilities[(product_id, variant.pk)] = notes[:255]

        except Exception as e:
            stats['errors'] += 1
            logger.error(
                "Error procesando compatibilidad odoo_id=%s: %s",
                record.get('id'), e,
                exc_info=True,
            )

    if variants_to_persist:
        VariantVehiculo.objects.bulk_update(
            list(variants_to_persist.values()),
            ['odoo_variante_id'],
        )

    # ── 5. Reconciliar compatibilidades locales vs estado deseado ───────────
    existing_compatibilities = list(
        CompatibilidadProducto.objects
        .filter(producto_id__in=tmpl_to_product_id.values())
        .only('id', 'producto_id', 'variante_id', 'notas_instalacion')
    )
    existing_by_key = {
        (compat.producto_id, compat.variante_id): compat
        for compat in existing_compatibilities
    }

    to_create = []
    to_update = []

    for key, notes in desired_compatibilities.items():
        existing = existing_by_key.get(key)
        if existing is None:
            to_create.append(
                CompatibilidadProducto(
                    producto_id=key[0],
                    variante_id=key[1],
                    notas_instalacion=notes,
                )
            )
            continue

        if existing.notas_instalacion != notes:
            existing.notas_instalacion = notes
            to_update.append(existing)

    stale_ids = [
        compat.id
        for key, compat in existing_by_key.items()
        if key not in desired_compatibilities
    ]

    if to_create:
        CompatibilidadProducto.objects.bulk_create(to_create)
        stats['compat_created'] = len(to_create)

    if to_update:
        CompatibilidadProducto.objects.bulk_update(to_update, ['notas_instalacion'])
        stats['compat_updated'] = len(to_update)

    if stale_ids:
        deleted_count, _ = CompatibilidadProducto.objects.filter(id__in=stale_ids).delete()
        stats['compat_removed'] = deleted_count

    logger.info("%s compatibilidades: %s", provider.name, stats)
    status = 'success'
    if stats['errors'] or stats['skipped_no_variant']:
        status = 'partial'
    mark_sync_finished(provider, 'compatibility', started_at, status=status, metrics=stats)
    return stats


def _build_variant_maps(odoo_variant_ids: list[int], odoo_variant_map: dict) -> dict:
    """Prefetch de variantes Django para resolver compatibilidades sin queries por fila."""
    by_odoo_id = {
        variant.odoo_variante_id: variant
        for variant in VariantVehiculo.objects.filter(
            odoo_variante_id__in=set(odoo_variant_ids)
        )
    }

    django_pk_values = set()
    for record in odoo_variant_map.values():
        django_ext_id = record.get('django_external_id')
        if not django_ext_id:
            continue
        try:
            django_pk_values.add(int(django_ext_id))
        except (TypeError, ValueError):
            continue

    by_django_pk = VariantVehiculo.objects.in_bulk(django_pk_values)
    return {
        'by_odoo_id': by_odoo_id,
        'by_django_pk': by_django_pk,
    }


def _resolve_django_variant(
    odoo_variant_id: int | None,
    odoo_variant_map: dict,
    *,
    variant_maps: dict | None = None,
):
    """
    Resuelve un VariantVehiculo de Django a partir de su ID en Odoo.

    Estrategia en orden de prioridad:
      1. VariantVehiculo.odoo_variante_id == odoo_variant_id   (más rápido)
      2. vehiculo.variante.django_external_id → PK directo en Django
      3. Sin match → retorna None; loguea para que el operador ejecute
         el comando push_vehicles para poblar django_external_id.

    Args:
        odoo_variant_id:  ID de vehiculo.variante en Odoo
        odoo_variant_map: Resultado de connector.get_vehicle_variants()

    Returns:
        VariantVehiculo | None
    """
    if not odoo_variant_id:
        return None

    variant_maps = variant_maps or {'by_odoo_id': {}, 'by_django_pk': {}}

    # Estrategia 1: ya tenemos el odoo_variante_id en Django
    variant = variant_maps['by_odoo_id'].get(odoo_variant_id)
    if variant:
        return variant

    try:
        variant = VariantVehiculo.objects.get(odoo_variante_id=odoo_variant_id)
        variant_maps['by_odoo_id'][odoo_variant_id] = variant
        variant_maps['by_django_pk'][variant.pk] = variant
        return variant
    except VariantVehiculo.DoesNotExist:
        pass

    # Estrategia 2: usar django_external_id guardado en Odoo
    odoo_record = odoo_variant_map.get(odoo_variant_id)
    if odoo_record:
        django_ext_id = odoo_record.get('django_external_id')
        if django_ext_id:
            try:
                django_pk = int(django_ext_id)
                variant = variant_maps['by_django_pk'].get(django_pk)
                if variant:
                    return variant

                variant = VariantVehiculo.objects.get(pk=django_pk)
                variant_maps['by_django_pk'][django_pk] = variant
                if variant.odoo_variante_id:
                    variant_maps['by_odoo_id'][variant.odoo_variante_id] = variant
                return variant
            except (ValueError, TypeError, VariantVehiculo.DoesNotExist):
                pass

    # Estrategia 3: sin match seguro — no intentamos natural key para evitar
    # falsos positivos cuando existen múltiples variantes con config similar.
    logger.debug(
        "No se pudo resolver VariantVehiculo para odoo_variante_id=%s. "
        "Ejecutar push_vehicles para poblar django_external_id.",
        odoo_variant_id,
    )
    return None
