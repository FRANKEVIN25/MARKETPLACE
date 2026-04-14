# Sincronización de Compatibilidades: Odoo ↔ Django

## Resumen de lo implementado

A continuación se listan los cambios importantes que se han implementado para soportar el scope de variantes por proveedor y la sincronización bidireccional entre Django y Odoo.

- **Django (backend)**
   - `apps/marketplace/models.py`
      - Campo `Provider.variantes_habilitadas` → M2M a `VariantVehiculo`, tabla intermedia `marketplace_provider_variantesvehiculo`.
      - Signal `m2m_changed` → cuando el admin agrega/quita variantes del scope, llama automáticamente a `scope_variante_for_company` / `unscope_variante_from_company` en Odoo sin intervención manual.
   - `apps/marketplace/migrations/0008_provider_variantes_habilitadas.py`
      - Migración auto-contenida que depende de `vehicles.0002`.
   - `apps/marketplace/admin.py`
      - `filter_horizontal = ('variantes_habilitadas',)` → widget de selección con búsqueda en tiempo real.
      - Nuevo fieldset "🚗 Scope de Vehículos" con descripción instructiva.
      - Columna "Variantes" en el listado de providers.
      - Acción `push_variantes_a_odoo` → ejecuta `push_vehicles --provider-id` desde la UI del admin.
   - `apps/vehicles/admin.py`
      - `search_fields` expandido (tecnología, año hasta) para mejor búsqueda en el widget M2M.
      - Columna `odoo_variante_id` y `Providers` en el listado.
      - `readonly_fields = ('odoo_variante_id',)`.

- **OdooConnector**
   - `apps/sync/odoo_connector.py`
      - Tres métodos nuevos en la sección "VEHICLE SCOPE POR PROVEEDOR":
         - `scope_variante_for_company(odoo_variante_id, company_id)` → ORM command `(4, id)`, idempotente.
         - `unscope_variante_from_company(odoo_variante_id, company_id)` → ORM command `(3, id)`.
         - `sync_full_scope_for_company(odoo_variante_ids, company_id)` → diff completo en 2 batch-writes, garantiza consistencia total.

- **push_vehicles**
   - `apps/vehicles/management/commands/push_vehicles.py`
      - Nuevo flag `--provider-id=N` → usa `provider.variantes_habilitadas` como queryset.
      - Al finalizar el push con `--provider-id`, llama a `sync_full_scope_for_company` → añade variantes nuevas al scope y revoca las que ya no están (en un solo par de batch-writes).
      - `--only-unlinked` sigue funcionando en modo provider.

- **Odoo (addon `ecomparts_integration`)**
   - `services/odoo/addons/ecomparts_integration/models/vehicle_models.py`
      - Campo `VarianteVehiculo.company_ids` → `Many2many` a `res.company`, tabla `vehiculo_variante_company_rel`.
   - `security/ir_rules.xml` (nuevo)
      - Record Rule `rule_vehiculo_variante_by_company`: aplica a `group_user`, dominio `['|', ('company_ids', '=', False), ('company_ids', 'in', [company_id])]`.
      - Variantes sin scope asignado (`company_ids` vacío) son visibles para todos → fallback seguro durante puesta en marcha.
   - `__manifest__.py`
      - Registra `security/ir_rules.xml` en `data`.
   - `views/product_views.xml`
      - `no_quick_create: True` en `variant_id` (el Record Rule ya filtra el queryset a nivel ORM).

Estos cambios permiten que los proveedores vean solo las variantes que les corresponden en Odoo sin duplicar el catálogo maestro (marcas/modelos/motores/etc.) en múltiples compañías, mejorando UX y manteniendo Django como fuente de verdad para el catálogo.


## Qué es una compatibilidad

Una compatibilidad define que **un producto específico** (ej: "Pastilla de freno Brembo") funciona en **una variante de vehículo específica** (ej: Toyota Corolla 2.0L AT 4x2 2018-2023).

En Django esto se modela con la tabla intermedia `CompatibilidadProducto`:

```
Product ──────────────────── CompatibilidadProducto ──────── VariantVehiculo
(odoo_template_id=12)         (notas_instalacion)             (odoo_variante_id=7)
```

En Odoo se modela con `autopart.compatibility` del módulo `ecomparts_integration`:

```
product.template ──── autopart.compatibility ──── vehiculo.variante
(id=12)               (fitment_notes)             (id=7, django_external_id="42")
```

---

## Arquitectura: Django como catálogo maestro

El catálogo de variantes de vehículos es **universal** — no pertenece a un tenant individual. Un Toyota Corolla 2.0L AT 4x2 2018-2023 es **el mismo registro** sin importar qué proveedor venda repuestos para él.

```
Django (catálogo maestro)          Odoo (copia sincronizada)
─────────────────────────          ─────────────────────────
VariantVehiculo.id = 42    ←──→    vehiculo.variante.id = 7
  odoo_variante_id = 7             django_external_id = "42"
```

**Regla de oro:** Django crea/aprueba las variantes. Odoo las recibe via `push_vehicles`. Los proveedores usan las variantes de Odoo para asignar compatibilidades a sus productos.

---

## Los dos vínculos de anclaje

| Campo | Dónde vive | Quién lo escribe | Propósito |
|-------|-----------|-----------------|-----------|
| `VariantVehiculo.odoo_variante_id` | Django | Comando `push_vehicles` | Lookup rápido Django → Odoo |
| `vehiculo.variante.django_external_id` | Odoo | Comando `push_vehicles` (via RPC) | Lookup inverso Odoo → Django |

`django_external_id` es **readonly en la UI de Odoo** (bloquea edición manual) pero
**writable via RPC** (el comando push puede escribirlo). Esta separación es intencional:
solo el sistema, no los usuarios de Odoo, debe modificar esa relación.

> **Nota técnica:** el `readonly=True` a nivel de campo en Odoo bloquea también las
> escrituras via RPC. Por eso se eliminó del modelo (vehicle_models.py) y se aplicó
> solo en las vistas (vehicle_views.xml con `readonly="1"`). El resultado es idéntico
> visualmente pero permite que el push funcione.

---

## El flujo completo: Django → Odoo → Django

```
1. ADMIN crea variante en Django
   VariantVehiculo(modelo=Corolla, motor=2.0L, trans=AT, trac=4x2, 2018-2023)
   → odoo_variante_id = NULL (aún no vinculada)

2. ADMIN corre push_vehicles
   → Crea/encuentra vehiculo.variante en Odoo
   → Escribe django_external_id = "42" en Odoo (via RPC)
   → Guarda odoo_variante_id = 7 en Django
   → Variante VINCULADA en ambos sistemas

3. PROVEEDOR en su UI de Odoo
   → Ve la variante "Toyota Corolla 2.0L AT 4x2 2018-2023" disponible
   → Abre su producto "Pastilla de freno Brembo"
   → Agrega compatibilidad seleccionando la variante

4. SYNC trae las compatibilidades a Django (cada hora via Celery Beat)
   → Lee autopart.compatibility desde Odoo
   → Resuelve la variante: odoo_variante_id=7 → VariantVehiculo.id=42 (Vía 1)
   → Crea CompatibilidadProducto(producto=..., variante_id=42)
```

---

## Flujo de resolución de variante en la sync (2 vías)

```python
def _resolve_django_variant(odoo_variant_id, odoo_variant_map):
    # Vía 1: lookup directo por odoo_variante_id (post-push, el más frecuente)
    try:
        return VariantVehiculo.objects.get(odoo_variante_id=odoo_variant_id)
    except VariantVehiculo.DoesNotExist:
        pass

    # Vía 2: usar django_external_id guardado en Odoo (fallback)
    odoo_record = odoo_variant_map.get(odoo_variant_id)
    if odoo_record and odoo_record.get('django_external_id'):
        django_pk = int(odoo_record['django_external_id'])
        return VariantVehiculo.objects.get(pk=django_pk)
    # Si ninguna resuelve → retorna None → sync skipea + warning en log
```

---

## Comando push_vehicles

```bash
# Ver qué haría sin guardar nada
docker exec -it ecomparts-backend python manage.py push_vehicles --dry-run

# Push completo de todo el catálogo
docker exec -it ecomparts-backend python manage.py push_vehicles

# Solo variantes aún no vinculadas (más rápido, para runs incrementales en produccion)
docker exec -it ecomparts-backend python manage.py push_vehicles --only-unlinked

# Forzar re-empuje aunque ya estén vinculadas (útil después de recrear DB de Odoo)
docker exec -it ecomparts-backend python manage.py push_vehicles --force
```

El comando es **idempotente**: corre tan seguido como sea necesario. Internamente usa una
estrategia de 3 vías para cada entidad (marca, modelo, motor, transmisión, tracción, variante):

```
1. Busca por django_external_id  → ya vinculado, retorna odoo_id (sin writes)
2. Busca por clave natural        → existe sin vincular, vincula y retorna
3. Crea en Odoo                   → registro genuinamente nuevo
```

Usa cachés en memoria para marcas/modelos/motores/etc. compartidos: si 100 variantes
son del mismo modelo, el modelo solo se busca/crea una vez.

---

## Escenarios de producción

### Escenario A — Nuevo proveedor se afilia (el más común)

Un proveedor nuevo llega con un catálogo de N productos con sus vehiculos de compatibilidad.

```
1. Admin revisa qué variantes necesita el proveedor.
2. Las que ya existen en Django → ya están disponibles en Odoo (post-push inicial).
3. Las que no existen → Admin las crea en Django.
4. Admin corre:
     python manage.py push_vehicles --only-unlinked
   → Solo las nuevas se envían a Odoo.
5. Proveedor abre Odoo y ve todas las variantes disponibles.
6. Proveedor crea sus productos y asigna compatibilidades desde la UI de Odoo.
7. La sync (Celery Beat, cada hora) trae las compatibilidades a Django.
```

### Escenario B — Proveedor necesita una variante que no existe

```
Opción 1 — Coordinado con el admin (recomendado):
  1. Proveedor solicita al admin que agregue la variante.
  2. Admin la crea en Django (panel admin o shell).
  3. Admin corre: python manage.py push_vehicles --only-unlinked
  4. Proveedor la ve disponible en Odoo inmediatamente.

Opción 2 — Proveedor la crea en Odoo directamente:
  → django_external_id queda vacío.
  → La sync skipea esa compatibilidad con warning:
    "⚠️  Sin match para odoo_variante_id=X — ejecutar push de vehículos primero"
  → Admin debe crear la variante en Django y correr push_vehicles --only-unlinked.
```

### Escenario C — Catálogo de 1000+ variantes en producción

El sistema escala bien porque:

- `push_vehicles` cachea marcas/modelos/motores en memoria → evita queries repetidas a Odoo por entidades compartidas entre variantes
- `--only-unlinked` procesa solo las nuevas en cada run incremental
- La sync de compatibilidades hace exactamente **2 queries a Odoo** independientemente del volumen
- `odoo_variante_id` en Django permite lookup O(1) por cada compatibilidad (Vía 1)

### Escenario D — Se recrea la DB de Odoo (dev/staging)

```
1. Los odoo_variante_id en Django apuntan a IDs que ya no existen en Odoo.
2. Correr: python manage.py push_vehicles --force
   → Re-vincula toda la jerarquía con los nuevos IDs de Odoo.
3. La sync vuelve a funcionar.
```

### Escenario E — Sync continua (producción estable)

Una vez que el catálogo está construido y vinculado:

```
push_vehicles  → solo al agregar variantes nuevas en Django
sync_products  → cada hora (Celery Beat), trae producto + compatibilidades
```

El catálogo crece gradualmente: cada nuevo proveedor que se afilia puede traer variantes
que antes no estaban. El admin revisa, agrega las que faltan en Django, y corre push_vehicles.

### Escenario F — 100+ marcas y miles de variantes: scope por proveedor

**El problema:** con un catálogo de 10 000+ variantes, mostrar todas en el selector de
compatibilidades de Odoo es inusable. Un proveedor de repuestos Toyota no debería ver
variantes de BMW, ni un proveedor de camionetas debería ver sedanes de ciudad.



## Primera puesta en marcha (entorno nuevo)

```bash
# 1. Cargar vehículos base en Django
docker exec -it ecomparts-backend python manage.py seed

# 2. Empujar catálogo hacia Odoo (establece vínculos bidireccionales)
docker exec -it ecomparts-backend python manage.py push_vehicles

# 3. Verificar vínculos
docker exec -it ecomparts-backend python manage.py shell -c "
from apps.vehicles.models import VariantVehiculo
total = VariantVehiculo.objects.count()
vinculadas = VariantVehiculo.objects.filter(odoo_variante_id__isnull=False).count()
print(f'{vinculadas}/{total} variantes vinculadas con Odoo')
"

# 4. Los proveedores crean compatibilidades en su UI de Odoo

# 5. Sync trae las compatibilidades a Django
docker exec -it ecomparts-backend python manage.py sync_products
```

---

## Archivos involucrados

| Archivo | Rol |
|---------|-----|
| `apps/vehicles/models.py` | `VariantVehiculo.odoo_variante_id` (ancla Django→Odoo) |
| `apps/vehicles/management/commands/push_vehicles.py` | **Push completo** del catálogo → Odoo con vinculación bidireccional |
| `apps/products/models.py` | `CompatibilidadProducto` (tabla through M2M) |
| `apps/sync/odoo_connector.py` → `push_marca/modelo/motor/transmision/traccion/variante()` | Métodos de push con estrategia 3 vías + caché |
| `apps/sync/odoo_connector.py` → `get_compatibilities()` | Lee `autopart.compatibility` en lote |
| `apps/sync/odoo_connector.py` → `get_vehicle_variants()` | Lee `vehiculo.variante` con `django_external_id` |
| `apps/sync/tasks.py` → `sync_provider_compatibility()` | Tarea Celery de compatibilidades |
| `apps/sync/tasks.py` → `_resolve_django_variant()` | Resolución bidireccional de variante (2 vías) |
| `apps/sync/tasks.py` → `sync_provider_products()` paso 5 | Llama a compat al final de la sync completa |
| `apps/products/management/commands/sync_products.py` → `_sync_compatibility()` | Mismo flujo vía CLI |
| `services/odoo/addons/ecomparts_integration/models/vehicle_models.py` | Modelos Odoo — `django_external_id` sin `readonly` a nivel de campo |
| `services/odoo/addons/ecomparts_integration/views/vehicle_views.xml` | Vistas Odoo — `django_external_id` con `readonly="1"` (solo UI) |
| `services/odoo/addons/ecomparts_integration/models/compatibility.py` | `autopart.compatibility` en Odoo |

---

## Cómo ejecutar (referencia rápida)

```bash
# Push vehículos Django → Odoo (vinculación bidireccional)
docker exec -it ecomparts-backend python manage.py push_vehicles
docker exec -it ecomparts-backend python manage.py push_vehicles --only-unlinked
docker exec -it ecomparts-backend python manage.py push_vehicles --dry-run

# Sync completa (categorías + almacenes + productos + stock + compatibilidades)
docker exec -it ecomparts-backend python manage.py sync_products

# Solo compatibilidades
docker exec -it ecomparts-backend python manage.py sync_products --skip-stock

# Sin compatibilidades
docker exec -it ecomparts-backend python manage.py sync_products --skip-compat

# Dry-run
docker exec -it ecomparts-backend python manage.py sync_products --dry-run
```

### Tarea Celery directa (Django shell o worker)
```python
from apps.sync.tasks import sync_provider_compatibility
result = sync_provider_compatibility(provider_id=2)
print(result)
# {
#   'provider': 'Accesorios Axel',
#   'compat_created': 12,
#   'compat_updated': 3,
#   'skipped_no_product': 0,
#   'skipped_no_variant': 1,
#   'errors': 0
# }
```

---

## Eficiencia de queries

| Paso | Queries a Odoo |
|------|---------------|
| `push_vehicles`: por tipo único de entidad (marca/modelo/…) | ≤2 con caché en memoria |
| `get_compatibilities` | 1 (todos los templates del provider) |
| `get_vehicle_variants` | 1 (todos los IDs únicos en un `in`) |
| Resolución Vía 1 en sync (odoo_variante_id) | 0 queries adicionales a Odoo |
| Total queries Odoo por sync de compatibilidades | **2** |

---

## Consideraciones importantes

- La sync **no borra** compatibilidades en Django cuando se desactivan en Odoo (`active=False`). Quedan hasta limpieza manual. Para limpieza activa habría que comparar el conjunto completo.
- El catálogo de variantes es universal y compartido entre proveedores. Múltiples proveedores pueden tener compatibilidades hacia la misma `VariantVehiculo`.
- `unique_together = ('producto', 'variante')` garantiza idempotencia en `CompatibilidadProducto`.
- `fitment_notes` (Odoo) → `notas_instalacion` en Django, truncado a 255 chars.

---

## Mejoras pendientes

### [MEJORA] Auto-importar variantes nuevas creadas directamente en Odoo

**Estado:** Pendiente  
**Prioridad:** Media

Cuando un proveedor crea una variante en Odoo sin que Django la haya empujado, la sync actualmente skipea esa compatibilidad. La mejora añadiría una Vía 3 en `_resolve_django_variant`: si no se encuentra por ninguna de las 2 vías existentes, intentar crear la variante en Django automáticamente a partir de los datos de Odoo.

**Riesgo:** requiere que todos los sub-registros (modelo, motor, transmision, traccion) también existan en Django con sus respectivos `django_external_id` en Odoo. Sin eso, la auto-creación fallaría silenciosamente o crearía datos parciales.

**Archivos a modificar:**
- `apps/sync/tasks.py` → `_resolve_django_variant()`: añadir Vía 3
- `apps/vehicles/models.py`: posible campo `is_pending_review` para variantes auto-importadas


# Sincronización de Compatibilidades: Odoo ↔ Django

## Resumen de lo implementado

A continuación se listan los cambios importantes que se han implementado para soportar el scope de variantes por proveedor y la sincronización bidireccional entre Django y Odoo.

- **Django (backend)**
   - `apps/marketplace/models.py`
      - Campo `Provider.variantes_habilitadas` → M2M a `VariantVehiculo`, tabla intermedia `marketplace_provider_variantesvehiculo`.
      - Signal `m2m_changed` → cuando el admin agrega/quita variantes del scope, llama automáticamente a `scope_variante_for_company` / `unscope_variante_from_company` en Odoo sin intervención manual.
   - `apps/marketplace/migrations/0008_provider_variantes_habilitadas.py`
      - Migración auto-contenida que depende de `vehicles.0002`.
   - `apps/marketplace/admin.py`
      - `filter_horizontal = ('variantes_habilitadas',)` → widget de selección con búsqueda en tiempo real.
      - Nuevo fieldset "🚗 Scope de Vehículos" con descripción instructiva.
      - Columna "Variantes" en el listado de providers.
      - Acción `push_variantes_a_odoo` → ejecuta `push_vehicles --provider-id` desde la UI del admin.
   - `apps/vehicles/admin.py`
      - `search_fields` expandido (tecnología, año hasta) para mejor búsqueda en el widget M2M.
      - Columna `odoo_variante_id` y `Providers` en el listado.
      - `readonly_fields = ('odoo_variante_id',)`.

- **OdooConnector**
   - `apps/sync/odoo_connector.py`
      - Tres métodos nuevos en la sección "VEHICLE SCOPE POR PROVEEDOR":
         - `scope_variante_for_company(odoo_variante_id, company_id)` → ORM command `(4, id)`, idempotente.
         - `unscope_variante_from_company(odoo_variante_id, company_id)` → ORM command `(3, id)`.
         - `sync_full_scope_for_company(odoo_variante_ids, company_id)` → diff completo en 2 batch-writes, garantiza consistencia total.

- **push_vehicles**
   - `apps/vehicles/management/commands/push_vehicles.py`
      - Nuevo flag `--provider-id=N` → usa `provider.variantes_habilitadas` como queryset.
      - Al finalizar el push con `--provider-id`, llama a `sync_full_scope_for_company` → añade variantes nuevas al scope y revoca las que ya no están (en un solo par de batch-writes).
      - `--only-unlinked` sigue funcionando en modo provider.

- **Odoo (addon `ecomparts_integration`)**
   - `services/odoo/addons/ecomparts_integration/models/vehicle_models.py`
      - Campo `VarianteVehiculo.company_ids` → `Many2many` a `res.company`, tabla `vehiculo_variante_company_rel`.
   - `security/ir_rules.xml` (nuevo)
      - Record Rule `rule_vehiculo_variante_by_company`: aplica a `group_user`, dominio `['|', ('company_ids', '=', False), ('company_ids', 'in', [company_id])]`.
      - Variantes sin scope asignado (`company_ids` vacío) son visibles para todos → fallback seguro durante puesta en marcha.
   - `__manifest__.py`
      - Registra `security/ir_rules.xml` en `data`.
   - `views/product_views.xml`
      - `no_quick_create: True` en `variant_id` (el Record Rule ya filtra el queryset a nivel ORM).

Estos cambios permiten que los proveedores vean solo las variantes que les corresponden en Odoo sin duplicar el catálogo maestro (marcas/modelos/motores/etc.) en múltiples compañías, mejorando UX y manteniendo Django como fuente de verdad para el catálogo.
