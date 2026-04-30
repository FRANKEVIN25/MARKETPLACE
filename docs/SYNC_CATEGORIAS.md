# Sincronización de Categorías: Django → Odoo

## Problema que resuelve

Odoo usa `product.category` con IDs auto-incrementales propios. Django usa `products.Category` con sus propios IDs auto-incrementales. Si cualquiera de las dos bases se reprovisiona, esos IDs dejan de coincidir.

**La solución incorrecta** sigue siendo asumir que `odoo.category.id == django.category.id` o depender del nombre exacto para vincular categorías.

**La solución implementada ahora** es:

- Django es el maestro del catálogo global.
- Cada `Category` tiene un `sync_key` UUID inmutable.
- Odoo guarda ese mismo valor en `product.category.django_sync_key`.
- `odoo_category_id` se mantiene en Django como puntero al ID real actual de Odoo, útil para resolver `categ_id` en productos.

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

## Fuente de verdad

La fuente de verdad operativa del catálogo es Django:

| Sistema | Rol | Archivo / Modelo |
|---------|-----|------------------|
| Django  | Fuente de verdad | `services/backend/apps/products/management/commands/seed_categories.py` → `products.Category` |
| Odoo    | Proyección operativa para proveedores | `product.category` + `django_sync_key` |
| Odoo XML | Solo bootstrap / legado | `services/odoo/addons/ecomp/data/categories_seed.xml` |

> **Regla actual:** las altas, renombres y movimientos se hacen en Django y luego se propagan a Odoo con `push_categories`.

---

## Modelo Django: `Category`

```python
# apps/products/models.py
class Category(MPTTModel):
    name            = models.CharField(max_length=100)
    slug            = models.SlugField(unique=True)
    parent          = TreeForeignKey('self', ...)   # jerarquía MPTT (3 niveles)
    sync_key        = models.UUIDField(unique=True, editable=False)
    odoo_category_id = models.IntegerField(
        null=True, blank=True, unique=True,
        help_text="ID de product.category en Odoo"
    )
```

- `sync_key` es la ancla estable principal entre sistemas.
- `odoo_category_id` tiene constraint `unique=True` en DB y se usa como cache del ID nativo de Odoo.
- `odoo_category_id` puede empezar en `NULL` hasta ejecutar `push_categories`.

---

## Modelo Odoo: `product.category`

Modelo nativo de Odoo, extendido por `ecomp`. Campos relevantes:

| Campo Odoo         | Uso en Django                         |
|--------------------|---------------------------------------|
| `id`               | → se guarda en `odoo_category_id`     |
| `django_sync_key`  | → coincide con `Category.sync_key`    |
| `name`             | → `Category.name`                     |
| `parent_id`        | → `Category.parent` (2ª pasada sync)  |
| `complete_name`    | ruta completa, ej: "All / Frenos"     |

---

## Flujo oficial de sincronización

### 1. Seed en Django

`seed_categories` crea o reutiliza el árbol canónico en Django. Cada categoría recibe un `sync_key` estable.

### 2. Push global Django → Odoo

`push_categories` recorre el árbol MPTT en orden padre → hijo y aplica esta estrategia:

```
for category in Category.objects.order_by(level, tree_id, lft):
    push_category(
        django_sync_key = category.sync_key,
        odoo_category_id = category.odoo_category_id,   # legado / cache
        natural_key = (category.name, parent_odoo_id),
    )

Prioridad de matching:
1. django_sync_key   ← ancla principal y estable
2. odoo_category_id  ← cache local / compatibilidad legada
3. (name, parent_id) ← bootstrap controlado
4. create            ← categoría nueva en Odoo
```

Para categorías raíz, el padre objetivo en Odoo es `product.product_category_all` (`All`).

### 3. Sync de productos por proveedor

Cuando se sincroniza un producto, Odoo devuelve `categ_id = (5, "Frenos")`. La sync de productos ya no recalcula categorías; solo consume el mapa persistido en Django:

```python
category = odoo_categ_map.get(categ_raw[0])   # categ_raw[0] == 5
product.category = category
```

Si falta alguna categoría global vinculada en Django, `sync_products` falla rápido y pide ejecutar `push_categories`.

---

## Flujo de carga inicial (entornos dev/staging)

```
1. Cargar jerarquía en Django:
   python manage.py seed_categories

2. Empujar catálogo global a Odoo:
    python manage.py push_categories

3. (opcional) Cargar productos de prueba:
   python manage.py seed_products
   # Nota: seed_products ya no crea categorías; requiere que seed_categories haya corrido antes.

4. Ejecutar sync completa de productos:
    python manage.py sync_products
     → usa `odoo_category_id` ya persistido como cache local para resolver `Product.category`
```

---

## Archivos involucrados

| Archivo | Rol |
|---------|-----|
| `apps/products/models.py` | Define `Category.sync_key`, `odoo_category_id` y MPTT parent |
| `apps/products/migrations/0010_category_sync_key.py` | Agrega `sync_key` y lo rellena para categorías existentes |
| `apps/products/management/commands/seed_categories.py` | **Carga inicial** de la jerarquía en Django (idempotente) |
| `apps/sync/management/commands/push_categories.py` | Empuja/vincula el catálogo global Django → Odoo |
| `apps/sync/services/categories.py` | `push_categories()` y `get_persisted_category_map()` |
| `apps/products/management/commands/seed_products.py` | Datos de prueba — referencia categorías por nombre, no las crea |
| `apps/sync/management/commands/sync_products.py` | Sync por provider usando mapa de categorías ya persistido |
| `services/odoo/addons/ecomp/models/products.py` | Agrega `django_sync_key` a `product.category` |
| `services/odoo/addons/ecomp/data/categories_seed.xml` | Fixture legado / bootstrap |

---

## Cómo ejecutar

### 1. Carga inicial completa

```bash
# Actualizar migraciones Django si aún no corriste la nueva versión
docker exec -it ecomparts-backend python manage.py migrate

# Actualizar el módulo Odoo para agregar product.category.django_sync_key
docker exec -it ecomparts-backend python manage.py upgrade_odoo_module --module=ecomp

# Django: crear jerarquía de categorías
docker exec -it ecomparts-backend python manage.py seed_categories

# Django -> Odoo: empujar catálogo global
docker exec -it ecomparts-backend python manage.py push_categories

# Django: (opcional) productos de prueba
docker exec -it ecomparts-backend python manage.py seed_products

# Sync productos → consume el mapa global ya vinculado
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

### 4. Sync automatizada

```
push_categories (baja frecuencia, global)
sync_all_active_providers → sync_provider_products
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
| `push_categories` | O(n) pequeño sobre ~100 nodos |
| `sync_products` | 0 queries extra de categorías; consume mapa local |

En Django, `push_categories` solo persiste `odoo_category_id` cuando cambia. `sync_products` ya no recalcula jerarquía ni hace bridge por nombre en cada provider.

---

## Consideraciones importantes

- `sync_key` es la ancla estable principal. No depende del nombre ni del PK de Django.
- `odoo_category_id` empieza en `NULL` tras `seed_categories`. `push_categories` lo rellena con el ID real asignado por Odoo, pero ese campo actúa como cache local; la vinculación estable sigue dada por `sync_key`.
- `sync_products` asume que el catálogo global ya fue empujado. Si faltan categorías vinculadas, aborta con error claro.
- `categories_seed.xml` puede seguir existiendo durante la transición, pero ya no es la fuente principal para altas y cambios.
- `seed_products.py` referencia categorías por nombre exacto (ej: `"Pastillas de Freno"`). Si renombrás una categoría, actualizá también `CATEGORY_ALIASES` en ese archivo.

---

## Estado actual

En el flujo normal de producción ya no existe bridge por nombre:

- `seed_categories` crea el árbol en Django.
- `push_categories` vincula por `sync_key` y persiste `odoo_category_id` como cache operativa.
- `sync_products` solo consume ese mapa local.

Eso elimina la dependencia operativa del nombre exacto entre sistemas.
