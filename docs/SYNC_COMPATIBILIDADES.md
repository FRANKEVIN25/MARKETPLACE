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

- **Odoo (addon `ecomp`)**
   - `services/odoo/addons/ecomp/models/vehicle_models.py`
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

En Odoo se modela con `autopart.compatibility` del módulo `ecomp`:

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

4. SYNC trae las compatibilidades a Django en una fase separada y de baja frecuencia
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
7. La sync nocturna de compatibilidades trae los cambios a Django.
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
sync_provider_catalog_snapshot / sync_products  → ventana nocturna de catálogo
sync_all_compatibility                         → ventana nocturna separada
sync_all_stock                                 → intervalo corto y configurable
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
| `apps/sync/connector/vehicles.py` | Métodos de push con estrategia 3 vías + caché |
| `apps/sync/connector/compatibility.py` | Lectura de `autopart.compatibility` y `vehiculo.variante` en lote |
| `apps/sync/services/compatibility.py` | Sync de compatibilidades y resolución bidireccional de variante |
| `apps/sync/tasks.py` → `sync_all_compatibility()` / `sync_provider_compatibility()` | Tareas Celery de compatibilidades |
| `apps/sync/models.py` | `ProviderSyncState` para observabilidad por provider y por fase |
| `apps/sync/services/observability.py` | Persistencia de inicio/fin/estado/métricas de cada fase |
| `apps/sync/management/commands/sync_compatibility.py` | Ejecución manual de compatibilidades vía CLI |
| `services/odoo/addons/ecomp/models/vehicle_models.py` | Modelos Odoo — `django_external_id` sin `readonly` a nivel de campo |
| `services/odoo/addons/ecomp/views/vehicle_views.xml` | Vistas Odoo — `django_external_id` con `readonly="1"` (solo UI) |
| `services/odoo/addons/ecomp/models/compatibility.py` | `autopart.compatibility` en Odoo |

---

## Cómo ejecutar (referencia rápida)

```bash
# Push vehículos Django → Odoo (vinculación bidireccional)
docker exec -it ecomparts-backend python manage.py push_vehicles
docker exec -it ecomparts-backend python manage.py push_vehicles --only-unlinked
docker exec -it ecomparts-backend python manage.py push_vehicles --dry-run

# Sync completa de catálogo, imágenes y compatibilidades
docker exec -it ecomparts-backend python manage.py sync_products

# Solo compatibilidades
docker exec -it ecomparts-backend python manage.py sync_compatibility

# Sin compatibilidades
docker exec -it ecomparts-backend python manage.py sync_products --skip-compat

# Solo stock rápido
docker exec -it ecomparts-backend python manage.py sync_stock

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

- La sync sí reconcilia el conjunto activo: si una compatibilidad deja de venir desde Odoo, se elimina de Django en la fase de reconcile.
- El catálogo de variantes es universal y compartido entre proveedores. Múltiples proveedores pueden tener compatibilidades hacia la misma `VariantVehiculo`.
- `unique_together = ('producto', 'variante')` garantiza idempotencia en `CompatibilidadProducto`.
- `fitment_notes` (Odoo) → `notas_instalacion` en Django, truncado a 255 chars.
- La fase de compatibilidades ya corre separada del snapshot de catálogo y del stock, y deja estado persistido por provider en `ProviderSyncState`.

---

## Arquitectura operativa actual

La arquitectura más sana para compatibilidades quedó así:

- `push_vehicles` mantiene el catálogo vehicular y sus anclas bidireccionales.
- Los proveedores crean y editan compatibilidades en Odoo.
- Django sincroniza compatibilidades en una fase propia, separada de catálogo e imágenes.
- La frecuencia recomendada es baja o nocturna, no al ritmo del stock.
- Cada corrida deja métricas y estado por provider para operación y soporte.

Eso evita mezclar en una sola corrida:

- snapshot de catálogo,
- binarios de imágenes,
- stock rápido,
- y compatibilidades relacionales pesadas.

---

## Mejoras pendientes

### [REVISION PENDIENTE] Compatibilidades diferenciales

**Estado:** Pendiente de revisión  
**Prioridad:** Media

Hoy la sync de compatibilidades funciona por reconcile del conjunto activo del provider, lo cual ya es correcto para la etapa actual del proyecto.

La mejora arquitectónica a revisar más adelante sería pasar de reconcile completo a sync diferencial, por ejemplo usando un ancla adicional como:

- `odoo_compatibility_id` en Django,
- `write_date` remoto,
- o alguna versión/hash específico expuesto por Odoo.

Eso permitiría traer solo altas, cambios y bajas relevantes en vez de reconstruir el estado deseado completo en cada corrida.

Por ahora queda explícitamente como revisión futura, no como cambio necesario inmediato.

### [MEJORA] Auto-importar variantes nuevas creadas directamente en Odoo

**Estado:** Pendiente  
**Prioridad:** Media

Cuando un proveedor crea una variante en Odoo sin que Django la haya empujado, la sync actualmente skipea esa compatibilidad. La mejora añadiría una Vía 3 en `_resolve_django_variant`: si no se encuentra por ninguna de las 2 vías existentes, intentar crear la variante en Django automáticamente a partir de los datos de Odoo.

**Riesgo:** requiere que todos los sub-registros (modelo, motor, transmision, traccion) también existan en Django con sus respectivos `django_external_id` en Odoo. Sin eso, la auto-creación fallaría silenciosamente o crearía datos parciales.

**Archivos a modificar:**
- `apps/sync/services/compatibility.py` → `_resolve_django_variant()`: añadir Vía 3
- `apps/vehicles/models.py`: posible campo `is_pending_review` para variantes auto-importadas

### [PROPUESTA] Importación de compatibilidades por códigos cortos en una sola celda

**Estado:** Propuesta funcional  
**Prioridad:** Alta si se quiere carga masiva desde Excel/CSV

### Objetivo

Permitir una columna de importación como esta en productos:

```text
Compatibilidad = var0001,var0004,var0007
```

La intención es que una sola celda represente varias variantes compatibles, sin obligar al usuario a preparar un archivo separado con una fila por compatibilidad.

### Situación actual

Hoy el sistema ya tiene anclas bidireccionales para compatibilidades, pero no tiene todavía un código corto de importación para variantes equivalente al de categorías:

- **Django**
   - `VariantVehiculo` tiene `odoo_variante_id`.
   - Ese campo sirve para resolver sync Odoo → Django.
   - **No existe** un `import_code` corto, estable y legible para variantes.
- **Odoo**
   - `vehiculo.variante` tiene `django_external_id`.
   - Ese campo guarda el PK de Django como texto.
   - Sirve para vinculación técnica vía RPC, pero **no es ideal** como valor operativo de importación manual.
- **Modelo de compatibilidad**
   - La relación real no es un Many2many plano: se materializa como `autopart.compatibility` en Odoo y `CompatibilidadProducto` en Django.
   - Por eso la compatibilidad es una entidad propia y no solo una lista de IDs pegada al producto.

### Conclusión técnica

Con el diseño actual, **Django no está listo** para soportar bien una importación amigable del tipo `var0001,var0004,var0007`.

Sí existe una clave técnica (`django_external_id`), pero faltan dos piezas para que el flujo sea limpio y mantenible:

1. Un **código corto y estable** de variante generado en Django.
2. Una **capa de importación en Odoo** que convierta una celda multi-valor en múltiples registros `autopart.compatibility`.

### Propuesta recomendada

#### 1. Añadir código corto estable en Django para variantes

Agregar un campo nuevo en `apps/vehicles/models.py`:

```python
import_code = models.CharField(
      max_length=16,
      unique=True,
      editable=False,
      blank=True,
      help_text="Código corto y estable para proyección de compatibilidades en Odoo."
)
```

Formato sugerido:

- `VAR0001`
- `VAR0002`
- `VAR0003`

Requisitos del campo:

- No depender del nombre de la variante.
- No depender del PK de Django.
- No cambiar si se edita modelo, motor, años o tracción.
- Ser visible en admin/API para facilitar exportaciones y soporte.

#### 2. Proyectar ese código a Odoo

Agregar campo espejo en `vehiculo.variante`:

- `django_import_code`

Y mantenerlo desde `push_vehicles`, igual que hoy se mantiene `django_external_id`.

Con eso, cada variante en Odoo tendría dos anclas distintas:

- `django_external_id` → vínculo técnico con el PK Django.
- `django_import_code` → código corto operativo para importaciones.

### Dos formas de importar compatibilidades

#### Opción A — Importación estándar de Odoo, una fila por compatibilidad

Archivo recomendado:

```text
External ID,Name,Product Category,Compatibility/Product,Compatibility/Variant
product_template_101,Soporte de Iphone,ecomp.cat_lef035,product_template_101,ecomp.var_var0001
product_template_101,Soporte de Iphone,ecomp.cat_lef035,product_template_101,ecomp.var_var0004
product_template_101,Soporte de Iphone,ecomp.cat_lef035,product_template_101,ecomp.var_var0007
```

Ventajas:

- Usa el modelo real de Odoo.
- Es más transparente para depuración.
- Permite luego agregar `fitment_notes` por fila.
- No requiere parseo especial dentro de una celda.

Desventaja:

- Duplica filas del producto cuando hay muchas compatibilidades.

#### Opción B — Importación amigable con una sola celda multi-valor

Archivo deseado por negocio, dos formas:

```text
External ID,Name,Product Category,Compatibilidad
product_template_101,Soporte de Iphone,ecomp.cat_lef035,"var0001,var0004,var0007"
product_template_101,Soporte de Iphone,ecomp.cat_lef035,"ecomp.var_var0001,ecomp.var_var0004,ecomp.var_var0007"
```

Esta opción **no la resuelve bien el importador estándar de Odoo** porque:

- `compatibility_ids` es un One2many, no un Many2many simple.
- Odoo no va a expandir automáticamente esa celda en varios registros `autopart.compatibility`.
- La relación además puede tener metadatos propios como `fitment_notes`.

Si se quiere este formato, hace falta una personalización en Odoo. La más limpia sería:

- Agregar un campo auxiliar de importación en `product.template`, por ejemplo `compatibility_import_codes_raw`.
- Parsear la cadena en `create()` y `write()` o en un método explícito de postproceso.
- Resolver cada token contra `vehiculo.variante.django_import_code`.
- Crear o reactivar registros en `autopart.compatibility`.
- Desactivar o eliminar compatibilidades que ya no estén presentes, si se quiere modo reconcile.

### Recomendación de arquitectura

La recomendación más sólida es implementar en dos etapas:

**Etapa 1 — Base estable**

- Añadir `VariantVehiculo.import_code` en Django.
- Añadir `vehiculo.variante.django_import_code` en Odoo.
- Proyectar External IDs de variantes en Odoo con un esquema explícito, por ejemplo:
   - `ecomp.var_var0001`
   - `ecomp.var_var0004`
   - `ecomp.var_var0007`
- Habilitar importación de compatibilidades en archivo separado o en varias filas por producto.

**Etapa 2 — UX simplificada**

- Implementar columna única `Compatibilidad` con lista separada por comas.
- Resolver internamente esos códigos a múltiples `autopart.compatibility`.
- Mantener el archivo de una fila por producto como formato amigable para operación.

### Decisión sugerida

Si el objetivo inmediato es destrabar carga masiva sin demasiada personalización, conviene:

1. Crear `import_code` en `VariantVehiculo` en Django.
2. Sincronizarlo a Odoo como `django_import_code`.
3. Generar External IDs de variantes tipo `ecomp.var_var0001`.
4. Importar compatibilidades en formato fila-por-fila sobre `autopart.compatibility` o con columnas hijas en productos.

### Estado actual de la etapa 1

Los puntos 1, 2 y 3 ya quedaron cubiertos:

- Django genera `VariantVehiculo.import_code`.
- `push_vehicles` proyecta ese código a Odoo como `vehiculo.variante.django_import_code`.
- El addon `ecomp` materializa automáticamente `ir.model.data` para variantes con formato `ecomp.var_var0001`.

### Importación fila-por-fila recomendada hoy

La ruta recomendada inmediata es importar directamente sobre el modelo `autopart.compatibility` desde el menú **Autoparts > Compatibilidades**.

Archivo sugerido:

```text
External ID,Product/External ID,Variant/External ID,fitment_notes,active
compat_prod101_var0001,product_template_101,ecomp.var_var0001,"Solo AT",1
compat_prod101_var0004,product_template_101,ecomp.var_var0004,"",1
compat_prod101_var0007,product_template_101,ecomp.var_var0007,"Requiere kit adicional",1
```

Notas operativas:

- `Product/External ID` debe apuntar al External ID real del `product.template` en Odoo.
- `Variant/External ID` debe usar el XML ID generado por el addon, por ejemplo `ecomp.var_var0001`.
- `External ID` de cada compatibilidad conviene generarlo por fila para que futuras reimportaciones actualicen en vez de duplicar.
- Si la UI de importación muestra etiquetas traducidas, puede variar el nombre visual de las columnas, pero conceptualmente los campos son `product_tmpl_id`, `variant_id`, `fitment_notes` y `active`.

Con esta ruta no hace falta todavía un importador custom para celda multi-valor.

Si el objetivo es una UX de Excel mucho más simple para usuarios no técnicos, entonces además de lo anterior conviene construir un importador custom para la celda multi-valor.

### Veredicto

Para compatibilidades, **sí necesitamos un campo adicional en Django** si queremos un flujo realmente mantenible y amigable:

- `odoo_variante_id` sirve como cache operativo, pero no como código portable de importación.
- `django_external_id` sirve como ancla técnica, pero no como código corto de negocio.
- El campo faltante es un `import_code` estable para `VariantVehiculo`.

Sin ese campo, se puede seguir sincronizando por RPC y por IDs internos, pero no queda una base limpia para importaciones humanas tipo `var0001,var0004,var0007`.
