import logging

from django.core.management.base import BaseCommand

from apps.sync.connector import OdooConnector
from apps.sync.services.categories import push_categories

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Empuja el catálogo global de categorías desde Django hacia Odoo'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n📂 Empujando catálogo global de categorías a Odoo...\n'))

        try:
            odoo = OdooConnector()
            self.stdout.write(self.style.SUCCESS(f'✅ Conectado a Odoo (UID: {odoo.uid})'))

            stats = {}
            push_categories(odoo, stats)

            self.stdout.write(self.style.SUCCESS('\n✅ Push de categorías completado'))
            self.stdout.write(
                f'   Creadas:     {stats.get("categories_created", 0)}\n'
                f'   Actualizadas:{stats.get("categories_updated", 0)}\n'
                f'   Vinculadas:  {stats.get("categories_linked", 0)}\n'
                f'   Errores:     {stats.get("categories_errors", 0)}\n'
            )

            if stats.get('categories_errors', 0):
                self.stdout.write(self.style.WARNING(
                    '⚠️  Algunas categorías no pudieron empujarse. Revisa el log para identificar padres faltantes.'
                ))

        except Exception as e:
            logger.exception('Error ejecutando push_categories: %s', e)
            self.stderr.write(self.style.ERROR(f'❌ Error ejecutando push_categories: {e}'))
