import logging

from django.core.management.base import BaseCommand

from apps.sync.connector import OdooConnector

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Actualiza un módulo instalado en Odoo vía RPC'

    def add_arguments(self, parser):
        parser.add_argument(
            '--module',
            required=True,
            help='Nombre técnico del módulo Odoo a actualizar',
        )

    def handle(self, *args, **options):
        module_name = options['module']

        try:
            odoo = OdooConnector()
            self.stdout.write(self.style.SUCCESS(f'✅ Conectado a Odoo (UID: {odoo.uid})'))

            modules = odoo.execute_kw(
                'ir.module.module', 'search_read',
                [[['name', '=', module_name]]],
                {'fields': ['id', 'name', 'state'], 'limit': 1},
            )
            if not modules:
                self.stderr.write(self.style.ERROR(f'❌ Módulo no encontrado en Odoo: {module_name}'))
                return

            module = modules[0]
            if module['state'] != 'installed':
                self.stderr.write(
                    self.style.ERROR(
                        f'❌ El módulo {module_name} no está instalado (estado actual: {module["state"]}).'
                    )
                )
                return

            self.stdout.write(f'📦 Actualizando módulo {module_name}...')
            odoo.execute_kw('ir.module.module', 'button_immediate_upgrade', [[module['id']]])
            self.stdout.write(self.style.SUCCESS(f'✅ Módulo actualizado: {module_name}'))

        except Exception as e:
            logger.exception('Error actualizando módulo Odoo %s: %s', module_name, e)
            self.stderr.write(self.style.ERROR(f'❌ Error actualizando módulo Odoo: {e}'))