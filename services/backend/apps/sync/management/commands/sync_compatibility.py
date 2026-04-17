"""
Management command: sync_compatibility
======================================
Sincroniza únicamente compatibilidades producto↔vehículo desde Odoo.

Se ejecuta por provider o para todos los providers activos/aprobados con
company_id en Odoo. Complementa a sync_products y permite correr la sync de
compatibilidades de forma independiente.

Uso:
    # Todos los providers activos y aprobados
    python manage.py sync_compatibility

    # Provider específico
    python manage.py sync_compatibility --provider-id=3
"""
import logging

from django.core.management.base import BaseCommand

from apps.marketplace.models import Provider
from apps.sync.services.compatibility import sync_provider_compatibility

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sincroniza compatibilidades producto↔vehículo desde Odoo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider-id',
            type=int,
            default=None,
            help='ID del Provider específico; omitir para todos los activos/aprobados',
        )

    def handle(self, *args, **options):
        providers = self._get_providers(options['provider_id'])
        if providers is None:
            return

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🚗 Sincronizando compatibilidades de {providers.count()} provider(s)...\n'
            )
        )

        total = {
            'created': 0,
            'updated': 0,
            'removed': 0,
            'skipped': 0,
            'errors': 0,
        }

        for provider in providers:
            self.stdout.write(f'🏢 {provider.name} (company_id={provider.odoo_company_id})')
            result = sync_provider_compatibility(provider.id)

            if 'error' in result:
                self.stdout.write(self.style.ERROR(f'   ❌ {result["error"]}'))
                total['errors'] += 1
                continue

            created = result.get('compat_created', 0)
            updated = result.get('compat_updated', 0)
            removed = result.get('compat_removed', 0)
            skipped = (
                result.get('skipped_no_product', 0)
                + result.get('skipped_no_variant', 0)
            )
            errors = result.get('errors', 0)

            total['created'] += created
            total['updated'] += updated
            total['removed'] += removed
            total['skipped'] += skipped
            total['errors'] += errors

            self.stdout.write(
                self.style.SUCCESS(
                    f'   ✅ Compat: +{created} / ~{updated} / -{removed} / omitidas {skipped}'
                )
            )
            if errors:
                self.stdout.write(self.style.WARNING(f'   ⚠️  Errores: {errors}'))

        self.stdout.write(f'\n{"─" * 50}')
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Total compatibilidades: +{total["created"]} / ~{total["updated"]}'
            )
        )
        self.stdout.write(f'Compat removidas: {total["removed"]}')
        self.stdout.write(f'Compat omitidas: {total["skipped"]}')
        if total['errors']:
            self.stdout.write(self.style.ERROR(f'❌ Total errores: {total["errors"]}'))
        self.stdout.write('')

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
            self.stdout.write(self.style.ERROR('❌ No hay providers para sincronizar compatibilidades'))
            return None
        return qs