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
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

REQUIRED_MODULES = ['orders_odoo', 'multi_company_products']

# Grupos correctos para usuarios proveedor
PROVIDER_GROUPS_ADD = [23, 45, 26]   # Ventas/Admin, Inventario/Admin, Facturación
PROVIDER_GROUPS_REMOVE = [21, 22, 44]  # grupos básicos que se reemplazan

# Reglas de aislamiento a aplicar {rule_id: domain}
# Nota: estos IDs corresponden a registros existentes en la instancia Odoo
# actual. Los dominios deben respetar los campos reales de cada modelo para no
# romper el arranque al ejecutar setup_odoo en cada boot.
ISOLATION_RULES = {
    71:  "['|', ('company_id', 'in', company_ids), ('company_id', '=', False)]",  # product.supplierinfo
    161: "[('move_ids.move_type', 'in', ('out_invoice', 'out_refund'))]",         # account.move.send.batch.wizard
    105: "[('company_id', 'in', company_ids)]",                                    # account.move
    137: "[(1, '=', 1)]",                                                          # payment.token
    109: "[('company_ids', 'parent_of', company_ids)]",                           # account.account
    111: "[('company_id', 'in', company_ids)]",                                    # account.tax.group
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
            self.stderr.write('❌ Odoo no disponible, saltando configuración')
            return

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

    def _apply_isolation_rules(self, odoo):
        """Aplica reglas de aislamiento multi-company"""
        self.stdout.write('🔒 Aplicando reglas de aislamiento...')
        for rule_id, domain in ISOLATION_RULES.items():
            try:
                # Verificar que la regla existe
                rules = odoo.execute_kw(
                    'ir.rule', 'search_read',
                    [[['id', '=', rule_id]]],
                    {'fields': ['id', 'name', 'domain_force']}
                )
                if not rules:
                    self.stdout.write(f'  ⚠️  Regla [{rule_id}] no encontrada, saltando')
                    continue

                current_domain = rules[0]['domain_force']
                if current_domain == domain:
                    self.stdout.write(f'  ✅ Regla [{rule_id}] ya configurada')
                    continue

                odoo.execute_kw('ir.rule', 'write', [[rule_id], {'domain_force': domain}])
                self.stdout.write(f'  ✅ Regla [{rule_id}] actualizada: {rules[0]["name"]}')
            except Exception as e:
                self.stderr.write(f'  ❌ Error en regla [{rule_id}]: {e}')

    def _configure_provider_permissions(self, odoo):
        """Configura permisos correctos para todos los usuarios proveedor"""
        self.stdout.write('👥 Configurando permisos de proveedores...')
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
                        any(g not in current_groups for g in PROVIDER_GROUPS_ADD) or
                        any(g in current_groups for g in PROVIDER_GROUPS_REMOVE)
                    )

                    if not needs_update:
                        self.stdout.write(f'  ✅ {provider.name} ya tiene permisos correctos')
                        continue

                    odoo.execute_kw(
                        'res.users', 'write',
                        [[uid], {
                            'groups_id': (
                                [(3, gid) for gid in PROVIDER_GROUPS_REMOVE] +
                                [(4, gid) for gid in PROVIDER_GROUPS_ADD]
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