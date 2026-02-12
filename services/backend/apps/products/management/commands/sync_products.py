"""
Comando para sincronizar productos desde Odoo
Usa el OdooConnector y tasks existentes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.marketplace.models import Provider
from apps.products.models import Product, Category
from apps.sync.odoo_connector import get_odoo_connector_for_provider
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza productos desde Odoo hacia el marketplace de Django'

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

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        provider_id = options.get('provider_id')
        limit = options.get('limit')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 MODO DRY-RUN: No se guardarán cambios\n'))
        
        # Determinar providers a sincronizar
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
            'products_created': 0,
            'products_updated': 0,
            'errors': 0
        }
        
        # Sincronizar cada provider
        for provider in providers:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(f'🏢 Provider: {provider.name} ({provider.get_tier_display()})')
            self.stdout.write(f'   Odoo Company ID: {provider.odoo_company_id}')
            self.stdout.write(f'{"="*60}\n')
            
            try:
                # Obtener conector de Odoo
                odoo = get_odoo_connector_for_provider(provider)
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Conectado a Odoo (UID: {odoo.uid})'
                ))
                
                # Obtener productos de Odoo
                self.stdout.write('   📡 Obteniendo productos de Odoo...')
                odoo_products = odoo.get_products(limit=limit)
                
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Encontrados {len(odoo_products)} productos en Odoo\n'
                ))
                
                provider_stats = {
                    'created': 0,
                    'updated': 0,
                    'errors': 0
                }
                
                # Sincronizar cada producto
                for idx, odoo_product in enumerate(odoo_products, 1):
                    try:
                        # Obtener o crear categoría
                        category = self._get_or_create_category(
                            odoo_product.get('categ_id'),
                            dry_run
                        )
                        
                        # Datos del producto
                        product_data = {
                            'provider': provider,
                            'name': odoo_product['name'],
                            'reference': odoo_product.get('default_code', f'AUTO-{odoo_product["id"]}'),
                            'sku': odoo_product.get('default_code', ''),
                            'description': odoo_product.get('description_sale') or odoo_product.get('description', ''),
                            'price': Decimal(str(odoo_product.get('list_price', 0))),
                            'cost': Decimal(str(odoo_product.get('standard_price', 0))),
                            'stock': int(odoo_product.get('qty_available', 0)),
                            'barcode': odoo_product.get('barcode', ''),
                            'weight': Decimal(str(odoo_product.get('weight', 0))),
                            'category': category,
                            'is_active': odoo_product.get('active', True),
                            'odoo_product_id': odoo_product['id'],
                            'odoo_template_id': odoo_product.get('product_tmpl_id', [None])[0] if isinstance(odoo_product.get('product_tmpl_id'), list) else None,
                            'odoo_state': 'sellable' if odoo_product.get('active') else 'draft',
                            'last_sync_at': timezone.now(),
                        }
                        
                        # Buscar producto existente
                        existing = Product.objects.filter(
                            provider=provider,
                            odoo_product_id=odoo_product['id']
                        ).first()
                        
                        if dry_run:
                            if existing:
                                action = '🔄 Actualizar'
                                provider_stats['updated'] += 1
                            else:
                                action = '✨ Crear'
                                provider_stats['created'] += 1
                        else:
                            # Guardar producto
                            if existing:
                                for key, value in product_data.items():
                                    setattr(existing, key, value)
                                existing.save()
                                action = '🔄 Actualizado'
                                provider_stats['updated'] += 1
                            else:
                                Product.objects.create(**product_data)
                                action = '✨ Creado'
                                provider_stats['created'] += 1
                        
                        # Mostrar progreso cada 10 productos
                        if idx % 10 == 0 or idx == 1:
                            self.stdout.write(
                                f'   [{idx}/{len(odoo_products)}] {action}: {odoo_product["name"][:50]} '
                                f'(Stock: {int(odoo_product.get("qty_available", 0))}, '
                                f'Precio: S/ {odoo_product.get("list_price", 0):.2f})'
                            )
                        
                    except Exception as e:
                        provider_stats['errors'] += 1
                        self.stdout.write(self.style.ERROR(
                            f'   ❌ Error con producto {odoo_product.get("name", "N/A")}: {str(e)}'
                        ))
                        logger.error(f"Error sincronizando producto {odoo_product['id']}: {e}", exc_info=True)
                
                # Actualizar contador de productos del provider (solo si no es dry-run)
                if not dry_run:
                    provider.total_products = Product.objects.filter(
                        provider=provider,
                        is_active=True
                    ).count()
                    provider.save(update_fields=['total_products'])
                
                # Mostrar resumen del provider
                self.stdout.write(f'\n   📊 Resumen de {provider.name}:')
                self.stdout.write(f'      ✨ Creados: {provider_stats["created"]}')
                self.stdout.write(f'      🔄 Actualizados: {provider_stats["updated"]}')
                self.stdout.write(f'      ❌ Errores: {provider_stats["errors"]}')
                
                # Acumular estadísticas
                total_stats['providers'] += 1
                total_stats['products_created'] += provider_stats['created']
                total_stats['products_updated'] += provider_stats['updated']
                total_stats['errors'] += provider_stats['errors']
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'\n   ❌ ERROR al sincronizar {provider.name}: {str(e)}\n'
                ))
                logger.error(f"Error sincronizando provider {provider.id}: {e}", exc_info=True)
        
        # Resumen final
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS('✅ SINCRONIZACIÓN COMPLETADA'))
        self.stdout.write(f'{"="*60}')
        self.stdout.write(f'Providers procesados: {total_stats["providers"]}')
        self.stdout.write(f'Productos creados: {total_stats["products_created"]}')
        self.stdout.write(f'Productos actualizados: {total_stats["products_updated"]}')
        self.stdout.write(f'Errores: {total_stats["errors"]}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY-RUN: No se guardaron cambios'))
        
        self.stdout.write('')
    
    def _get_or_create_category(self, categ_data, dry_run=False):
        """Obtiene o crea una categoría basada en datos de Odoo"""
        if not categ_data:
            # Categoría por defecto
            if dry_run:
                return None
            category, _ = Category.objects.get_or_create(
                name='General',
                defaults={
                    'description': 'Productos sin categoría específica'
                }
            )
            return category
        
        # categ_data es una tupla (id, nombre) de Odoo
        category_name = categ_data[1] if isinstance(categ_data, (list, tuple)) else str(categ_data)
        
        if dry_run:
            return None
        
        category, created = Category.objects.get_or_create(
            name=category_name,
            defaults={
                'description': f'Categoría sincronizada desde Odoo'
            }
        )
        
        return category