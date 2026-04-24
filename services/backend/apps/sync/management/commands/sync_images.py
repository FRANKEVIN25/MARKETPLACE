"""
Management command: sync_images
===============================
Sincroniza únicamente imágenes de producto desde Odoo hacia Cloudinary/Django.

Complementa a sync_products: permite ejecutar solo la fase diferencial de
imágenes sin tocar catálogo, stock ni compatibilidades.

Uso:
    # Todos los providers activos y aprobados
    python manage.py sync_images

    # Provider específico
    python manage.py sync_images --provider-id=3

    # Fuerza refresh de todas las imágenes con match local, aunque
    # x_image_version no haya cambiado
    python manage.py sync_images --force
"""

from django.core.management.base import BaseCommand

from apps.marketplace.models import Provider
from apps.sync.services.products import sync_provider_product_images


class Command(BaseCommand):
    help = 'Sincroniza solo imágenes de producto desde Odoo hacia Cloudinary/Django'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider-id',
            type=int,
            default=None,
            help='ID del Provider específico; omitir para todos los activos/aprobados',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza el refresh de imágenes aunque x_image_version no haya cambiado',
        )

    def handle(self, *args, **options):
        providers = self._get_providers(options['provider_id'])
        if providers is None:
            return

        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(
                f'\n🖼️  Sincronizando imágenes de {providers.count()} provider(s)...\n'
            )
        )

        total = {
            'scanned': 0,
            'candidates': 0,
            'updated': 0,
            'cleared': 0,
            'skipped': 0,
            'errors': 0,
        }

        for provider in providers:
            self.stdout.write(f'🏢 {provider.name} (company_id={provider.odoo_company_id})')
            result = sync_provider_product_images(provider.id, force=force)

            if 'error' in result:
                self.stdout.write(self.style.ERROR(f'   ❌ {result["error"]}'))
                total['errors'] += 1
                continue

            images = result.get('images', {})
            total['scanned'] += images.get('scanned', 0)
            total['candidates'] += images.get('candidates', 0)
            total['updated'] += images.get('updated', 0)
            total['cleared'] += images.get('cleared', 0)
            total['skipped'] += images.get('skipped', 0)
            total['errors'] += images.get('errors', 0)

            self.stdout.write(
                self.style.SUCCESS(
                    f'   ✅ Imágenes: escaneadas {images.get("scanned", 0)}'
                    f' / candidatas {images.get("candidates", 0)}'
                    f' / actualizadas {images.get("updated", 0)}'
                    f' / limpiadas {images.get("cleared", 0)}'
                    f' / omitidas {images.get("skipped", 0)}'
                )
            )
            if images.get('errors', 0):
                self.stdout.write(self.style.WARNING(f'   ⚠️  Errores: {images["errors"]}'))

        self.stdout.write(f'\n{"─" * 50}')
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Total imágenes: escaneadas {total["scanned"]}'
                f' / candidatas {total["candidates"]}'
                f' / actualizadas {total["updated"]}'
                f' / limpiadas {total["cleared"]}'
            )
        )
        self.stdout.write(f'Imágenes omitidas: {total["skipped"]}')
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
            self.stdout.write(self.style.ERROR('❌ No hay providers para sincronizar imágenes'))
            return None
        return qs