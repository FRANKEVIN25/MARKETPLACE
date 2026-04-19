"""
Management command: sync_stock
================================
Actualiza únicamente total_stock_cached de todos los productos de un provider
(o de todos los providers activos) consultando qty_available en Odoo.

Más rápido que sync_products: no toca categorías, metadatos ni compatibilidades.
Útil para mantener el stock al día entre ciclos completos de sync.

Corresponde a la tarea Celery sync_all_stock / sync_provider_stock de
apps/sync/tasks.py — permite ejecutarla manualmente sin Celery.

Uso:
    # Todos los providers activos y aprobados
    python manage.py sync_stock

    # Provider específico
    python manage.py sync_stock --provider-id=3

    # Dry-run: reporta cuántos productos actualizaría sin guardar
    python manage.py sync_stock --dry-run
    python manage.py sync_stock --provider-id=3 --dry-run
"""
import logging

from django.core.management.base import BaseCommand

from apps.marketplace.models import Provider
from apps.sync.services.products import sync_provider_stock

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Actualiza total_stock_cached de productos desde Odoo (sin tocar metadatos ni compat)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider-id',
            type=int,
            default=None,
            help='ID del Provider específico; omitir para todos los activos/aprobados',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Conecta a Odoo y reporta cuántos productos actualizaría sin guardar',
        )

    def handle(self, *args, **options):
        provider_id = options['provider_id']
        dry_run     = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n🔍 MODO DRY-RUN: No se guardarán cambios\n'))

        providers = self._get_providers(provider_id)
        if providers is None:
            return

        self.stdout.write(
            self.style.SUCCESS(f'\n📦 Actualizando stock de {providers.count()} provider(s)...\n')
        )

        total_updated = 0
        total_errors  = 0

        for provider in providers:
            self.stdout.write(f'🏢 {provider.name} (company_id={provider.odoo_company_id})')

            if dry_run:
                self._dry_run_provider(provider)
            else:
                result = sync_provider_stock(provider.id)
                if 'error' in result:
                    self.stdout.write(self.style.ERROR(f'   ❌ {result["error"]}'))
                    total_errors += 1
                else:
                    updated = result.get('updated', 0)
                    unchanged = result.get('unchanged', 0)
                    missing_local = result.get('missing_local', 0)
                    errors  = result.get('errors', 0)
                    total_updated += updated
                    total_errors  += errors
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'   ✅ Stock actualizado: {updated} productos'
                            f' | sin cambios: {unchanged}'
                            f' | sin match local: {missing_local}'
                        )
                    )
                    if errors:
                        self.stdout.write(self.style.WARNING(f'   ⚠️  Errores: {errors}'))

        self.stdout.write(f'\n{"─" * 50}')
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY-RUN: No se guardaron cambios'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✅ Total productos actualizados: {total_updated}'))
            if total_errors:
                self.stdout.write(self.style.ERROR(f'❌ Total errores: {total_errors}'))
        self.stdout.write('')

    # ── helpers ───────────────────────────────────────────────────────────────

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
            self.stdout.write(self.style.ERROR('❌ No hay providers para actualizar stock'))
            return None
        return qs

    def _dry_run_provider(self, provider):
        from apps.sync.connector import get_odoo_connector_for_provider
        from apps.products.models import Product

        try:
            odoo = get_odoo_connector_for_provider(provider)
            odoo_products = odoo.get_products(company_id=provider.odoo_company_id)
            django_count  = Product.objects.filter(
                provider=provider,
                odoo_product_id__isnull=False,
            ).count()
            self.stdout.write(
                f'   🔍 Odoo: {len(odoo_products)} productos'
                f' | Django con odoo_product_id: {django_count}'
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error conectando a Odoo: {e}'))
            logger.error('sync_stock dry-run error provider %s: %s', provider.id, e)
