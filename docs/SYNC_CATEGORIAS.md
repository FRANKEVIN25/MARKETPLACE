# Sincronización de Categorías: Odoo ↔ Django

## Problema que resuelve

Odoo usa `product.category` con IDs auto-incrementales propios. Django usa `products.Category` con sus propios IDs auto-incrementales. Si se comparte una base de datos de vehículos o se recrea cualquiera de los dos sistemas, los IDs dejan de coincidir.

**La solución incorrecta** sería asumir que `odoo.category.id == django.category.id`. Basta con recrear la DB de Odoo para que esa relación se rompa silenciosamente.

**La solución implementada** es usar `odoo_category_id` como campo ancla en Django: guarda explícitamente el ID de Odoo y hace `update_or_create` por ese campo.

---

## Jerarquía canónica de 3 niveles

Las categorías son **universales** — no pertenecen a ningún tenant/proveedor. La estructura es idéntica en Odoo y en Django:

```
Nivel 1 (12)          Nivel 2 (30)               Nivel 3 (~60)
─────────────────────────────────────────────────────────────────
Motor y Compon…     Componentes Internos      Pistones, Empaques y Juntas
                    Distribución              Correas y Cadenas
                                              Tensores y Poleas
                    Admisión                  Filtros de Aire
                                              Mangueras de Admisión
                                              Sensores MAF y MAP

Sistema de Frenos   Fricción                  Pastillas de Freno
                                              Zapatas de Freno
                    Discos y Tambores         Discos de Freno
                                              Tambores de Freno
                    Hidráulico y ABS          Bombas de Freno
                                              Sensores ABS y Módulos

Suspensión y Dir.   Suspensión                Amortiguadores y Resortes
                                              Bases de Amortiguador
                    Dirección                 Cremalleras y Bombas
                                              Terminales de Dirección
                    Tren Delantero            Rótulas y Bujes
                                              Brazos de Suspensión

Transmisión         Embrague                  Kit de Embrague
                                              Disco y Prensa
                    Tracción                  Ejes y Homocinéticas
                                              Diferencial

Sist. Eléctrico…    Encendido y Carga         Bujías y Bobinas
                                              Baterías y Alternador
                    Sensores y Control        Sensores de Motor
                                              ECU y Módulos de Control

Iluminación         Faros                     Faros Delanteros
                                              Faros Traseros y Neblineros
                    Bombillas                 LED y Halógenos
                                              Xenón

Carrocería y Ext.   Exterior                  Parachoques y Capó
                                              Puertas y Paneles
                    Espejos y Accesorios      Espejos Retrovisores
                                              Molduras y Embellecedores
                    Limpieza Parabrisas       Plumillas Limpiaparabrisas
                                              Motores Limpiaparabrisas

Ruedas y Neumát.    Llantas                   Neumáticos
                    Aros                      Rines de Aluminio y Acero
                    Accesorios de Rueda       Pernos y Tuercas
                                              Válvulas de Inflado

Refrigeración…      Enfriamiento Motor        Radiadores y Termostatos
                                              Bombas de Agua
                    Aire Acondicionado        Compresores de AC
                                              Filtro de Habitáculo

Combustible…        Combustible               Bombas de Combustible
                                              Filtros de Combustible
                                              Inyectores
                    Escape                    Silenciadores y Tubos
                                              Catalizadores

Mantenimiento…      Aceites                   Aceite de Motor
                                              Aceite de Transmisión
                    Fluidos                   Refrigerante
                                              Líquido de Frenos
                    Filtros Mantenimiento     Filtro de Aire
                                              Filtro de Aceite
                                              Filtro de Combustible

Herramientas…       Herramientas              Llaves y Dados
                    Equipos de Diagnóstico    Escáner OBD2
                                              Gatas y Elevadores
                    Accesorios para Vehículo  Alarmas y Cámaras
                                              Fundas y Protectores
```

---

## Fuente de verdad: archivos de definición

La jerarquía se define en **dos lugares** que deben mantenerse sincronizados entre sí:

| Sistema | Archivo fuente | Modelo |
|---------|---------------|--------|
| Odoo    | `services/odoo/addons/ecomparts_integration/data/categories_seed.xml` | `product.category` |
| Django  | `services/backend/apps/products/management/commands/seed_categories.py` | `products.Category` (MPTT) |

> **Regla:** si añades, renombras o mueves una categoría, actualiza **ambos archivos** a la vez.

---

## Modelo Django: `Category`

```python
# apps/products/models.py
class Category(MPTTModel):
    name            = models.CharField(max_length=100)
    slug            = models.SlugField(unique=True)
    parent          = TreeForeignKey('self', ...)   # jerarquía MPTT (3 niveles)
    odoo_category_id = models.IntegerField(
        null=True, blank=True, unique=True,
        help_text="ID de product.category en Odoo"
    )
```

- `odoo_category_id` tiene constraint `unique=True` en DB.
- Es `null=True` para categorías creadas manualmente en Django sin contraparte en Odoo.
- Migración aplicada: `0002_category_odoo_id.py`.

---

## Modelo Odoo: `product.category`

Modelo nativo de Odoo. Campos relevantes que se leen durante la sync:

| Campo Odoo         | Uso en Django                         |
|--------------------|---------------------------------------|
| `id`               | → se guarda en `odoo_category_id`     |
| `name`             | → `Category.name`                     |
| `parent_id`        | → `Category.parent` (2ª pasada sync)  |
| `complete_name`    | ruta completa, ej: "All / Frenos"     |

---

## Flujo de sincronización (2 pasos)

La sync usa **dos pasadas** para resolver la jerarquía sin problemas de FK forward:

```
OdooConnector.get_categories()
        │
        │  product.category search_read
        │  fields: [id, name, parent_id, complete_name]
        ▼
PASO 1 — Crear/actualizar todos los nodos (sin parent todavía):
    for oc in odoo_categories:
        Category.objects.update_or_create(
            odoo_category_id = oc['id'],        ← ancla
            defaults = { 'name': oc['name'], 'is_active': True }
        )
        odoo_categ_map[oc['id']] = cat

PASO 2 — Asignar parents (jerarquía 3 niveles):
    for oc in odoo_categories where oc['parent_id']:
        parent_cat = odoo_categ_map[ oc['parent_id'][0] ]
        child_cat  = odoo_categ_map[ oc['id'] ]
        if child_cat.parent != parent_cat:
            child_cat.parent = parent_cat
            child_cat.save(update_fields=['parent'])
```

Cuando se sincroniza un producto, Odoo devuelve `categ_id = (5, "Frenos")`. Se resuelve:

```python
category = odoo_categ_map.get(categ_raw[0])   # categ_raw[0] == 5
product.category = category
```

---

## Flujo de carga inicial (entornos dev/staging)

```
1. Instalar módulo ecomparts_integration en Odoo
   → categories_seed.xml se carga automáticamente
   → crea las 12 categorías principales, ~30 subcategorías y ~60 hojas en product.category

2. Cargar jerarquía en Django:
   python manage.py seed_categories

3. (opcional) Cargar productos de prueba:
   python manage.py seed_products
   # Nota: seed_products ya no crea categorías; requiere que seed_categories haya corrido antes.

4. Ejecutar sync completa:
   python manage.py sync_products
   → odoo_category_id se rellena por primera vez en cada categoría Django
   → parent MPTT se establece para los 3 niveles
   → próximas syncs son inmediatas (lookup directo por odoo_category_id)
```

---

## Archivos involucrados

| Archivo | Rol |
|---------|-----|
| `apps/products/models.py` | Define `Category.odoo_category_id` + MPTT parent |
| `apps/products/migrations/0002_category_odoo_id.py` | Agrega el campo a la DB |
| `apps/products/management/commands/seed_categories.py` | **Carga inicial** de la jerarquía en Django (idempotente) |
| `apps/products/management/commands/seed_products.py` | Datos de prueba — referencia categorías por nombre, no las crea |
| `apps/sync/odoo_connector.py` → `get_categories()` | Lee `product.category` de Odoo (incluye `parent_id`) |
| `apps/sync/tasks.py` → `sync_provider_products()` paso 1 | Sync con jerarquía — 2 pasadas (crear nodos, luego parents) |
| `apps/products/management/commands/sync_products.py` → `_sync_categories()` | CLI con misma lógica de 2 pasadas |
| `services/odoo/addons/ecomparts_integration/data/categories_seed.xml` | Fixture Odoo — se carga al instalar el módulo (`noupdate="1"`) |
| `services/odoo/addons/ecomparts_integration/__manifest__.py` | Carga `categories_seed.xml` antes de `vehicle_variants_seed.xml` |

---

## Cómo ejecutar

### 1. Carga inicial completa

```bash
# Instalar módulo en Odoo desde la UI — categories_seed.xml se carga solo

# Django: crear jerarquía de categorías
docker exec -it ecomparts-backend python manage.py seed_categories

# Django: (opcional) productos de prueba
docker exec -it ecomparts-backend python manage.py seed_products

# Sync → rellena odoo_category_id + wirings de parent en MPTT
docker exec -it ecomparts-backend python manage.py sync_products
```

### 2. Dry-run (ver qué crearía sin guardar)

```bash
docker exec -it ecomparts-backend python manage.py seed_categories --dry-run
```

### 3. Reset en dev (borra y recrea)

```bash
# ⚠ SOLO EN DEV
docker exec -it ecomparts-backend python manage.py seed_categories --reset
```

### 4. Sync automatizada (Celery Beat, cada hora)

```
sync_all_active_providers → sync_provider_products → paso 1: categorías (2 pasadas)
```

### 5. Desde el shell de Django

```python
from apps.sync.odoo_connector import OdooConnector

odoo = OdooConnector()
cats = odoo.get_categories()
print(cats)
# [
#   {'id': 5, 'name': 'Sistema de Frenos',
#    'parent_id': [1, 'All'], 'complete_name': 'All / Sistema de Frenos'},
#   {'id': 8, 'name': 'Pastillas de Freno',
#    'parent_id': [6, '...'], 'complete_name': 'All / Sistema de Frenos / Fricción / Pastillas de Freno'},
#   ...
# ]
```

---

## Eficiencia de queries

| Paso | Queries a Odoo |
|------|---------------|
| Obtener todas las categorías | 1 (sin filtro de company) |
| Total queries a Odoo | **1** |

En Django: la primera sync hace ≤2 queries por categoría (SELECT + INSERT/UPDATE). La segunda pasada de parents hace 1 UPDATE por nodo con parent nuevo. Total: **O(n)** siendo `n` el número de categorías (~100 nodos incluyendo "All" y ramas Odoo nativas).

---

## Consideraciones importantes

- La sync **no borra** categorías de Django que ya no estén en Odoo. Si eliminás una en Odoo quedará en Django hasta limpieza manual.
- `odoo_category_id` empieza en `NULL` tras `seed_categories`. La primera sync lo rellena. A partir de ahí las syncs futuras son inmediatas (lookup por `odoo_category_id`, no por nombre).
- Con `noupdate="1"` en el XML, reinstalar el módulo Odoo **no sobreescribe** renombres manuales. Para forzar actualización, borrar el registro en `ir.model.data` con el external ID correspondiente (`ecomparts_integration.categ_frenos`, etc.).
- Si añadís una nueva categoría: actualizar **ambos** `categories_seed.xml` y `CATEGORY_TREE` en `seed_categories.py`. En Odoo reinstalar o cargar el registro a mano. En Django re-ejecutar `seed_categories`.
- `seed_products.py` referencia categorías por nombre exacto (ej: `"Pastillas de Freno"`). Si renombrás una categoría, actualizá también `CATEGORY_ALIASES` en ese archivo.

---

## Mejoras pendientes

### [MEJORA] Eliminar el bridge por nombre en la primera sync

**Estado:** Pendiente  
**Prioridad:** Media — no afecta el flujo normal de producción una vez poblado `odoo_category_id`, pero es frágil si se añaden categorías nuevas.

**Contexto:**

Después de ejecutar `seed_categories` las categorías Django tienen `odoo_category_id=NULL`. Para que la primera sync las vincule correctamente sin re-crearlas (y sin colisionar el constraint de slug único), se introdujo un **bridge de emergencia**: si no encuentra por `odoo_category_id`, busca por `name` exacto donde `odoo_category_id IS NULL`.

El orden de prioridad real en el código es:

```
1. GET por odoo_category_id   ← único ancla estable (syncs normales)
2. GET por name (bridge)      ← solo primera sync / entornos sin seed_categories
3. CREATE                     ← categoría genuinamente nueva en Odoo
```

**Problema del bridge:**

- Es sensible a diferencias de nombre entre Odoo y Django (mayúsculas, tildes, espacios).
- Un renombrado en cualquiera de los dos lados produce una categoría duplicada silenciosa.
- Hace el flujo menos predecible para alguien que llega al código por primera vez.

**Solución correcta (para producción):**

En lugar de depender del bridge, el flujo debería ser:

1. Crear la categoría en Odoo (desde la UI o vía XML seed).
2. Obtener el ID real asignado por Odoo — visible en la URL del formulario (`/web#id=XX&model=product.category`) o via shell:
   ```python
   odoo.execute('product.category', 'search_read',
       [[['name', '=', 'Pastillas de Freno']]],
       {'fields': ['id', 'name', 'complete_name']}
   )
   ```
3. Setear ese ID en Django antes de correr la sync:
   ```python
   # Desde el admin de Django o el shell
   Category.objects.filter(name='Pastillas de Freno').update(odoo_category_id=XX)
   ```

Con ese `odoo_category_id` pre-cargado, la sync usa directamente la estrategia 1 y el bridge nunca se activa.

A largo plazo, `seed_categories` podría aceptar un argumento `--fill-odoo-ids` que consulte Odoo por nombre y rellene los IDs automáticamente como paso final del seeding, eliminando la necesidad del bridge por completo.

**Impacto de no resolverlo hoy:**

En el estado actual (`odoo_category_id` ya poblado en las 104 categorías), el bridge **nunca se activa** en syncs normales. Solo se activaría si se añade una categoría nueva en Odoo y se corre `seed_categories` antes de la sync. En ese escenario la coincidencia por nombre puede fallar silenciosamente si los nombres difieren entre sistemas.

**Archivos a modificar cuando se implemente:**

| Archivo | Cambio |
|---------|--------|
| `apps/products/management/commands/seed_categories.py` | Añadir opción `--fill-odoo-ids` que rellena `odoo_category_id` consultando Odoo por nombre como paso post-seed |
| `apps/sync/tasks.py` | Eliminar bloque bridge (`except Category.DoesNotExist` por nombre) una vez que el seeding garantice IDs pre-cargados |
| `apps/products/management/commands/sync_products.py` | Idem |
