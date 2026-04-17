"""
services/categories.py
======================
Sincronización global del catálogo de categorías entre Django y Odoo.

Flujo objetivo:
    1. Django es maestro del árbol Category.
    2. push_categories() crea/vincula nodos en Odoo usando sync_key estable.
    3. Los syncs de productos solo consumen odoo_category_id ya persistido.
"""
import logging

logger = logging.getLogger(__name__)


def get_persisted_category_map(odoo_category_ids: set[int] | None = None) -> dict:
    """
    Retorna el mapa persistido en Django {odoo_category_id: Category}.

    Solo incluye categorías ya vinculadas con Odoo.
    """
    from apps.products.models import Category

    qs = Category.objects.filter(odoo_category_id__isnull=False)
    if odoo_category_ids:
        qs = qs.filter(odoo_category_id__in=odoo_category_ids)

    return {
        cat.odoo_category_id: cat
        for cat in qs.select_related('parent').order_by('level', 'tree_id', 'lft')
    }


def push_categories(odoo, stats: dict | None = None) -> dict:
    """
    Empuja el árbol global Category desde Django hacia Odoo.

    La vinculación estable usa Category.sync_key <-> product.category.django_sync_key.

    Args:
        odoo: Instancia OdooConnector autenticada.
        stats: Dict mutable para estadísticas.

    Returns:
        dict {odoo_category_id: Category instance}
    """
    from apps.products.models import Category

    if stats is None:
        stats = {}

    if not odoo.category_supports_sync_key():
        raise RuntimeError(
            "Odoo no expone product.category.django_sync_key. "
            "Ejecuta la actualización del módulo ecomparts_integration y vuelve a correr push_categories."
        )

    root_odoo_id = odoo.get_category_root_id()
    if not root_odoo_id:
        raise RuntimeError("No se pudo resolver la categoría raíz 'All' en Odoo")

    categories = Category.objects.all().select_related('parent').order_by('level', 'tree_id', 'lft')
    pushed_parent_ids = {}
    categ_map = {}

    for category in categories:
        if category.parent_id:
            parent_odoo_id = pushed_parent_ids.get(category.parent_id) or category.parent.odoo_category_id
            if not parent_odoo_id:
                stats['categories_errors'] = stats.get('categories_errors', 0) + 1
                logger.error(
                    "No se pudo empujar categoría %s porque su padre %s aún no tiene odoo_category_id",
                    category.name,
                    category.parent_id,
                )
                continue
        else:
            parent_odoo_id = root_odoo_id

        odoo_id, created, updated = odoo.push_category(
            name=category.name,
            django_sync_key=str(category.sync_key),
            parent_odoo_id=parent_odoo_id,
            is_active=category.is_active,
            odoo_category_id=category.odoo_category_id,
        )

        if category.odoo_category_id != odoo_id:
            category.odoo_category_id = odoo_id
            category.save(update_fields=['odoo_category_id'])
            updated = True

        pushed_parent_ids[category.pk] = odoo_id
        categ_map[odoo_id] = category

        if created:
            stats['categories_created'] = stats.get('categories_created', 0) + 1
        elif updated:
            stats['categories_updated'] = stats.get('categories_updated', 0) + 1
        else:
            stats['categories_linked'] = stats.get('categories_linked', 0) + 1

    logger.info(
        "Push categorías: +%d creadas / ~%d actualizadas / =%d vinculadas / !%d errores",
        stats.get('categories_created', 0),
        stats.get('categories_updated', 0),
        stats.get('categories_linked', 0),
        stats.get('categories_errors', 0),
    )
    return categ_map
