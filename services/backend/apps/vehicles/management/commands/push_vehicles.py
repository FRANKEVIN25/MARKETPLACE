"""
Comando: push_vehicles
Empuja el catálogo universal de vehículos de Django hacia Odoo y establece
los vínculos bidireccionales (django_external_id en Odoo ↔ odoo_variante_id en Django).

Por qué es necesario:
  - Django es la fuente de verdad del catálogo de vehículos.
  - Odoo necesita las variantes para que los proveedores puedan crear
    compatibilidades (autopart.compatibility) desde la UI de Odoo.
  - Una vez que un proveedor asigna compatibilidades en Odoo, la sync
    (sync_products) las trae a Django resolviendo la variante por
    odoo_variante_id (más rápido) o django_external_id (fallback).

Flujo con --provider-id (scope por proveedor):
  1. Lee provider.variantes_habilitadas (M2M definido en marketplace/models.py).
  2. Para cada VariantVehiculo en ese scope:
     a–f. Empuja la jerarquía completa hacia Odoo (igual que el push global).
  3. Llama a sync_full_scope_for_company:
     - Añade company_id a vehiculo.variante.company_ids para las variantes del scope.
     - Quita company_id de variantes que ya no están en el scope de Django.
  El resultado es que el proveedor en Odoo solo ve las variantes de su scope.

Flujo global (sin --provider-id):
  Empuja TODAS las variantes sin modificar company_ids.
  Úsalo para la puesta en marcha inicial o para construir el catálogo base.

Uso:
  # Dry-run (muestra qué haría sin guardar)
  docker exec -it ecomparts-backend python manage.py push_vehicles --dry-run

  # Push completo (catálogo global)
  docker exec -it ecomparts-backend python manage.py push_vehicles

  # Solo variantes sin odoo_variante_id (incremental, más rápido)
  docker exec -it ecomparts-backend python manage.py push_vehicles --only-unlinked

  # Forzar re-empuje aunque ya tengan odoo_variante_id (re-sincronizar)
  docker exec -it ecomparts-backend python manage.py push_vehicles --force

  # Solo las variantes habilitadas de un proveedor específico
  docker exec -it ecomparts-backend python manage.py push_vehicles --provider-id=5

  # Provider incremental (solo nuevas sin odoo_variante_id)
  docker exec -it ecomparts-backend python manage.py push_vehicles --provider-id=5 --only-unlinked

Idempotencia:
  Puede correrse múltiples veces sin riesgo. Usa la estrategia de 3 vías
  (por django_external_id → clave natural → crear) en cada entidad.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.vehicles.models import (
    Marca, ModeloVehiculo, Transmision, Traccion, Motor, VariantVehiculo
)
from apps.sync.odoo_connector import OdooConnector
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Empuja el catálogo de vehículos de Django a Odoo y establece los vínculos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula el push sin guardar cambios.',
        )
        parser.add_argument(
            '--only-unlinked',
            action='store_true',
            help='Solo procesa variantes sin odoo_variante_id (más rápido en producción).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-empuja aunque la variante ya tenga odoo_variante_id.',
        )
        parser.add_argument(
            '--provider-id',
            type=int,
            default=None,
            dest='provider_id',
            help=(
                'Si se especifica, solo empuja las variantes_habilitadas de ese Provider '
                'y sincroniza el scope en Odoo (company_ids de vehiculo.variante). '
                'Requiere que el Provider tenga odoo_company_id configurado.'
            ),
        )

    def handle(self, *args, **options):
        dry_run       = options['dry_run']
        only_unlinked = options['only_unlinked']
        force         = options['force']
        provider_id   = options.get('provider_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY-RUN: no se guardará nada'))

        odoo = OdooConnector()
        if not odoo._authenticate():
            self.stderr.write(self.style.ERROR('❌ No se pudo conectar a Odoo'))
            return

        self.stdout.write(f'✅ Conectado a Odoo (UID: {odoo._uid})')

        # ── Resolución del queryset y company_id de scope ───────────────────
        odoo_company_id = None

        if provider_id:
            from apps.marketplace.models import Provider
            try:
                provider = Provider.objects.get(pk=provider_id)
            except Provider.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'❌ Provider con id={provider_id} no encontrado'))
                return

            if not provider.odoo_company_id:
                self.stderr.write(self.style.ERROR(
                    f'❌ Provider "{provider.name}" no tiene odoo_company_id. '
                    'Configúralo en Odoo primero (acción "Aprobar y configurar Odoo").'
                ))
                return

            odoo_company_id = provider.odoo_company_id
            qs = provider.variantes_habilitadas.select_related(
                'modelo__marca', 'motor', 'transmision', 'traccion'
            )
            self.stdout.write(
                f'🏢 Scope proveedor: {provider.name} (company_id={odoo_company_id})'
            )
        else:
            qs = VariantVehiculo.objects.select_related(
                'modelo__marca', 'motor', 'transmision', 'traccion'
            )

        # Filtro --only-unlinked aplica en ambos modos
        if only_unlinked and not force:
            qs = qs.filter(odoo_variante_id__isnull=True)

        total    = qs.count()
        created  = 0
        linked   = 0
        skipped  = 0
        errors   = 0

        self.stdout.write(f'📋 Variantes a procesar: {total}')

        # Cachés en memoria para evitar queries repetidas a Odoo
        marca_cache     = {}   # {django_marca_id: odoo_id}
        modelo_cache    = {}   # {django_modelo_id: odoo_id}
        motor_cache     = {}   # {django_motor_id: odoo_id}
        trans_cache     = {}   # {django_trans_id: odoo_id}
        traccion_cache  = {}   # {django_traccion_id: odoo_id}

        # Acumula odoo_variante_ids del scope para el sync final
        pushed_odoo_variante_ids = []

        for variante in qs.iterator():
            try:
                modelo     = variante.modelo
                marca      = modelo.marca
                motor      = variante.motor
                transmision = variante.transmision
                traccion   = variante.traccion

                if dry_run:
                    self.stdout.write(
                        f'  [DRY] {variante} → odoo_variante_id={variante.odoo_variante_id or "?"}'
                    )
                    skipped += 1
                    if variante.odoo_variante_id:
                        pushed_odoo_variante_ids.append(variante.odoo_variante_id)
                    continue

                with transaction.atomic():
                    # Marca
                    if marca.id not in marca_cache:
                        marca_cache[marca.id] = odoo.push_marca(
                            marca.nombre, marca.slug, marca.id
                        )
                    marca_odoo_id = marca_cache[marca.id]

                    # Modelo
                    if modelo.id not in modelo_cache:
                        modelo_cache[modelo.id] = odoo.push_modelo(
                            modelo.nombre, modelo.slug, marca_odoo_id, modelo.id
                        )
                    modelo_odoo_id = modelo_cache[modelo.id]

                    # Motor
                    if motor.id not in motor_cache:
                        motor_cache[motor.id] = odoo.push_motor(
                            motor.combustible, motor.cilindrada_cc,
                            motor.codigo_motor, motor.tecnologia, motor.id
                        )
                    motor_odoo_id = motor_cache[motor.id]

                    # Transmision
                    if transmision.id not in trans_cache:
                        trans_cache[transmision.id] = odoo.push_transmision(
                            transmision.tipo, transmision.velocidades, transmision.id
                        )
                    trans_odoo_id = trans_cache[transmision.id]

                    # Traccion
                    if traccion.id not in traccion_cache:
                        traccion_cache[traccion.id] = odoo.push_traccion(
                            traccion.tipo, traccion.id
                        )
                    traccion_odoo_id = traccion_cache[traccion.id]

                    # Variante
                    odoo_variante_id = odoo.push_variante(
                        modelo_odoo_id, motor_odoo_id, trans_odoo_id,
                        traccion_odoo_id, variante.anio_desde, variante.anio_hasta,
                        variante.id, variante.import_code
                    )

                    # Vincular en Django si cambió
                    if variante.odoo_variante_id != odoo_variante_id:
                        VariantVehiculo.objects.filter(pk=variante.pk).update(
                            odoo_variante_id=odoo_variante_id
                        )
                        created += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✨ Vinculada: {variante} → odoo_id={odoo_variante_id}'
                            )
                        )
                    else:
                        linked += 1

                    pushed_odoo_variante_ids.append(odoo_variante_id)

            except Exception as e:
                errors += 1
                logger.error(f'Error procesando variante {variante}: {e}', exc_info=True)
                self.stderr.write(
                    self.style.ERROR(f'  ❌ Error en {variante}: {e}')
                )

        # ── Sincronizar scope en Odoo (solo cuando hay un provider específico) ──
        if odoo_company_id and not dry_run and pushed_odoo_variante_ids:
            self.stdout.write('')
            self.stdout.write(
                f'🔒 Sincronizando scope en Odoo para company_id={odoo_company_id}...'
            )
            try:
                scope_result = odoo.sync_full_scope_for_company(
                    pushed_odoo_variante_ids, odoo_company_id
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'   ✅ Scope actualizado: '
                        f'+{scope_result["added"]} variantes, '
                        f'-{scope_result["removed"]} variantes revocadas'
                    )
                )
            except Exception as e:
                logger.error(f'Error sincronizando scope: {e}', exc_info=True)
                self.stderr.write(
                    self.style.ERROR(f'  ❌ Error al sincronizar scope en Odoo: {e}')
                )
        elif odoo_company_id and dry_run:
            self.stdout.write(
                f'  [DRY] sync_full_scope_for_company({len(pushed_odoo_variante_ids)} variantes, '
                f'company_id={odoo_company_id}) — no ejecutado'
            )

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write('📊 RESUMEN PUSH VEHÍCULOS')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Total variantes procesadas: {total}')
        self.stdout.write(f'  ✨ Nuevas vinculaciones:   {created}')
        self.stdout.write(f'  🔄 Ya vinculadas (sin cambio): {linked}')
        self.stdout.write(f'  ⏭️  Omitidas (dry-run):     {skipped}')
        self.stdout.write(f'  ❌ Errores:                {errors}')
        if errors == 0:
            self.stdout.write(self.style.SUCCESS('✅ Push completado sin errores'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Completado con {errors} error(es)'))
