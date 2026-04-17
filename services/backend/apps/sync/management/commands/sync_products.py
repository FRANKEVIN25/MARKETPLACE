"""
Management command: sync_products
==================================
Capa delgada de CLI sobre apps/sync/services/products.py.

Toda la lógica de sincronización vive en:
  - apps/sync/services/products.py  → sync_provider_products(), sync_provider_stock()
    - apps/sync/services/categories.py → push_categories(), get_persisted_category_map()
  - apps/sync/services/compatibility.py → sync_provider_compatibility()

Este command solo se ocupa de:
  1. Parsear argumentos y determinar el conjunto de providers.
  2. Llamar al service correspondiente.
  3. Formatear el output para la terminal.

Uso:
  # Todos los providers activos y aprobados
  python manage.py sync_products

  # Provider específico
  python manage.py sync_products --provider-id=3

  # Dry-run: conecta a Odoo y reporta qué haría, sin guardar
  python manage.py sync_products --dry-run
  python manage.py sync_products --provider-id=3 --dry-run --limit=20

  # Solo productos sin compatibilidades (más rápido, p.ej. para actualizar precios)
  python manage.py sync_products --skip-compat

Nota sobre --dry-run:
    En modo dry-run el command conecta a Odoo y reporta cuántos productos
    crearía/actualizaría usando el mapa global de categorías ya persistido.
  Solo disponible con --limit en este modo.

Nota sobre --skip-compat:
  Omite la sincronización de autopart.compatibility.
  Útil cuando solo se necesita actualizar precios/stock y la jerarquía de
  compatibilidades no cambió.
"""
import logging

from django.core.management.base import BaseCommand

from apps.marketplace.models import Provider
from apps.sync.connector import get_odoo_connector_for_provider
from apps.sync.services.categories import get_persisted_category_map
from apps.sync.services.compatibility import sync_provider_compatibility
from apps.sync.services.products import sync_provider_products

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza productos (+ categorías + stock + compatibilidades) desde Odoo al marketplace'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider-id',
            type=int,
            default=None,
            help='ID del Provider específico a sincronizar',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Conecta a Odoo y reporta qué haría sin guardar cambios',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='(Solo dry-run) Límite de productos a inspeccionar',
        )
        parser.add_argument(
            '--skip-compat',
            action='store_true',
            help='Omite la sincronización de compatibilidades producto↔vehículo',
        )

    # ── handle ────────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        provider_id = options['provider_id']
        dry_run     = options['dry_run']
        limit       = options['limit']
        skip_compat = options['skip_compat']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 MODO DRY-RUN: No se guardarán cambios\n'))

        providers = self._get_providers(provider_id)
        if providers is None:
            return

        self.stdout.write(self.style.SUCCESS(
            f'\n📦 Sincronizando {providers.count()} provider(s)...\n'
        ))

        total = {
            'providers': 0,
            'categories_available': 0, 'categories_missing': 0,
            'products_created': 0,   'products_updated': 0,
            'images_updated': 0,     'images_errors': 0,
            'compat_created': 0,     'compat_updated': 0,
            'compat_removed': 0,
            'compat_skipped': 0,
            'errors': 0,
        }

        for provider in providers:
            self._print_provider_header(provider)

            if dry_run:
                self._handle_dry_run(provider, limit, skip_compat, total)
            else:
                self._handle_live(provider, skip_compat, total)

        self._print_summary(total, dry_run)

    # ── providers ─────────────────────────────────────────────────────────────

    def _get_providers(self, provider_id):
        if provider_id:
            qs = Provider.objects.filter(
                id=provider_id,
                is_active=True,
                odoo_company_id__isnull=False,
            )
            if not qs.exists():
                self.stdout.write(self.style.ERROR(
                    f'❌ Provider {provider_id} no existe, no está activo, '
                    'o no tiene odoo_company_id'
                ))
                return None
            return qs

        qs = Provider.objects.filter(
            is_active=True,
            is_approved=True,
            odoo_company_id__isnull=False,
        )
        if not qs.exists():
            self.stdout.write(self.style.ERROR('❌ No hay providers para sincronizar'))
            return None
        return qs

    # ── live sync (delegación total al service) ───────────────────────────────

    def _handle_live(self, provider, skip_compat, total):
        """
        Modo normal: delega a sync_provider_products() y decide si incluye
        compatibilidades según --skip-compat.
        """
        try:
            result = sync_provider_products(
                provider.id,
                include_compatibility=not skip_compat,
            )

            if 'error' in result:
                self.stdout.write(self.style.ERROR(
                    f'   ❌ Error: {result["error"]}'
                ))
                total['errors'] += 1
                return

            # Acumular estadísticas
            cats = result.get('categories', {})
            prods = result.get('products', {})
            images = result.get('images', {})
            compat = result.get('compatibility', {})

            total['categories_available'] += cats.get('available', 0)
            total['categories_missing'] += cats.get('missing', 0)
            total['products_created']   += prods.get('created', 0)
            total['products_updated']   += prods.get('updated', 0)
            total['images_updated']     += images.get('updated', 0)
            total['images_errors']      += images.get('errors', 0)
            total['compat_created']     += compat.get('created', 0)
            total['compat_updated']     += compat.get('updated', 0)
            total['compat_removed']     += compat.get('removed', 0)
            total['compat_skipped']     += compat.get('skipped', 0)
            total['errors']             += prods.get('errors', 0) + images.get('errors', 0) + compat.get('errors', 0)
            total['providers']          += 1

            # Resumen por provider
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Categorías globales disponibles: {cats.get("available", 0)}'
            ))
            if cats.get('missing', 0):
                self.stdout.write(self.style.WARNING(
                    f'   ⚠️  Categorías faltantes en Django: {cats.get("missing", 0)}'
                ))
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Productos:  +{prods.get("created", 0)} / ~{prods.get("updated", 0)}'
                f' (de {prods.get("total_odoo", "?")} en Odoo)'
            ))
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Imágenes:   ~{images.get("updated", 0)} / err {images.get("errors", 0)}'
            ))
            if not skip_compat:
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Compat:     +{compat.get("created", 0)} / ~{compat.get("updated", 0)}'
                    f' / -{compat.get("removed", 0)} / omitidas {compat.get("skipped", 0)}'
                ))
            if prods.get('errors', 0):
                self.stdout.write(self.style.WARNING(
                    f'   ⚠️  Errores productos: {prods["errors"]}'
                ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n   ❌ ERROR con {provider.name}: {e}\n'))
            logger.error('Error sincronizando provider %s: %s', provider.id, e, exc_info=True)
            total['errors'] += 1

    # ── dry-run (conecta a Odoo, cuenta, no guarda) ───────────────────────────

    def _handle_dry_run(self, provider, limit, skip_compat, total):
        """
        Conecta a Odoo, inspecciona productos y valida que sus categorías ya
        estén vinculadas globalmente en Django.
        """
        try:
            odoo = get_odoo_connector_for_provider(provider)
            self.stdout.write(self.style.SUCCESS(f'   ✅ Conectado a Odoo (UID: {odoo.uid})'))

            # Productos
            self.stdout.write('   📡 Obteniendo productos de Odoo...')
            odoo_products = odoo.get_products(
                company_id=provider.odoo_company_id,
                limit=limit,
            )
            self.stdout.write(self.style.SUCCESS(
                f'   ✅ Encontrados {len(odoo_products)} productos'
                f'{" (limitado a " + str(limit) + ")" if limit else ""}'
            ))

            root_category_id = odoo.get_category_root_id()

            needed_category_ids = {
                raw[0]
                for product in odoo_products
                if (raw := product.get('categ_id')) and isinstance(raw, (list, tuple)) and raw[0]
            }
            if root_category_id:
                needed_category_ids.discard(root_category_id)

            categ_map = get_persisted_category_map(needed_category_ids)
            missing_category_ids = sorted(needed_category_ids - set(categ_map.keys()))
            self.stdout.write(
                f'   📂 Categorías globales disponibles: {len(categ_map)} / faltantes: {len(missing_category_ids)}'
            )

            from apps.products.models import Product

            would_create = would_update = 0
            for op in odoo_products:
                exists = Product.objects.filter(
                    provider=provider,
                    odoo_product_id=op['id'],
                ).exists()
                if exists:
                    would_update += 1
                else:
                    would_create += 1

            self.stdout.write(
                f'   🔍 Productos a crear: {would_create} / a actualizar: {would_update}'
            )

            # Compatibilidades
            if not skip_compat:
                tmpl_ids_count = Product.objects.filter(
                    provider=provider,
                    odoo_template_id__isnull=False,
                ).count()
                compat_count = len(odoo.get_compatibilities(
                    list(
                        Product.objects
                        .filter(provider=provider, odoo_template_id__isnull=False)
                        .values_list('odoo_template_id', flat=True)
                    )
                )) if tmpl_ids_count else 0
                self.stdout.write(
                    f'   🚗 Compatibilidades en Odoo: {compat_count}'
                )

            total['categories_available'] += len(categ_map)
            total['categories_missing'] += len(missing_category_ids)
            total['products_created']   += would_create
            total['products_updated']   += would_update
            total['providers']          += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n   ❌ ERROR (dry-run) con {provider.name}: {e}\n'))
            logger.error('Error dry-run provider %s: %s', provider.id, e, exc_info=True)
            total['errors'] += 1

    # ── helpers de output ─────────────────────────────────────────────────────

    def _print_provider_header(self, provider):
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write(f'🏢 Provider: {provider.name} ({provider.get_tier_display()})')
        self.stdout.write(f'   Odoo Company ID: {provider.odoo_company_id}')
        self.stdout.write(f'{"=" * 60}\n')

    def _print_summary(self, total, dry_run):
        self.stdout.write(f'\n{"=" * 60}')
        label = '🔍 DRY-RUN COMPLETADO' if dry_run else '✅ SINCRONIZACIÓN COMPLETADA'
        self.stdout.write(self.style.SUCCESS(label))
        self.stdout.write(f'{"=" * 60}')
        self.stdout.write(f'Providers procesados:       {total["providers"]}')
        self.stdout.write(
            f'Categorías disp./faltantes: {total["categories_available"]} / {total["categories_missing"]}'
        )
        self.stdout.write(
            f'Productos creados/upd:      {total["products_created"]} / {total["products_updated"]}'
        )
        self.stdout.write(f'Imágenes refrescadas:       {total["images_updated"]}')
        self.stdout.write(
            f'Compat creadas/upd:         {total["compat_created"]} / {total["compat_updated"]}'
        )
        self.stdout.write(f'Compat removidas:           {total["compat_removed"]}')
        self.stdout.write(f'Compat omitidas (sin match):{total["compat_skipped"]}')
        self.stdout.write(f'Errores:                    {total["errors"]}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se guardaron cambios'))
        self.stdout.write('')
