"""
Management command: setup_odoo
Configura Odoo automáticamente al arrancar el backend.
- Instala módulos necesarios
- Aplica reglas de aislamiento multi-company
- Configura permisos de grupos para proveedores
- Idempotente: se puede ejecutar múltiples veces sin efectos secundarios
"""
import logging
import time
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

REQUIRED_MODULES = ['ecomp', 'orders_odoo', 'multi_company_products', 'odoo_django_webhook']

# Grupos correctos para usuarios proveedor
PROVIDER_GROUPS_ADD = [
    'sales_team.group_sale_manager',
    'stock.group_stock_manager',
    'account.group_account_invoice',
]
PROVIDER_GROUPS_REMOVE = [
    'sales_team.group_sale_salesman',
    'sales_team.group_sale_salesman_all_leads',
    'stock.group_stock_user',
]

# Los XML IDs identifican las mismas reglas en bases inicializadas desde cero.
ISOLATION_RULES = {
    'product.product_supplierinfo_comp_rule': "['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]",
    'sale.account_invoice_send_batch_rule_see_all': "[('move_ids.move_type', 'in', ('out_invoice', 'out_refund'))]",
    'account.account_move_comp_rule': "[('company_id', 'in', company_ids)]",
    'account_payment.payment_token_billing_rule': "[(1, '=', 1)]",
    'account.account_comp_rule': "[('company_ids', 'parent_of', company_ids)]",
    'account.tax_group_comp_rule': "[('company_id', 'in', company_ids)]",
}


class Command(BaseCommand):
    help = 'Configura Odoo: módulos, permisos y reglas de aislamiento multi-company'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Forzar reconfiguración aunque ya esté aplicada'
        )
        parser.add_argument(
            '--skip-modules', action='store_true',
            help='Saltar instalación de módulos'
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Iniciando configuración de Odoo...')

        # Esperar a que Odoo esté disponible
        odoo = self._wait_for_odoo()
        if not odoo:
            raise CommandError('Odoo no disponible para completar la configuración')

        # 1. Instalar módulos
        if not options.get('skip_modules'):
            self._install_modules(odoo)

        # 2. Aplicar reglas de aislamiento
        self._apply_isolation_rules(odoo)

        # 3. Configurar permisos de proveedores existentes
        self._configure_provider_permissions(odoo)

        # 4. Crear regla de sale.order con user_id del proveedor
        self._ensure_sale_order_isolation(odoo)

        self.stdout.write(self.style.SUCCESS('✅ Configuración de Odoo completada'))

    def _wait_for_odoo(self, retries=10, delay=5):
        """Espera a que Odoo esté disponible"""
        try:
            from apps.sync.odoo_connector import OdooConnector
            for attempt in range(retries):
                try:
                    odoo = OdooConnector()
                    # Test rápido
                    odoo.execute_kw('res.company', 'search_read', [[]], {'fields': ['id'], 'limit': 1})
                    self.stdout.write('✅ Odoo disponible')
                    return odoo
                except Exception as e:
                    self.stdout.write(f'⏳ Esperando Odoo... (intento {attempt+1}/{retries}): {str(e)[:50]}')
                    time.sleep(delay)
        except ImportError:
            self.stderr.write('❌ OdooConnector no disponible')
        return None

    def _install_modules(self, odoo):
        """Instala módulos requeridos si no están instalados"""
        self.stdout.write('📦 Verificando módulos...')
        for module_name in REQUIRED_MODULES:
            try:
                modules = odoo.execute_kw(
                    'ir.module.module', 'search_read',
                    [[['name', '=', module_name]]],
                    {'fields': ['id', 'state']}
                )
                if not modules:
                    self.stdout.write(f'  ⚠️  {module_name} no encontrado')
                    continue

                module = modules[0]
                if module['state'] == 'installed':
                    self.stdout.write(f'  ✅ {module_name} ya instalado')
                    continue

                self.stdout.write(f'  📥 Instalando {module_name}...')
                odoo.execute_kw('ir.module.module', 'button_immediate_install', [[module['id']]])
                self.stdout.write(f'  ✅ {module_name} instalado')
            except Exception as e:
                self.stderr.write(f'  ❌ Error instalando {module_name}: {e}')

    def _resolve_external_id(self, odoo, xml_id, model):
        """Resuelve un XML ID sin depender de los IDs de otra base de datos."""
        module, name = xml_id.split('.', 1)
        records = odoo.execute_kw(
            'ir.model.data', 'search_read',
            [[['module', '=', module], ['name', '=', name], ['model', '=', model]]],
            {'fields': ['res_id'], 'limit': 1},
        )
        if not records:
            raise CommandError(f'No se encontró {xml_id} ({model})')
        return records[0]['res_id']

    def _apply_isolation_rules(self, odoo):
        """Aplica reglas de aislamiento multi-company"""
        self.stdout.write('🔒 Aplicando reglas de aislamiento...')
        for xml_id, domain in ISOLATION_RULES.items():
            try:
                rule_id = self._resolve_external_id(odoo, xml_id, 'ir.rule')
                # Verificar que la regla existe
                rules = odoo.execute_kw(
                    'ir.rule', 'search_read',
                    [[['id', '=', rule_id]]],
                    {'fields': ['id', 'name', 'domain_force']}
                )
                if not rules:
                    raise CommandError(f'Regla {xml_id} no encontrada')

                current_domain = rules[0]['domain_force']
                if current_domain == domain:
                    self.stdout.write(f'  ✅ Regla [{rule_id}] ya configurada')
                    continue

                odoo.execute_kw('ir.rule', 'write', [[rule_id], {'domain_force': domain}])
                self.stdout.write(f'  ✅ Regla [{rule_id}] actualizada: {rules[0]["name"]}')
            except Exception as e:
                raise CommandError(f'Error configurando la regla {xml_id}: {e}') from e

    def _configure_provider_permissions(self, odoo):
        """Configura permisos correctos para todos los usuarios proveedor"""
        self.stdout.write('👥 Configurando permisos de proveedores...')
        groups_add = [self._resolve_external_id(odoo, xml_id, 'res.groups') for xml_id in PROVIDER_GROUPS_ADD]
        groups_remove = [self._resolve_external_id(odoo, xml_id, 'res.groups') for xml_id in PROVIDER_GROUPS_REMOVE]
        try:
            from apps.marketplace.models import Provider
            for provider in Provider.objects.filter(odoo_user_id__isnull=False):
                uid = provider.odoo_user_id
                try:
                    user = odoo.execute_kw(
                        'res.users', 'search_read',
                        [[['id', '=', uid]]],
                        {'fields': ['id', 'groups_id']}
                    )
                    if not user:
                        continue

                    current_groups = user[0]['groups_id']
                    needs_update = (
                        any(g not in current_groups for g in groups_add) or
                        any(g in current_groups for g in groups_remove)
                    )

                    if not needs_update:
                        self.stdout.write(f'  ✅ {provider.name} ya tiene permisos correctos')
                        continue

                    odoo.execute_kw(
                        'res.users', 'write',
                        [[uid], {
                            'groups_id': (
                                [(3, gid) for gid in groups_remove] +
                                [(4, gid) for gid in groups_add]
                            )
                        }]
                    )
                    self.stdout.write(f'  ✅ {provider.name} permisos actualizados')
                except Exception as e:
                    self.stderr.write(f'  ❌ {provider.name}: {e}')
        except Exception as e:
            self.stderr.write(f'❌ Error configurando permisos: {e}')

    def _ensure_sale_order_isolation(self, odoo):
        """Asegura que las sale orders tienen user_id del proveedor correcto"""
        self.stdout.write('📋 Verificando Sale Orders sin user_id de proveedor...')
        try:
            from apps.orders.models import SubOrder
            for sub in SubOrder.objects.filter(odoo_sale_id__isnull=False):
                provider = sub.provider
                if not provider.odoo_user_id:
                    continue
                try:
                    orders = odoo.execute_kw(
                        'sale.order', 'search_read',
                        [[['id', '=', sub.odoo_sale_id]]],
                        {'fields': ['id', 'user_id'],
                         'context': {'allowed_company_ids': [provider.odoo_company_id]}}
                    )
                    if not orders:
                        continue
                    current_uid = orders[0]['user_id'][0] if orders[0]['user_id'] else False
                    if current_uid == provider.odoo_user_id:
                        continue
                    odoo.execute_kw(
                        'sale.order', 'write',
                        [[sub.odoo_sale_id], {'user_id': provider.odoo_user_id}],
                        {'context': {'allowed_company_ids': [provider.odoo_company_id]}}
                    )
                    self.stdout.write(f'  ✅ {sub.sub_order_number} → user_id corregido')
                except Exception as e:
                    self.stderr.write(f'  ❌ {sub.sub_order_number}: {str(e)[:60]}')
        except Exception as e:
            self.stderr.write(f'❌ Error verificando sale orders: {e}')
