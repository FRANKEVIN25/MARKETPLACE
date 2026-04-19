"""
Management command: sync_delivery_status
==========================================
Re-sincroniza el estado de entrega (x_delivery_status) entre Django y Odoo
para SubOrders cuyo stock.picking ya fue validado (done) en Odoo pero el webhook
no llegó a Django (p.ej. por el bug de ALLOWED_HOSTS).

Ubicado en apps/sync/ porque opera sobre la integración Django↔Odoo,
no sobre la lógica del dominio orders.

Uso:
    python manage.py sync_delivery_status
    python manage.py sync_delivery_status --suborder ORD-2026-00022-A
    python manage.py sync_delivery_status --dry-run
"""
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Re-sincroniza x_delivery_status en Odoo y SubOrder.status en Django "
        "para pickings de salida que ya están en estado 'done' en Odoo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--suborder',
            type=str,
            default=None,
            help='Número de SubOrder específica a sincronizar (ej: ORD-2026-00022-A)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Solo muestra qué se haría, sin aplicar cambios',
        )

    def handle(self, *args, **options):
        from apps.orders.models import SubOrder
        from apps.sync.services.orders import get_odoo_connection, update_odoo_delivery_status

        dry_run = options['dry_run']
        target_suborder = options.get('suborder')

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  Modo DRY-RUN — no se aplicarán cambios'))

        # 1. Conectar a Odoo
        self.stdout.write('🔌 Conectando a Odoo...')
        odoo = get_odoo_connection()
        if not odoo:
            self.stderr.write(self.style.ERROR('❌ No se pudo conectar a Odoo'))
            return

        self.stdout.write(self.style.SUCCESS('✅ Conectado a Odoo'))

        # 2. Obtener SubOrders candidatas
        # Incluye:
        #   - SubOrders que Django aún no marcó como enviado/entregado
        #     (el picking puede estar done en Odoo pero el webhook nunca llegó)
        #   - SubOrders que Django ya marcó como enviado/entregado pero cuyo
        #     x_delivery_status en Odoo todavía está pendiente
        #     (p.ej. cuando el write a Odoo falló tras actualizar Django)
        qs = SubOrder.objects.filter(
            odoo_sale_id__isnull=False,
        ).exclude(
            status='cancelado',
        ).select_related('order')

        if target_suborder:
            qs = qs.filter(sub_order_number=target_suborder)

        suborders = list(qs)

        if not suborders:
            self.stdout.write('ℹ️  No hay SubOrders candidatas para sincronizar.')
            return

        self.stdout.write(f'🔎 Revisando {len(suborders)} SubOrder(s)...\n')

        updated = 0
        skipped = 0
        errors = 0

        for sub in suborders:
            try:
                # 3. Obtener el nombre de la sale.order en Odoo
                sale_orders = odoo.execute_kw(
                    'sale.order',
                    'read',
                    [[sub.odoo_sale_id]],
                    {'fields': ['name', 'state', 'x_delivery_status']},
                )
                if not sale_orders:
                    self.stdout.write(
                        f'  ⚠️  {sub.sub_order_number}: sale.order {sub.odoo_sale_id} no encontrada en Odoo'
                    )
                    skipped += 1
                    continue

                sale_order_data = sale_orders[0]
                sale_name = sale_order_data['name']
                current_x_delivery = sale_order_data.get('x_delivery_status') or 'pendiente'

                # 4. Buscar outgoing pickings en estado 'done' para esta sale.order
                done_picking_ids = odoo.execute_kw(
                    'stock.picking',
                    'search',
                    [[
                        ['origin', '=', sale_name],
                        ['state', '=', 'done'],
                        ['picking_type_code', '=', 'outgoing'],
                    ]],
                )

                expected_odoo_status = {
                    'enviado':   'enviado',
                    'entregado': 'recibido',
                }.get(sub.status)

                # Si Django ya está en enviado/entregado, verificar si Odoo está desactualizado
                if expected_odoo_status and current_x_delivery != expected_odoo_status:
                    self.stdout.write(
                        f'  🔄 {sub.sub_order_number} ({sale_name}): '
                        f'Django={sub.status}, Odoo={current_x_delivery} → {expected_odoo_status} '
                        f'(Odoo desactualizado)'
                    )
                    if not dry_run:
                        ok = update_odoo_delivery_status(sub)
                        if ok:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'     ✅ Odoo x_delivery_status → {expected_odoo_status}'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'     ⚠️  No se pudo actualizar Odoo para {sub.sub_order_number}'
                                )
                            )
                    else:
                        self.stdout.write(self.style.WARNING('     [DRY-RUN]'))
                    updated += 1
                    continue

                if not done_picking_ids:
                    self.stdout.write(
                        f'  ℹ️  {sub.sub_order_number} ({sale_name}): '
                        f'sin pickings done. Django={sub.status}, Odoo={current_x_delivery}'
                    )
                    skipped += 1
                    continue

                self.stdout.write(
                    f'  📦 {sub.sub_order_number} ({sale_name}): '
                    f'picking(s) done={done_picking_ids}. '
                    f'Django={sub.status} → enviado | Odoo={current_x_delivery} → enviado'
                )

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING('     [DRY-RUN] No se aplican cambios')
                    )
                    updated += 1
                    continue

                # 5. Actualizar Django SubOrder
                prev_status = sub.status
                update_fields = []

                if sub.status not in ('enviado', 'entregado'):
                    sub.status = 'enviado'
                    update_fields.append('status')

                if not sub.shipped_at:
                    sub.shipped_at = timezone.now()
                    update_fields.append('shipped_at')

                if update_fields:
                    sub.save(update_fields=update_fields)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'     ✅ Django: {sub.sub_order_number} {prev_status} → {sub.status}'
                        )
                    )

                # 6. Actualizar x_delivery_status en Odoo
                ok = update_odoo_delivery_status(sub)
                if ok:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'     ✅ Odoo: x_delivery_status → enviado '
                            f'(sale.order {sub.odoo_sale_id})'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'     ⚠️  No se pudo actualizar x_delivery_status en Odoo '
                            f'para {sub.sub_order_number}'
                        )
                    )

                updated += 1

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f'  ❌ Error procesando {sub.sub_order_number}: {e}')
                )
                logger.exception('sync_delivery_status error para %s', sub.sub_order_number)
                errors += 1

        # Resumen
        self.stdout.write('\n' + '─' * 50)
        self.stdout.write(self.style.SUCCESS(f'✅ Actualizadas : {updated}'))
        self.stdout.write(f'⏭️  Omitidas   : {skipped}')
        if errors:
            self.stdout.write(self.style.ERROR(f'❌ Errores     : {errors}'))
