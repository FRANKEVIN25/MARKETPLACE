"""
services/products.py
====================
Sincronización de productos y stock de Odoo → Django.

Incluye:
        - sync_provider_catalog_snapshot(): snapshot de catálogo estable + stock agregado
        - sync_provider_product_images(): sync diferencial de imágenes Odoo → Cloudinary → Django
        - sync_provider_products(): sync completa (snapshot catálogo → compat)
  - sync_provider_stock(): actualización rápida de stock sin tocar metadatos
  - _resolve_reference(): protección anti-duplicación de references en Odoo
"""
import base64
import logging

from django.utils import timezone

from apps.marketplace.models import Provider
from apps.products.models import Product
from apps.sync.connector import get_odoo_connector_for_provider

from .categories import get_persisted_category_map
from .compatibility import sync_provider_compatibility
from .observability import mark_sync_finished, mark_sync_started

logger = logging.getLogger(__name__)


def sync_provider_catalog_snapshot(provider_id: int, *, include_images: bool = False) -> dict:
    """
    Sincroniza el snapshot de catálogo estable de un provider.

    Incluye catálogo técnico-comercial, stock agregado y reconciliación de
    productos faltantes en el snapshot Odoo. Compatibilidades quedan fuera.

    Args:
        provider_id: Provider a sincronizar
        include_images: Si es True también resuelve/sube imágenes en esta corrida

    Returns:
        dict con estadísticas de la sincronización
    """
    provider = _get_sync_provider(provider_id)
    if provider is None:
        logger.error("Provider %s no existe o no está activo/aprobado", provider_id)
        return {'error': 'Provider no encontrado'}

    logger.info("Iniciando snapshot de catálogo para %s", provider.name)
    started_at = mark_sync_started(provider, 'catalog')

    odoo = get_odoo_connector_for_provider(provider)
    now = timezone.now()

    stats = _build_sync_stats(provider.name)

    try:
        odoo_products = odoo.get_products(
            company_id=provider.odoo_company_id,
            include_inactive=True,
        )
    except Exception as e:
        logger.error("Error obteniendo productos de Odoo para %s: %s", provider.name, e)
        mark_sync_finished(
            provider,
            'catalog',
            started_at,
            status='failed',
            metrics=stats,
            error_message=str(e),
        )
        return {**stats, 'error': str(e)}

    category_resolution = _resolve_catalog_categories(odoo, odoo_products, stats)
    if 'error' in category_resolution:
        mark_sync_finished(
            provider,
            'catalog',
            started_at,
            status='failed',
            metrics=stats,
            error_message=category_resolution['error'],
        )
        return {**stats, 'error': category_resolution['error']}

    _sync_catalog_products(
        provider=provider,
        odoo_products=odoo_products,
        categ_map=category_resolution['categ_map'],
        root_category_id=category_resolution['root_category_id'],
        now=now,
        stats=stats,
        include_images=include_images,
    )

    _refresh_provider_total_products(provider)

    logger.info("Snapshot de catálogo para %s: %s", provider.name, stats)
    mark_sync_finished(
        provider,
        'catalog',
        started_at,
        status='partial' if stats['products']['errors'] else 'success',
        metrics=stats,
    )
    return stats


def sync_provider_product_images(provider_id: int, *, force: bool = False) -> dict:
    """
    Sincroniza imágenes de producto de forma diferencial.

    Usa una señal remota liviana (`x_image_version`) para decidir si vale la pena
    pedir `image_1920` y reenviar la imagen a Cloudinary. `x_image_version` solo
    cambia cuando `image_1920` se modifica, eliminando falsos positivos por cambios
    de precio, descripción u otros campos del producto.
    """
    provider = _get_sync_provider(provider_id)
    if provider is None:
        logger.error("Provider %s no existe o no está activo/aprobado", provider_id)
        return {'error': 'Provider no encontrado'}

    logger.info("Iniciando sync diferencial de imágenes para %s", provider.name)
    started_at = mark_sync_started(provider, 'images')
    odoo = get_odoo_connector_for_provider(provider)
    stats = {
        'provider': provider.name,
        'images': {'scanned': 0, 'candidates': 0, 'updated': 0, 'cleared': 0, 'skipped': 0, 'errors': 0},
    }

    try:
        remote_products = odoo.get_products(
            company_id=provider.odoo_company_id,
            fields=['id', 'default_code', 'x_image_version'],
            include_inactive=True,
        )
    except Exception as e:
        logger.error("Error obteniendo metadata de imágenes de Odoo para %s: %s", provider.name, e)
        mark_sync_finished(
            provider,
            'images',
            started_at,
            status='failed',
            metrics=stats,
            error_message=str(e),
        )
        return {**stats, 'error': str(e)}

    stats['images']['scanned'] = len(remote_products)
    if not remote_products:
        logger.info("%s — no hay productos remotos para evaluar imágenes", provider.name)
        mark_sync_finished(provider, 'images', started_at, status='success', metrics=stats)
        return stats

    local_products = Product.objects.filter(
        provider=provider,
        odoo_product_id__in=[product['id'] for product in remote_products],
    ).only(
        'id',
        'odoo_product_id',
        'image_url',
        'image_cloudinary_id',
        'odoo_image_version',
    )
    local_by_odoo_id = {
        product.odoo_product_id: product
        for product in local_products
    }

    candidate_ids = []
    remote_version_by_id = {}
    for remote_product in remote_products:
        remote_odoo_id = remote_product['id']
        local_product = local_by_odoo_id.get(remote_odoo_id)
        if local_product is None:
            stats['images']['skipped'] += 1
            continue

        remote_version = remote_product.get('x_image_version') or None
        remote_version_by_id[remote_odoo_id] = remote_version
        if force or _product_needs_image_refresh(local_product, remote_version):
            candidate_ids.append(remote_odoo_id)
        else:
            stats['images']['skipped'] += 1

    stats['images']['candidates'] = len(candidate_ids)
    if not candidate_ids:
        logger.info("%s — no hay imágenes candidatas para refrescar", provider.name)
        mark_sync_finished(provider, 'images', started_at, status='success', metrics=stats)
        return stats

    payloads = odoo.get_products_by_ids(
        candidate_ids,
        fields=['id', 'default_code', 'x_image_version', 'image_1920'],
        include_inactive=True,
    )
    payload_by_odoo_id = {
        payload['id']: payload
        for payload in payloads
    }

    products_to_update = []
    for remote_odoo_id in candidate_ids:
        local_product = local_by_odoo_id.get(remote_odoo_id)
        payload = payload_by_odoo_id.get(remote_odoo_id)
        if local_product is None or payload is None:
            stats['images']['errors'] += 1
            logger.warning(
                "%s — no se pudo resolver payload de imagen para odoo_product_id=%s",
                provider.name,
                remote_odoo_id,
            )
            continue

        try:
            image_url, image_cloudinary_id, refreshed = _resolve_image_fields_for_sync(
                payload,
                local_product,
            )
            if not refreshed:
                stats['images']['errors'] += 1
                continue

            had_image = bool(local_product.image_url or local_product.image_cloudinary_id)
            has_image_now = bool(image_url or image_cloudinary_id)

            local_product.image_url = image_url
            local_product.image_cloudinary_id = image_cloudinary_id
            local_product.odoo_image_version = remote_version_by_id.get(remote_odoo_id)
            products_to_update.append(local_product)

            if has_image_now:
                stats['images']['updated'] += 1
            elif had_image and not has_image_now:
                stats['images']['cleared'] += 1
            else:
                stats['images']['skipped'] += 1

        except Exception as e:
            logger.error(
                "Error sincronizando imagen odoo_product_id=%s: %s",
                remote_odoo_id,
                e,
            )
            stats['images']['errors'] += 1

    if products_to_update:
        Product.objects.bulk_update(
            products_to_update,
            ['image_url', 'image_cloudinary_id', 'odoo_image_version'],
        )

    logger.info("Sync diferencial de imágenes para %s: %s", provider.name, stats)
    mark_sync_finished(
        provider,
        'images',
        started_at,
        status='partial' if stats['images']['errors'] else 'success',
        metrics=stats,
    )
    return stats


def sync_provider_products(provider_id: int, include_compatibility: bool = True) -> dict:
    """
    Sincronización completa del provider.

    Orquesta dos fases:
      1. Snapshot de catálogo estable + stock agregado
      2. Compatibilidades, opcionalmente

    Returns:
        dict con estadísticas de la sincronización
    """
    stats = sync_provider_catalog_snapshot(provider_id, include_images=False)
    if 'error' in stats:
        return stats

    image_stats = sync_provider_product_images(provider_id)
    if 'error' in image_stats:
        stats['images'] = {'scanned': 0, 'candidates': 0, 'updated': 0, 'cleared': 0, 'skipped': 0, 'errors': 1}
    else:
        stats['images'] = image_stats.get('images', {})

    if include_compatibility:
        compat_stats = sync_provider_compatibility(provider_id)
        stats['compatibility'] = {
            'created': compat_stats.get('compat_created', 0),
            'updated': compat_stats.get('compat_updated', 0),
            'removed': compat_stats.get('compat_removed', 0),
            'skipped': (
                compat_stats.get('skipped_no_product', 0)
                + compat_stats.get('skipped_no_variant', 0)
            ),
            'errors': compat_stats.get('errors', 0),
        }
    else:
        logger.info(
            "%s — compatibilidades omitidas en sync_provider_products()",
            stats['provider'],
        )

    logger.info("Sync completa para %s: %s", stats['provider'], stats)
    return stats


def sync_provider_stock(provider_id: int) -> dict:
    """
    Actualiza únicamente total_stock_cached consultando qty_available en Odoo.
    Más rápido que la sync completa: no toca categorías ni metadatos de producto.

    Returns:
        dict con métricas de actualización de stock
    """
    provider = _get_sync_provider(provider_id)
    if provider is None:
        return {'error': 'Provider no encontrado'}

    started_at = mark_sync_started(provider, 'stock')

    try:
        odoo = get_odoo_connector_for_provider(provider)
        odoo_products = odoo.get_products(
            company_id=provider.odoo_company_id,
            fields=['id', 'qty_available'],
            include_inactive=True,
        )
    except Exception as e:
        logger.error("Error obteniendo productos de Odoo (stock) para %s: %s", provider.name, e)
        mark_sync_finished(
            provider,
            'stock',
            started_at,
            status='failed',
            error_message=str(e),
        )
        return {'error': str(e)}

    stats = {
        'scanned': len(odoo_products),
        'updated': 0,
        'unchanged': 0,
        'missing_local': 0,
        'errors': 0,
    }

    remote_stock_by_odoo_id = {
        product['id']: int(product.get('qty_available') or 0)
        for product in odoo_products
        if product.get('id')
    }

    if not remote_stock_by_odoo_id:
        logger.info("Stock actualizado para %s: %s", provider.name, stats)
        mark_sync_finished(provider, 'stock', started_at, status='success', metrics=stats)
        return stats

    local_products = Product.objects.filter(
        provider=provider,
        odoo_product_id__in=remote_stock_by_odoo_id.keys(),
    ).only('id', 'odoo_product_id', 'total_stock_cached')
    local_by_odoo_id = {
        product.odoo_product_id: product
        for product in local_products
    }

    products_to_update = []
    for odoo_product_id, qty_available in remote_stock_by_odoo_id.items():
        local_product = local_by_odoo_id.get(odoo_product_id)
        if local_product is None:
            stats['missing_local'] += 1
            continue

        if local_product.total_stock_cached == qty_available:
            stats['unchanged'] += 1
            continue

        local_product.total_stock_cached = qty_available
        products_to_update.append(local_product)

    try:
        if products_to_update:
            Product.objects.bulk_update(products_to_update, ['total_stock_cached'])
            stats['updated'] = len(products_to_update)
    except Exception as e:
        logger.error("Error aplicando bulk_update de stock para %s: %s", provider.name, e)
        stats['errors'] += len(products_to_update)

    logger.info("Stock actualizado para %s: %s", provider.name, stats)
    mark_sync_finished(
        provider,
        'stock',
        started_at,
        status='partial' if stats['errors'] else 'success',
        metrics=stats,
    )
    return stats


# ── Helpers privados ─────────────────────────────────────────────────────────

def _get_sync_provider(provider_id: int) -> Provider | None:
    """Retorna un provider elegible para sync o None si no aplica."""
    try:
        return Provider.objects.get(id=provider_id, is_active=True, is_approved=True)
    except Provider.DoesNotExist:
        return None


def _build_sync_stats(provider_name: str) -> dict:
    """Estructura base de estadísticas para sync de productos."""
    return {
        'provider': provider_name,
        'categories': {'available': 0, 'missing': 0},
        'products': {'total_odoo': 0, 'created': 0, 'updated': 0, 'deactivated': 0, 'errors': 0},
        'images': {'scanned': 0, 'candidates': 0, 'updated': 0, 'cleared': 0, 'skipped': 0, 'errors': 0},
        'stock': {'updated': 0, 'errors': 0},
        'compatibility': {'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0},
    }


def _resolve_catalog_categories(odoo, odoo_products: list[dict], stats: dict) -> dict:
    """Construye el mapa de categorías persistidas requerido por el snapshot."""
    root_category_id = odoo.get_category_root_id()

    needed_category_ids = {
        raw[0]
        for product in odoo_products
        if (raw := product.get('categ_id')) and isinstance(raw, (list, tuple)) and raw[0]
    }
    if root_category_id:
        needed_category_ids.discard(root_category_id)

    categ_map = get_persisted_category_map(needed_category_ids)
    stats['categories']['available'] = len(categ_map)

    missing_category_ids = sorted(needed_category_ids - set(categ_map.keys()))
    if missing_category_ids:
        logger.error(
            "Faltan categorías globales vinculadas en Django para los IDs Odoo: %s",
            missing_category_ids,
        )
        stats['categories']['missing'] = len(missing_category_ids)
        return {
            'error': (
                'Faltan categorías globales vinculadas en Django. '
                'Ejecuta push_categories para normalizar el catálogo.'
            ),
        }

    return {
        'root_category_id': root_category_id,
        'categ_map': categ_map,
    }


def _sync_catalog_products(
    *,
    provider: Provider,
    odoo_products: list[dict],
    categ_map: dict,
    root_category_id: int | None,
    now,
    stats: dict,
    include_images: bool,
) -> None:
    """Persiste el snapshot de catálogo estable de productos para un provider."""
    stats['products']['total_odoo'] = len(odoo_products)

    existing_by_odoo_id = _load_existing_products_by_odoo_id(provider)
    used_references = _load_provider_used_references(provider)
    snapshot_odoo_product_ids = set()

    for odoo_product in odoo_products:
        try:
            snapshot_odoo_product_ids.add(odoo_product['id'])
            existing_product = existing_by_odoo_id.get(odoo_product['id'])
            defaults = _build_product_defaults(
                odoo_product=odoo_product,
                existing_product=existing_product,
                used_references=used_references,
                categ_map=categ_map,
                root_category_id=root_category_id,
                now=now,
                include_images=include_images,
            )

            product, created = Product.objects.update_or_create(
                provider=provider,
                odoo_product_id=odoo_product['id'],
                defaults=defaults,
            )

            existing_by_odoo_id[odoo_product['id']] = product

            if created:
                stats['products']['created'] += 1
            else:
                stats['products']['updated'] += 1

        except Exception as e:
            logger.error(
                "Error sincronizando producto odoo_id=%s: %s",
                odoo_product.get('id'), e,
            )
            stats['products']['errors'] += 1

    stats['products']['deactivated'] = _deactivate_missing_products(
        provider,
        snapshot_odoo_product_ids,
        now,
    )
    stats['stock']['updated'] = (
        stats['products']['created'] + stats['products']['updated']
    )
    logger.info(
        "%s — snapshot catálogo: +%d / ~%d / -%d / err %d",
        provider.name,
        stats['products']['created'],
        stats['products']['updated'],
        stats['products']['deactivated'],
        stats['products']['errors'],
    )


def _load_existing_products_by_odoo_id(provider: Provider) -> dict[int, Product]:
    """Retorna productos actuales del provider indexados por odoo_product_id."""
    existing_products = Product.objects.filter(
        provider=provider,
        odoo_product_id__isnull=False,
    ).only(
        'id',
        'odoo_product_id',
        'reference',
        'image_url',
        'image_cloudinary_id',
    )
    return {
        product.odoo_product_id: product
        for product in existing_products
    }


def _load_provider_used_references(provider: Provider) -> dict[str, int | None]:
    """Retorna referencias ocupadas del provider para evitar colisiones locales."""
    provider_reference_rows = Product.objects.filter(
        provider=provider,
    ).exclude(
        reference__isnull=True,
    ).exclude(
        reference='',
    ).values_list('reference', 'odoo_product_id')
    return {
        reference: odoo_product_id
        for reference, odoo_product_id in provider_reference_rows
    }


def _build_product_defaults(
    *,
    odoo_product: dict,
    existing_product: Product | None,
    used_references: dict[str, int | None],
    categ_map: dict,
    root_category_id: int | None,
    now,
    include_images: bool,
) -> dict:
    """Construye defaults de Product a partir del snapshot Odoo."""
    image_url = image_cloudinary_id = None
    if include_images:
        image_url, image_cloudinary_id = _resolve_image_fields(
            odoo_product,
            existing_product,
        )
    elif existing_product:
        image_url = existing_product.image_url
        image_cloudinary_id = existing_product.image_cloudinary_id

    reference = _resolve_reference(odoo_product, used_references)
    if reference:
        used_references[reference] = odoo_product['id']

    qty_available = int(odoo_product.get('qty_available') or 0)
    tmpl_raw = odoo_product.get('product_tmpl_id')
    tmpl_id = tmpl_raw[0] if isinstance(tmpl_raw, (list, tuple)) else tmpl_raw

    return {
        'name': odoo_product['name'],
        'reference': reference,
        'description': odoo_product.get('description_sale') or '',
        'price': odoo_product.get('list_price', 0),
        'manufacturer_code': odoo_product.get('autopart_oem_code') or None,
        'image_url': image_url,
        'image_cloudinary_id': image_cloudinary_id,
        'product_type': odoo_product.get('type', 'product'),
        'category': _resolve_product_category(odoo_product, categ_map, root_category_id),
        'is_active': odoo_product.get('active', True),
        'es_universal': bool(odoo_product.get('autopart_universal')),
        'autopart_side': odoo_product.get('autopart_side') or 'na',
        'autopart_quality': (
            odoo_product.get('autopart_quality') or 'aftermarket_standard'
        ),
        'odoo_template_id': tmpl_id,
        'odoo_state': 'synced',
        'last_sync_at': now,
        'total_stock_cached': qty_available,
    }


def _resolve_product_category(odoo_product: dict, categ_map: dict, root_category_id: int | None):
    """Resuelve la categoría Django a partir de categ_id del snapshot Odoo."""
    categ_raw = odoo_product.get('categ_id')
    if not categ_raw or not isinstance(categ_raw, (list, tuple)) or not categ_raw[0]:
        return None

    if root_category_id and categ_raw[0] == root_category_id:
        return None

    return categ_map.get(categ_raw[0])


def _refresh_provider_total_products(provider: Provider) -> None:
    """Actualiza el contador denormalizado de productos activos del provider."""
    provider.total_products = Product.objects.filter(
        provider=provider,
        is_active=True,
    ).count()
    provider.save(update_fields=['total_products'])


def _product_needs_image_refresh(product: Product, remote_version: str | None) -> bool:
    """Decide si conviene pedir la imagen remota para un producto."""
    if not product.image_url or not product.image_cloudinary_id:
        return True

    if not remote_version:
        return False

    return product.odoo_image_version != remote_version

def _deactivate_missing_products(provider: Provider, snapshot_odoo_product_ids: set[int], now) -> int:
    """
    Desactiva productos sincronizados que ya no aparecen en el snapshot Odoo.

    Se usa como reconciliación defensiva para productos removidos del alcance
    del provider o inexistentes en el payload nocturno.
    """
    stale_qs = Product.objects.filter(
        provider=provider,
        odoo_product_id__isnull=False,
    )

    if not snapshot_odoo_product_ids:
        if stale_qs.exists():
            logger.warning(
                "%s — snapshot Odoo vacío; se omite desactivación masiva por seguridad.",
                provider.name,
            )
        return 0

    updated_rows = stale_qs.exclude(
        odoo_product_id__in=snapshot_odoo_product_ids,
    ).update(
        is_active=False,
        total_stock_cached=0,
        last_sync_at=now,
    )

    if updated_rows:
        logger.info(
            "%s — %d producto(s) desactivado(s) por no venir en el snapshot Odoo.",
            provider.name,
            updated_rows,
        )
    return updated_rows

def _resolve_image_fields(odoo_product: dict, existing_product: Product | None) -> tuple:
    """
    Resuelve qué imagen guardar localmente.

    Reglas:
      - Si Odoo no tiene imagen, Django también queda sin imagen.
      - Si la subida a Cloudinary falla, se conserva la imagen actual en Django.
    """
    image_b64 = odoo_product.get('image_1920')
    if not image_b64 or image_b64 is False:
        return None, None

    try:
        return _upload_image(odoo_product)
    except Exception as e:
        logger.warning(
            "No se pudo refrescar imagen para odoo_product_id=%s: %s. Se conserva la actual.",
            odoo_product.get('id'),
            e,
        )
        if existing_product:
            return existing_product.image_url, existing_product.image_cloudinary_id
        return None, None


def _resolve_image_fields_for_sync(
    odoo_product: dict,
    existing_product: Product | None,
) -> tuple[str | None, str | None, bool]:
    """
    Variante de sync diferencial que informa si la resolución quedó lista.

    Returns:
        tuple(image_url, image_cloudinary_id, refreshed)
    """
    image_b64 = odoo_product.get('image_1920')
    if not image_b64 or image_b64 is False:
        return None, None, True

    try:
        image_url, image_cloudinary_id = _upload_image(odoo_product)
        return image_url, image_cloudinary_id, True
    except Exception as e:
        logger.warning(
            "No se pudo refrescar imagen para odoo_product_id=%s: %s. Se conserva la actual.",
            odoo_product.get('id'),
            e,
        )
        if existing_product:
            return existing_product.image_url, existing_product.image_cloudinary_id, False
        return None, None, False


def _upload_image(odoo_product: dict) -> tuple:
    """
    Sube la imagen del producto a Cloudinary si está presente en Odoo.

    Returns:
        (image_url, image_cloudinary_id) — ambos None si no hay imagen.

    Raises:
        Exception: si Cloudinary rechaza la subida o la imagen no puede decodificarse.
    """
    image_b64 = odoo_product.get('image_1920')
    if not image_b64 or image_b64 is False:
        return None, None

    import cloudinary.uploader

    image_data = base64.b64decode(image_b64)
    product_ref = odoo_product.get('default_code') or str(odoo_product['id'])
    result = cloudinary.uploader.upload(
        image_data,
        public_id=f"ecomparts/products/{product_ref}",
        overwrite=True,
        resource_type="image",
        transformation=[{
            "width": 800, "height": 800,
            "crop": "limit", "quality": "auto",
            "fetch_format": "auto",
        }],
    )
    url = result.get('secure_url')
    public_id = result.get('public_id')
    logger.info("Imagen subida a Cloudinary: %s", url)
    return url, public_id


def _resolve_reference(odoo_product: dict, used_references: dict[str, int | None]) -> str | None:
    """
    Devuelve la referencia a usar para el producto.

    Si la referencia raw de Odoo ya está asignada a otro producto diferente del
    mismo provider (referencia duplicada en Odoo), devuelve el fallback
    ``ODOO-{odoo_product_id}`` con sufijo incremental si hace falta, para
    evitar colisiones en la columna UNIQUE.
    """
    raw = odoo_product.get('default_code') or None
    if raw is None:
        return None

    current_odoo_id = odoo_product['id']
    conflict = _reference_has_conflict(raw, current_odoo_id, used_references)

    if conflict:
        fallback = _build_unique_reference_fallback(current_odoo_id, used_references)
        logger.warning(
            "Referencia duplicada en Odoo '%s' (odoo_id=%s, odoo_id_conflictivo=%s). "
            "Usando fallback '%s'.",
            raw, current_odoo_id, used_references.get(raw), fallback,
        )
        return fallback

    return raw


def _reference_has_conflict(candidate: str, current_odoo_id: int, used_references: dict[str, int | None]) -> bool:
    """Indica si una referencia ya está ocupada por otro producto del provider."""
    if candidate not in used_references:
        return False

    existing_odoo_id = used_references.get(candidate)
    return existing_odoo_id is None or existing_odoo_id != current_odoo_id


def _build_unique_reference_fallback(current_odoo_id: int, used_references: dict[str, int | None]) -> str:
    """Genera un fallback de referencia sin colisionar con referencias existentes."""
    base_fallback = f"ODOO-{current_odoo_id}"
    candidate = base_fallback
    counter = 1

    while _reference_has_conflict(candidate, current_odoo_id, used_references):
        candidate = f"{base_fallback}-{counter}"
        counter += 1

    return candidate
