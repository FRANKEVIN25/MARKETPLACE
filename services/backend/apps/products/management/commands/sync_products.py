"""
Comando para sincronizar productos, categorías, almacenes, stock y compatibilidades desde Odoo.
Útil para devops, migraciones manuales y debugging.
Soporta --dry-run, --limit, --skip-stock y --skip-compat.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.marketplace.models import Provider
from apps.products.models import Product, Category, Warehouse, StockItem, CompatibilidadProducto
from apps.vehicles.models import VariantVehiculo
from apps.sync.odoo_connector import get_odoo_connector_for_provider
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza productos (+ categorías + almacenes + stock) desde Odoo al marketplace'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider-id',
            type=int,
            help='ID del Provider específico a sincronizar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la sincronización sin guardar cambios'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Límite de productos a sincronizar'
        )
        parser.add_argument(
            '--skip-stock',
            action='store_true',
            help='Omite la sincronización de stock (más rápido si solo quieres productos)'
        )
        parser.add_argument(
            '--skip-compat',
            action='store_true',
            help='Omite la sincronización de compatibilidades producto↔vehículo'
        )

    def handle(self, *args, **options):
        dry_run    = options.get('dry_run', False)
        provider_id = options.get('provider_id')
        limit      = options.get('limit')
        skip_stock = options.get('skip_stock', False)
        skip_compat = options.get('skip_compat', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 MODO DRY-RUN: No se guardarán cambios\n'))

        # ── Determinar providers ──────────────────────────────────────────────
        if provider_id:
            providers = Provider.objects.filter(
                id=provider_id,
                is_active=True,
                odoo_company_id__isnull=False
            )
            if not providers.exists():
                self.stdout.write(self.style.ERROR(
                    f'❌ Provider {provider_id} no existe, no está activo, o no tiene odoo_company_id'
                ))
                return
        else:
            providers = Provider.objects.filter(
                is_active=True,
                is_approved=True,
                odoo_company_id__isnull=False
            )

        if not providers.exists():
            self.stdout.write(self.style.ERROR('❌ No hay providers para sincronizar'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'\n📦 Sincronizando {providers.count()} provider(s)...\n'
        ))

        total_stats = {
            'providers': 0,
            'categories_created': 0, 'categories_updated': 0,
            'warehouses_created': 0, 'warehouses_updated': 0,
            'products_created': 0,   'products_updated': 0,
            'stock_updated': 0,
            'compat_created': 0,     'compat_updated': 0,
            'compat_skipped': 0,
            'errors': 0,
        }

        for provider in providers:
            self.stdout.write(f'\n{"=" * 60}')
            self.stdout.write(f'🏢 Provider: {provider.name} ({provider.get_tier_display()})')
            self.stdout.write(f'   Odoo Company ID: {provider.odoo_company_id}')
            self.stdout.write(f'{"=" * 60}\n')

            try:
                odoo = get_odoo_connector_for_provider(provider)
                self.stdout.write(self.style.SUCCESS(f'   ✅ Conectado a Odoo (UID: {odoo.uid})'))

                # ── 1. CATEGORÍAS ─────────────────────────────────────────────
                odoo_categ_map = self._sync_categories(odoo, dry_run, total_stats)

                # ── 2. ALMACENES ──────────────────────────────────────────────
                warehouse_map, location_map = self._sync_warehouses(
                    odoo, provider, dry_run, total_stats
                )

                # ── 3. PRODUCTOS ──────────────────────────────────────────────
                self.stdout.write('   📡 Obteniendo productos de Odoo...')
                odoo_products = odoo.get_products(
                    company_id=provider.odoo_company_id,
                    limit=limit
                )
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Encontrados {len(odoo_products)} productos\n'
                ))

                p_stats = {'created': 0, 'updated': 0, 'errors': 0}
                now = timezone.now()

                for idx, op in enumerate(odoo_products, 1):
                    try:
                        # Resolver categoría por odoo_category_id
                        # NO por nombre ni por PK: si Odoo recrea la DB los IDs
                        # cambian, pero odoo_category_id en Category sigue siendo
                        # el ancla correcta.
                        categ_raw = op.get('categ_id')
                        category = None
                        if categ_raw and isinstance(categ_raw, (list, tuple)) and categ_raw[0]:
                            category = odoo_categ_map.get(categ_raw[0])

                        # Resolver product_tmpl_id
                        tmpl_raw = op.get('product_tmpl_id')
                        tmpl_id = tmpl_raw[0] if isinstance(tmpl_raw, (list, tuple)) else tmpl_raw

                        product_data = {
                            'name':            op['name'],
                            'reference':       op.get('default_code') or f'ODOO-{op["id"]}',
                            'description':     op.get('description_sale') or '',
                            'price':           op.get('list_price', 0),
                            'product_type':    op.get('type', 'product'),
                            'category':        category,
                            'is_active':       op.get('active', True),
                            'odoo_product_id': op['id'],
                            'odoo_template_id': tmpl_id,
                            'odoo_state':      'synced',
                            'last_sync_at':    now,
                        }

                        existing = Product.objects.filter(
                            provider=provider,
                            odoo_id=op['id']
                        ).first()

                        if dry_run:
                            action = '🔄 Actualizar' if existing else '✨ Crear'
                            if existing:
                                p_stats['updated'] += 1
                            else:
                                p_stats['created'] += 1
                        else:
                            if existing:
                                for key, value in product_data.items():
                                    setattr(existing, key, value)
                                existing.save()
                                action = '🔄 Actualizado'
                                p_stats['updated'] += 1
                            else:
                                Product.objects.create(
                                    provider=provider,
                                    odoo_id=op['id'],
                                    **product_data
                                )
                                action = '✨ Creado'
                                p_stats['created'] += 1

                        if idx % 10 == 0 or idx == 1:
                            cat_name = category.name if category else '—'
                            self.stdout.write(
                                f'   [{idx}/{len(odoo_products)}] {action}: {op["name"][:45]} '
                                f'| Cat: {cat_name} '
                                f'| S/ {op.get("list_price", 0):.2f}'
                            )

                    except Exception as e:
                        p_stats['errors'] += 1
                        self.stdout.write(self.style.ERROR(
                            f'   ❌ Error con producto {op.get("name", "N/A")}: {e}'
                        ))
                        logger.error(f"Error sincronizando producto {op['id']}: {e}", exc_info=True)

                total_stats['products_created'] += p_stats['created']
                total_stats['products_updated'] += p_stats['updated']
                total_stats['errors']           += p_stats['errors']

                # ── 4. STOCK POR ALMACÉN ──────────────────────────────────────
                if not skip_stock and not dry_run:
                    self._sync_stock(odoo, provider, warehouse_map, location_map, total_stats)

                # ── 5. COMPATIBILIDADES PRODUCTO ↔ VEHÍCULO ──────────────────
                if not skip_compat and not dry_run:
                    self._sync_compatibility(odoo, provider, total_stats)

                # Actualizar contador del provider
                if not dry_run:
                    provider.total_products = Product.objects.filter(
                        provider=provider, is_active=True
                    ).count()
                    provider.save(update_fields=['total_products'])

                # Resumen del provider
                self.stdout.write(f'\n   📊 Resumen de {provider.name}:')
                self.stdout.write(f'      📂 Categorías creadas/upd: '
                                  f'{total_stats["categories_created"]} / {total_stats["categories_updated"]}')
                self.stdout.write(f'      🏭 Almacenes creados/upd: '
                                  f'{total_stats["warehouses_created"]} / {total_stats["warehouses_updated"]}')
                self.stdout.write(f'      ✨ Productos creados:      {p_stats["created"]}')
                self.stdout.write(f'      🔄 Productos actualizados: {p_stats["updated"]}')
                self.stdout.write(f'      ❌ Errores:                {p_stats["errors"]}')

                total_stats['providers'] += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'\n   ❌ ERROR con {provider.name}: {e}\n'))
                logger.error(f"Error sincronizando provider {provider.id}: {e}", exc_info=True)

        # ── Resumen final ──────────────────────────────────────────────────────
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write(self.style.SUCCESS('✅ SINCRONIZACIÓN COMPLETADA'))
        self.stdout.write(f'{"=" * 60}')
        self.stdout.write(f'Providers procesados:       {total_stats["providers"]}')
        self.stdout.write(f'Categorías creadas/upd:     {total_stats["categories_created"]} / {total_stats["categories_updated"]}')
        self.stdout.write(f'Almacenes creados/upd:      {total_stats["warehouses_created"]} / {total_stats["warehouses_updated"]}')
        self.stdout.write(f'Productos creados/upd:      {total_stats["products_created"]} / {total_stats["products_updated"]}')
        self.stdout.write(f'Stock items actualizados:   {total_stats["stock_updated"]}')
        self.stdout.write(f'Compat creadas/upd:         {total_stats["compat_created"]} / {total_stats["compat_updated"]}')
        self.stdout.write(f'Compat omitidas (sin match):{total_stats["compat_skipped"]}')
        self.stdout.write(f'Errores:                    {total_stats["errors"]}')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se guardaron cambios'))
        self.stdout.write('')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _sync_categories(self, odoo, dry_run, total_stats):
        """
        Sincroniza categorías desde Odoo vinculando por odoo_category_id.

        Por qué odoo_category_id y NO por nombre:
          - Los PKs auto-incrementales de Django y Odoo pueden desincronizarse
            si se recrea cualquiera de las dos DBs.
          - El nombre puede cambiar.
          - odoo_category_id es el ancla estable: si existe en Category, es
            exactamente esa categoría de Odoo, sin importar el PK de Django.

        Estrategia de 2 pasos:
          1. Crear/actualizar todos los nodos sin parent (evita FK a nodos
             aún no insertados).
          2. Segunda pasada: asignar parent_id a partir del parent_id de Odoo,
             construyendo así la jerarquía de 3 niveles en MPTT.

        Retorna {odoo_category_id: Category instance}.
        """
        self.stdout.write('   📂 Sincronizando categorías...')
        odoo_categories_raw = odoo.get_categories()
        # Filtrar la categoría raíz 'All' de Odoo — no existe en Django y no
        # se asigna a ningún producto; incluirla solo genera ruido.
        odoo_categories = [
            oc for oc in odoo_categories_raw
            if not (oc['name'] == 'All' and not oc.get('parent_id'))
        ]
        categ_map = {}

        # Paso 1: crear/actualizar sin parent
        # Estrategia de 3 vías para bridgear seed_categories → primera sync:
        #   1. Buscar por odoo_category_id     (syncs subsiguientes)
        #   2. Fallback: buscar por nombre     (primera sync tras seed_categories)
        #   3. Crear si realmente no existe
        # Sin esta lógica, update_or_create intentaría CREAR una nueva categoría
        # con el mismo nombre → colisión de slug unique constraint.
        for oc in odoo_categories:
            if dry_run:
                categ_map[oc['id']] = None
                continue
            created = False
            try:
                cat = Category.objects.get(odoo_category_id=oc['id'])
                changed = False
                if cat.name != oc['name']:
                    cat.name = oc['name']
                    changed = True
                if not cat.is_active:
                    cat.is_active = True
                    changed = True
                if changed:
                    cat.save(update_fields=['name', 'is_active'])
            except Category.DoesNotExist:
                # Bridge: categoría creada por seed_categories (odoo_category_id=NULL)
                try:
                    cat = Category.objects.get(
                        name=oc['name'], odoo_category_id__isnull=True
                    )
                    cat.odoo_category_id = oc['id']
                    if not cat.is_active:
                        cat.is_active = True
                    cat.save(update_fields=['odoo_category_id', 'is_active'])
                except Category.DoesNotExist:
                    cat = Category(odoo_category_id=oc['id'], name=oc['name'], is_active=True)
                    cat.save()
                    created = True
                except Category.MultipleObjectsReturned:
                    # Nombre duplicado en Django — usar el primero y vincular
                    cat = Category.objects.filter(
                        name=oc['name'], odoo_category_id__isnull=True
                    ).first()
                    cat.odoo_category_id = oc['id']
                    cat.save(update_fields=['odoo_category_id', 'is_active'])
            categ_map[oc['id']] = cat
            if created:
                total_stats['categories_created'] += 1
            else:
                total_stats['categories_updated'] += 1

        # Paso 2: asignar parents (jerarquía 3 niveles)
        if not dry_run:
            for oc in odoo_categories:
                parent_raw = oc.get('parent_id')  # False o [id, 'nombre']
                if not parent_raw:
                    continue
                parent_odoo_id = parent_raw[0]
                parent_cat = categ_map.get(parent_odoo_id)
                child_cat  = categ_map.get(oc['id'])
                if parent_cat and child_cat and child_cat.parent_id != parent_cat.pk:
                    child_cat.parent = parent_cat
                    child_cat.save(update_fields=['parent'])

        label = 'Encontradas' if dry_run else 'Sincronizadas'
        self.stdout.write(self.style.SUCCESS(
            f'   ✅ {label} {len(odoo_categories)} categorías'
        ))
        return categ_map

    def _sync_warehouses(self, odoo, provider, dry_run, total_stats):
        """
        Sincroniza almacenes de la company desde Odoo.
        Retorna:
          warehouse_map: {odoo_warehouse_id: Warehouse instance}
          location_map:  {odoo_warehouse_id: lot_stock_id (int)}
        """
        self.stdout.write('   🏭 Sincronizando almacenes...')
        odoo_warehouses = odoo.get_warehouses(provider.odoo_company_id)
        warehouse_map = {}
        location_map  = {}

        for ow in odoo_warehouses:
            lot_stock_id = ow['lot_stock_id'][0] if ow.get('lot_stock_id') else None
            if not dry_run:
                wh, created = Warehouse.objects.update_or_create(
                    odoo_warehouse_id=ow['id'],
                    provider=provider,
                    defaults={'name': ow['name'], 'is_active': True}
                )
                warehouse_map[ow['id']] = wh
                if created:
                    total_stats['warehouses_created'] += 1
                else:
                    total_stats['warehouses_updated'] += 1
            if lot_stock_id:
                location_map[ow['id']] = lot_stock_id

        label = 'Encontrados' if dry_run else 'Sincronizados'
        self.stdout.write(self.style.SUCCESS(
            f'   ✅ {label} {len(odoo_warehouses)} almacén(es)'
        ))
        return warehouse_map, location_map

    def _sync_stock(self, odoo, provider, warehouse_map, location_map, total_stats):
        """
        Actualiza StockItem por almacén usando stock.quant de Odoo.
        Consulta en lote (un read_group por almacén) para evitar N+1 queries.
        """
        self.stdout.write('   📦 Sincronizando stock por almacén...')

        provider_products = (
            Product.objects
            .filter(provider=provider, odoo_template_id__isnull=False)
            .values('id', 'odoo_template_id')
        )
        tmpl_to_product = {p['odoo_template_id']: p['id'] for p in provider_products}
        tmpl_ids = list(tmpl_to_product.keys())

        if not tmpl_ids:
            self.stdout.write('   ⚠️  Sin productos con odoo_template_id, omitiendo stock')
            return

        for odoo_wh_id, warehouse in warehouse_map.items():
            location_id = location_map.get(odoo_wh_id)
            if not location_id:
                continue

            stock_by_tmpl = odoo.get_stock_quants_for_warehouse(tmpl_ids, location_id)

            for tmpl_id, qty in stock_by_tmpl.items():
                product_id = tmpl_to_product.get(tmpl_id)
                if not product_id:
                    continue
                try:
                    StockItem.objects.update_or_create(
                        product_id=product_id,
                        warehouse=warehouse,
                        defaults={'quantity': qty}
                    )
                    total_stats['stock_updated'] += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'   ❌ Error stock product_id={product_id} wh={warehouse.name}: {e}'
                    ))
                    total_stats['errors'] += 1

        self.stdout.write(self.style.SUCCESS(
            f'   ✅ Stock actualizado: {total_stats["stock_updated"]} items'
        ))

    def _sync_compatibility(self, odoo, provider, total_stats):
        """
        Sincroniza autopart.compatibility desde Odoo → CompatibilidadProducto en Django.

        Estrategia de resolución de VariantVehiculo (en orden):
          1. VariantVehiculo.odoo_variante_id == variant_id de Odoo  (si ya sincronizado)
          2. vehiculo.variante.django_external_id en Odoo            (PK directo de Django)
          3. Si ninguno, se omite y se loguea para corrección manual.

        Guarda odoo_variante_id en el VariantVehiculo cuando lo resuelve por
        django_external_id, para que las próximas syncs usen la vía rápida (1).
        """
        self.stdout.write('   🚗 Sincronizando compatibilidades producto↔vehículo...')

        # Templates con odoo_template_id del provider
        provider_products = list(
            Product.objects
            .filter(provider=provider, odoo_template_id__isnull=False)
            .values('id', 'odoo_template_id')
        )
        tmpl_to_product_id = {p['odoo_template_id']: p['id'] for p in provider_products}
        tmpl_ids = list(tmpl_to_product_id.keys())

        if not tmpl_ids:
            self.stdout.write('   ⚠️  Sin productos con odoo_template_id, omitiendo compatibilidades')
            return

        compat_records = odoo.get_compatibilities(tmpl_ids)
        if not compat_records:
            self.stdout.write('   ℹ️  Sin registros de compatibilidad en Odoo para este provider')
            return

        # Prefetch variantes de Odoo en una sola query
        odoo_variant_ids = [
            r['variant_id'][0] for r in compat_records if r.get('variant_id')
        ]
        odoo_variant_map = odoo.get_vehicle_variants(list(set(odoo_variant_ids)))

        c_created = c_updated = c_skipped = c_errors = 0

        for record in compat_records:
            try:
                tmpl_id = record['product_tmpl_id'][0] if record.get('product_tmpl_id') else None
                product_id = tmpl_to_product_id.get(tmpl_id)
                if not product_id:
                    c_skipped += 1
                    continue

                odoo_variant_id = record['variant_id'][0] if record.get('variant_id') else None
                variant = self._resolve_variant(odoo_variant_id, odoo_variant_map)
                if not variant:
                    c_skipped += 1
                    self.stdout.write(
                        f'   ⚠️  Sin match para odoo_variante_id={odoo_variant_id} '
                        f'(tmpl_id={tmpl_id}) — ejecutar push de vehículos primero'
                    )
                    continue

                # Persistir el ID de Odoo en Django para futuras syncs (vía rápida)
                if variant.odoo_variante_id != odoo_variant_id:
                    VariantVehiculo.objects.filter(pk=variant.pk).update(
                        odoo_variante_id=odoo_variant_id
                    )

                notes = (record.get('fitment_notes') or '')[:255]
                _, created = CompatibilidadProducto.objects.update_or_create(
                    producto_id=product_id,
                    variante=variant,
                    defaults={'notas_instalacion': notes}
                )
                if created:
                    c_created += 1
                else:
                    c_updated += 1

            except Exception as e:
                c_errors += 1
                self.stdout.write(self.style.ERROR(
                    f'   ❌ Error compat id={record.get("id")}: {e}'
                ))
                logger.error(f"Error compat {record.get('id')}: {e}", exc_info=True)

        total_stats['compat_created'] += c_created
        total_stats['compat_updated'] += c_updated
        total_stats['compat_skipped'] += c_skipped
        total_stats['errors']         += c_errors

        self.stdout.write(self.style.SUCCESS(
            f'   ✅ Compatibilidades: +{c_created} / ~{c_updated} / omitidas {c_skipped}'
        ))

    def _resolve_variant(self, odoo_variant_id, odoo_variant_map):
        """
        Resuelve VariantVehiculo desde el ID de Odoo.
        Misma lógica que _resolve_django_variant() en tasks.py.
        """
        if not odoo_variant_id:
            return None

        # Vía 1: campo odoo_variante_id ya seteado en Django
        try:
            return VariantVehiculo.objects.get(odoo_variante_id=odoo_variant_id)
        except VariantVehiculo.DoesNotExist:
            pass

        # Vía 2: django_external_id guardado en Odoo
        odoo_record = odoo_variant_map.get(odoo_variant_id)
        if odoo_record:
            django_ext_id = odoo_record.get('django_external_id')
            if django_ext_id:
                try:
                    return VariantVehiculo.objects.get(pk=int(django_ext_id))
                except (ValueError, TypeError, VariantVehiculo.DoesNotExist):
                    pass

        return None