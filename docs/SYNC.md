# App `sync` — Documentación Técnica

## Índice

1. [Propósito y responsabilidades](#1-propósito-y-responsabilidades)
2. [Estructura de módulos](#2-estructura-de-módulos)
3. [Capa de transporte: `connector/`](#3-capa-de-transporte-connector)
   - [OdooBaseConnector](#31-odoobaseconnector)
   - [Mixins especializados](#32-mixins-especializados)
   - [OdooConnector (clase final)](#33-odooconnector-clase-final)
   - [Factory `get_odoo_connector_for_provider`](#34-factory-get_odoo_connector_for_provider)
4. [Capa de servicios: `services/`](#4-capa-de-servicios-services)
   - [provisioning.py](#41-provisioningpy)
   - [categories.py](#42-categoriespy)
   - [products.py](#43-productspy)
   - [compatibility.py](#44-compatibilitypy)
   - [orders.py](#45-orderspy)
5. [Tareas Celery: `tasks.py`](#5-tareas-celery-taskspy)
6. [Management Commands](#6-management-commands)
7. [Flujos principales](#7-flujos-principales)
   - [Alta de Provider (onboarding)](#71-alta-de-provider-onboarding)
   - [Sincronización completa de productos](#72-sincronización-completa-de-productos)
   - [Sincronización rápida de stock](#73-sincronización-rápida-de-stock)
   - [Ciclo de vida de una SubOrder](#74-ciclo-de-vida-de-una-suborder)
8. [Relación con otras apps](#8-relación-con-otras-apps)
9. [Compatibilidad de imports: `odoo_connector.py`](#9-compatibilidad-de-imports-odoo_connectorpy)
10. [Decisiones de diseño](#10-decisiones-de-diseño)
11. [Guía de referencia rápida](#11-guía-de-referencia-rápida)

---

## 1. Propósito y responsabilidades

La app `sync` es el **puente bidireccional** entre el marketplace Django y Odoo. Concentra toda la lógica de integración en un solo lugar siguiendo el principio de separación de capas:

| Dirección | Qué sincroniza |
|---|---|
| Odoo → Django | Categorías, productos, stock, compatibilidades producto↔vehículo |
| Django → Odoo | Jerarquía vehicular, órdenes de venta (sale.order), estados de pago y entrega |
| Bootstrap | Creación de Company + User en Odoo al registrar un nuevo Provider |

**Lo que `sync` NO hace:**
- No contiene modelos propios (no tiene `models.py`).
- No expone endpoints HTTP (no tiene `urls.py`).
- No aplica lógica de negocio de dominio (precios, descuentos, carrito) — esa lógica permanece en sus apps respectivas.

---

## 2. Estructura de módulos

```
apps/sync/
├── __init__.py
├── odoo_connector.py          ← shim de compatibilidad (re-exporta connector/)
├── tasks.py                   ← tareas Celery (capas delgadas sobre services/)
├── connector/                 ← transporte HTTP JSON-RPC hacia Odoo
│   ├── __init__.py            ← ensambla OdooConnector + factory
│   ├── base.py                ← _call(), autenticación, execute_kw(), ping()
│   ├── companies.py           ← res.company
│   ├── users.py               ← res.users
│   ├── products.py            ← product.*, stock.warehouse, stock.quant
│   ├── vehicles.py            ← vehiculo.* (push Django→Odoo)
│   └── compatibility.py       ← autopart.compatibility, vehiculo.variante (solo lectura)
├── services/                  ← lógica de negocio de la integración
│   ├── __init__.py
│   ├── provisioning.py        ← alta de nuevos providers en Odoo
│   ├── categories.py          ← sync categorías Odoo→Django
│   ├── products.py            ← sync productos+stock Odoo→Django
│   ├── compatibility.py       ← sync compatibilidades Odoo→Django
│   └── orders.py              ← sync órdenes Django→Odoo
└── management/
    └── commands/
        ├── setup_odoo.py          ← configura módulos, permisos y reglas al arrancar
        ├── sync_products.py       ← CLI para sync completa de productos
        ├── sync_stock.py          ← CLI para sync rápida de stock 
        └── sync_delivery_status.py← CLI para reconciliar estados de entrega
```

---

## 3. Capa de transporte: `connector/`

El conector implementa una arquitectura de **mixin por dominio** sobre una base de transporte HTTP. Ningún mixin importa modelos Django, son I/O puro contra Odoo.

### 3.1 `OdooBaseConnector`

Ubicado en `connector/base.py`, es la única clase con estado. Gestiona:

- **Ciclo de autenticación**: la primera llamada a `self.uid` dispara `_authenticate()`, que guarda el UID y las cookies de sesión en `self._session` (una instancia `requests.Session`). El UID **no** se cachea en Redis porque está acoplado a las cookies HTTP de la sesión.
- **`execute_kw(model, method, args, kwargs)`**: ejecuta cualquier método ORM de Odoo vía `/web/dataset/call_kw`. Siempre inyecta `{'tz': 'America/Lima'}` en el contexto. Si Odoo retorna `Session Expired`, reautentica una vez y reintenta automáticamente.
- **`ping()`**: health-check liviano que retorna `True/False`.

```
Credenciales → _authenticate() → self._uid + self._session (cookies)
                                          ↓
                              execute_kw (todas las operaciones ORM)
```

### 3.2 Mixins especializados

| Mixin | Archivo | Modelos Odoo |
|---|---|---|
| `OdooCompaniesMixin` | `companies.py` | `res.company` |
| `OdooUsersMixin` | `users.py` | `res.users` |
| `OdooProductsMixin` | `products.py` | `product.product`, `product.template`, `product.category`, `stock.warehouse`, `stock.quant` |
| `OdooVehiclesMixin` | `vehicles.py` | `vehiculo.marca`, `vehiculo.modelo`, `vehiculo.motor`, `vehiculo.transmision`, `vehiculo.traccion`, `vehiculo.variante` |
| `OdooCompatibilityMixin` | `compatibility.py` | `autopart.compatibility`, `vehiculo.variante` (solo lectura) |

**`OdooProductsMixin` — método destacado: `get_stock_quants_for_warehouse`**

Evita el problema N+1 en catalógos grandes usando `read_group` para agregar `stock.quant` por producto en una sola query, y luego un segundo query para mapear `product.product → product.template`.

**`OdooVehiclesMixin` — patrón de 3 vías (idempotente)**

Todos los métodos `push_*` del mixin vehicular son idempotentes:
1. Buscar por `django_external_id` → ya vinculado, retornar `odoo_id`.
2. Buscar por clave natural (nombre, etc.) → existe sin vincular, vincular y retornar.
3. Crear en Odoo → nuevo registro.

Esto permite ejecutar el push múltiples veces sin duplicar datos.

### 3.3 `OdooConnector` (clase final)

Compone todos los mixins mediante herencia múltiple:

```python
class OdooConnector(
    OdooCompaniesMixin,
    OdooUsersMixin,
    OdooProductsMixin,
    OdooVehiclesMixin,
    OdooCompatibilityMixin,
    OdooBaseConnector,   # ← siempre al final (MRO)
):
    ...
```

El orden de herencia garantiza que `OdooBaseConnector` (con `__init__` y `execute_kw`) se resuelva al final del MRO, permitiendo a cada mixin llamar `self.execute_kw()` sin imports circulares.

También se expone un singleton de conveniencia para uso rápido con las credenciales por defecto del `settings`:

```python
odoo_connector = OdooConnector()   # credentials from settings.ODOO_CONFIG
```

### 3.4 Factory `get_odoo_connector_for_provider`

```python
from apps.sync.connector import get_odoo_connector_for_provider

odoo = get_odoo_connector_for_provider(provider)
```

Retorna un `OdooConnector` apuntando a la URL y DB del `Provider` indicado. Las credenciales siempre son las del admin del `settings` (la desencriptación de credenciales propias del provider está pendiente de implementación).

---

## 4. Capa de servicios: `services/`

Toda la lógica de negocio de la integración vive aquí. Los servicios **sí importan modelos Django** y coordinan las llamadas al conector con persistencia en la base de datos.

### 4.1 `provisioning.py`

**Función principal: `create_provider_with_odoo_setup(user_id, provider_data, odoo_password)`**

Flujo de onboarding de un nuevo proveedor (dentro de una transacción atómica):

```
1. Verificar usuario Django existe
2. Crear (o recuperar) Provider en Django
3. Crear Company en Odoo  (res.company)  — admin connector
4. Derivar username único para Odoo
5. Crear User en Odoo vinculado a la Company
6. Guardar odoo_company_id, odoo_user_id, odoo_username en Provider
```

Si cualquiera de los pasos 3-6 falla, la transacción Django se revierte y el Provider queda marcado como inactivo.

**Función secundaria: `verify_provider_odoo_connection(provider_id)`**

Health-check que verifica que la Company y el User del provider aún existen en Odoo. Retorna `{success: bool, ...}`.

### 4.2 `categories.py`

**Funciones: `push_categories(odoo, stats) → dict` y `get_persisted_category_map() → dict`**

Empuja el catálogo global `Category` desde Django hacia `product.category` en Odoo.

La vinculación estable usa:

| Campo | Rol |
|---|---|
| `Category.sync_key` | Ancla principal y estable en Django |
| `product.category.django_sync_key` | Reflejo de esa ancla en Odoo |
| `Category.odoo_category_id` | Cache local del ID nativo actual de Odoo; no es la fuente de verdad |

`push_categories()` recorre el árbol MPTT en orden padre → hijo y, para cada nodo, intenta:
- buscar por `django_sync_key`
- luego por `odoo_category_id`
- luego por clave natural controlada (`name + parent_id`)
- y si no existe, crea la categoría en Odoo

`get_persisted_category_map()` retorna el mapa `{odoo_category_id: Category}` ya persistido localmente. Ese mapa se usa por eficiencia en las syncs de producto, pero el vínculo estable entre sistemas sigue siendo `sync_key`.

La categoría raíz `All` de Odoo sigue siendo el parent de las categorías top-level.

### 4.3 `products.py`

**Función principal: `sync_provider_products(provider_id) → dict`**

Sincronización completa para un provider (ejecuta los 3 pasos en secuencia):

```
0. Categorías globales ya empujadas por `push_categories()`
1. Productos     → get_products(company_id) + update_or_create() + Cloudinary
2. Stock         → total_stock_cached actualizado junto con el paso 1
3. Compatibilidades → sync_provider_compatibility()
```

Cada producto se mapea contra `Product` en Django usando `(provider, odoo_product_id)` como clave de idempotencia. La categoría se resuelve únicamente con el mapa persistido en Django por `odoo_category_id`. Si falta alguna categoría global vinculada, la sync falla rápido. Al finalizar, actualiza `Provider.total_products`.

**Subida de imágenes a Cloudinary (`_upload_image`)**

Si el producto trae `image_1920` (base64) desde Odoo, se sube a Cloudinary con transformación automática (800×800, quality auto, format auto). Falla silenciosamente si Cloudinary no está disponible.

**Anti-duplicación de referencias (`_resolve_reference`)**

Si la `default_code` de Odoo ya existe en otro producto del mismo provider en Django, usa el fallback `ODOO-{odoo_product_id}` para evitar colisiones en la columna `UNIQUE(provider, reference)`.

**Función secundaria: `sync_provider_stock(provider_id) → dict`**

Sincronización ligera: solo actualiza `total_stock_cached` consultando `qty_available` en Odoo. No toca categorías, imágenes ni compatibilidades. Se usa para ciclos frecuentes (cada 15 min en producción).

### 4.4 `compatibility.py`

**Función: `sync_provider_compatibility(provider_id) → dict`**

Sincroniza `autopart.compatibility` de Odoo hacia `CompatibilidadProducto` de Django.

Flujo optimizado (minimiza queries N+1):
1. Obtener todos los `Product` del provider con `odoo_template_id` en **una query**.
2. Consultar `autopart.compatibility` en Odoo en **lote** con todos los template IDs.
3. Prefetch `vehiculo.variante` en Odoo en **una sola query** con todos los IDs únicos.
4. Para cada registro: resolver `Product` y `VariantVehiculo`, luego `update_or_create` en `CompatibilidadProducto`.

**Resolución de `VariantVehiculo` (`_resolve_django_variant`) — 3 estrategias:**

| Estrategia | Condición | Mecanismo |
|---|---|---|
| 1 | `VariantVehiculo.odoo_variante_id` ya está guardado | Lookup directo por PK externo |
| 2 | Odoo tiene `django_external_id` en `vehiculo.variante` | Lookup por PK de Django |
| 3 | Sin match | Retorna `None` + log de aviso (resolver ejecutando `push_vehicles`) |

### 4.5 `orders.py`

Sincroniza el ciclo de vida de las órdenes entre Django y Odoo.

**Funciones principales:**

| Función | Dirección | Cuándo |
|---|---|---|
| `sync_suborder_to_odoo(suborder)` | Django → Odoo | Al confirmar pago de una SubOrder |
| `update_odoo_payment_status(suborder)` | Django → Odoo | Al cambiar `SubOrder.status` |
| `update_odoo_delivery_status(suborder)` | Django → Odoo | Al marcar como enviado/entregado |

**Mapas de estado:**

```python
# SubOrder.status → x_payment_status en Odoo
_PAYMENT_STATUS_MAP = {
    'pago_en_revision': 'pendiente_revision',
    'pago_rechazado':   'rechazado',
    'confirmado':       'aprobado',
    'enviado':          'aprobado',
    'entregado':        'aprobado',
    'cancelado':        False,   # limpia el campo
}

# SubOrder.status → x_delivery_status en Odoo
_DELIVERY_STATUS_MAP = {
    'pendiente_pago':   'pendiente',
    'confirmado':       'pendiente',
    'enviado':          'enviado',
    'entregado':        'recibido',
    'cancelado':        'cancelado',
}
```

**`sync_suborder_to_odoo` — Flujo detallado:**

1. Si `suborder.odoo_sale_id` ya existe → retorna el ID sin duplicar (idempotente).
2. Busca o crea `res.partner` en Odoo por email o DNI/RUC del customer.
3. Construye `order_lines` a partir de los `OrderItem` (omite productos sin `odoo_product_id`).
4. Antes de crear, verifica en Odoo si ya existe una `sale.order` con `x_marketplace_suborder_id` igual (segunda capa de idempotencia).
5. Crea la `sale.order` con todos los campos del módulo `orders_odoo` (estados, método de pago, dirección de entrega, etc.).

---

## 5. Tareas Celery: `tasks.py`

Las tareas son **capas delgadas** que delegan completamente a los servicios. Su única responsabilidad es deserializar argumentos y enrutar al servicio correcto.

| Tarea | Servicio delegado | Frecuencia sugerida |
|---|---|---|
| `create_provider_with_odoo_setup` | `provisioning.create_provider_with_odoo_setup` | On-demand (onboarding) |
| `sync_provider_products` | `products.sync_provider_products` | On-demand / diario |
| `sync_all_active_providers` | `sync_provider_products` (por cada provider) | Diario |
| `sync_provider_stock` | `products.sync_provider_stock` | Cada 15 min |
| `sync_all_stock` | `sync_provider_stock` (por cada provider) | Cada 15 min |
| `sync_provider_compatibility` | `compatibility.sync_provider_compatibility` | On-demand |
| `check_providers_for_upgrade` | Lógica inline (verifica tier) | Diario |
| `verify_provider_odoo_connection` | `provisioning.verify_provider_odoo_connection` | On-demand / semanal |
| `create_order_in_odoo` | — (TODO) | — |

> **Nota:** `sync_all_stock` solo procesa providers con `odoo_company_id` no nulo, ya que sin ese dato no hay contexto de empresa en Odoo.

---

## 6. Management Commands

### `setup_odoo`
```bash
python manage.py setup_odoo [--force] [--skip-modules]
```
Configura Odoo al arrancar el backend. Idempotente.
- Instala módulos `orders_odoo` y `multi_company_products`.
- Aplica 6 reglas de aislamiento multi-company (`ir.rule`).
- Configura grupos de permisos para todos los providers existentes.
- Espera a que Odoo esté disponible (hasta 10 reintentos con delay de 5s).

### `sync_products`
```bash
python manage.py sync_products [--provider-id=N] [--dry-run] [--limit=N] [--skip-compat]
```
Sincronización completa: categorías → productos → stock → compatibilidades.

Precondición: el catálogo global debe haber sido normalizado antes con `push_categories`.

| Modo | Comportamiento |
|---|---|
| Sin flags | Todos los providers activos y aprobados con `odoo_company_id` |
| `--provider-id=N` | Solo el provider especificado |
| `--dry-run` | Conecta a Odoo, reporta qué haría, **no guarda nada** |
| `--skip-compat` | Omite la sincronización de compatibilidades |

### `sync_stock`
```bash
python manage.py sync_stock [--provider-id=N] [--dry-run]
```
Sincronización rápida: solo actualiza `total_stock_cached`. No toca metadatos ni compatibilidades.

### `sync_delivery_status`
```bash
python manage.py sync_delivery_status [--suborder=ORD-YYYY-NNNNN-X] [--dry-run]
```
Reconciliación de estados de entrega. Útil cuando el webhook de Odoo no llegó a Django (p.ej. por caídas temporales). Compara el estado de `stock.picking` en Odoo con `SubOrder.status` en Django y corrige las discrepancias.

---

## 7. Flujos principales

### 7.1 Alta de Provider (onboarding)

```
[Vista/API marketplace] → tasks.create_provider_with_odoo_setup.delay(user_id, data, pwd)
                                      ↓  (Celery worker)
                          services/provisioning.create_provider_with_odoo_setup()
                                      ↓
                          ┌── 1. Crear Provider (Django DB) ──────────────────┐
                          ├── 2. connector.create_company() → res.company     │
                          ├── 3. connector.create_user_for_company()          │ atómico
                          └── 4. Provider.odoo_company_id / odoo_user_id ←───┘
                                      ↓
                          Provider listo para sincronizar productos
```

### 7.2 Sincronización completa de productos

```
[Celery Beat / CLI] → tasks.sync_provider_products.delay(provider_id)
                                ↓
                    services/products.sync_provider_products()
                                ↓
              ┌─ 0. push_categories()            → Category (Django) → product.category (Odoo)
              ├─ 1. connector.get_products()     → product.product  → Product  (Django)
              │      └─ _upload_image()          → Cloudinary
              │      └─ _resolve_reference()     → anti-duplicados
              ├─ 2. total_stock_cached           → actualizado en paso 1
              └─ 3. sync_provider_compatibility()→ autopart.compatibility → CompatibilidadProducto
```

### 7.3 Sincronización rápida de stock

```
[Celery Beat cada 15 min] → tasks.sync_all_stock()
                                   ↓ (por cada provider activo con odoo_company_id)
                       tasks.sync_provider_stock.delay(provider_id)
                                   ↓
                   services/products.sync_provider_stock()
                                   ↓
               connector.get_products(company_id)
                                   ↓
               Product.update(total_stock_cached=qty_available)
```

### 7.4 Ciclo de vida de una SubOrder

```
Cliente confirma pago
        ↓
[orders app] → tasks.sync_suborder_to_odoo (via signals o views)
        ↓
services/orders.sync_suborder_to_odoo(suborder)
        ├─ _get_or_create_partner()    → res.partner
        ├─ order_lines ← OrderItem.odoo_product_id
        └─ execute_kw('sale.order', 'create') → suborder.odoo_sale_id

Provider actualiza despacho en Odoo
        ↓
[Webhook Odoo → Django] o [sync_delivery_status command]
        ↓
SubOrder.status = 'enviado' / 'entregado'
        ↓
services/orders.update_odoo_delivery_status(suborder)
        └─ sale.order.write(x_delivery_status = 'enviado'/'recibido')
```

---

## 8. Relación con otras apps

```
┌─────────────────────────────────────────────────────────────────┐
│                         apps/sync                               │
│  connector/  ◄──── JSON-RPC ────►  ODOO                         │
│  services/   ↕ importa modelos   ↕                              │
└───────┬──────────────┬──────────────┬──────────────┬────────────┘
        │              │              │              │
   marketplace/    products/       orders/        vehicles/
   ─────────────   ──────────      ────────       ─────────
   Provider        Product         SubOrder       VariantVehiculo
   (odoo_company_id (odoo_product_id (odoo_sale_id  (odoo_variante_id
   odoo_user_id     odoo_template_id  status)        django_external_id
   odoo_username    total_stock_cached)               en Odoo)
   tier, is_approved Category
   is_active)       CompatibilidadProducto
```

### Detalle por app

| App | Qué usa `sync` | Qué provee a `sync` |
|---|---|---|
| **marketplace** | `Provider.get_odoo_connection_info()`, `generate_odoo_username()`, `set_odoo_password()` | Contexto multi-company para el conector |
| **products** | `Product`, `Category`, `CompatibilidadProducto` para persistir resultados de sync | Modelos destino de la sincronización |
| **orders** | `SubOrder`, `OrderItem`, `PaymentProof` para construir `sale.order` en Odoo | Origen de los datos que van hacia Odoo |
| **vehicles** | `VariantVehiculo` para resolver compatibilidades; `push_*` del conector para enviar la jerarquía | Catálogo vehicular que se indexa en Odoo |
| **customer** | `Customer` (vía `order.customer`) para crear `res.partner` en Odoo | Datos del comprador |

---

## 9. Compatibilidad de imports: `odoo_connector.py`

El módulo `apps/sync/odoo_connector.py` es un **shim de compatibilidad** que re-exporta todo desde `apps/sync/connector/`. Garantiza que todos los imports previos al refactor sigan funcionando:

```python
# Ambas formas funcionan:
from apps.sync.odoo_connector import OdooConnector                   # legado
from apps.sync.connector import OdooConnector                        # nuevo (preferido)
```

---

## 10. Decisiones de diseño

### UID de Odoo no se cachea en Redis
El UID de autenticación está acoplado a las cookies HTTP de `requests.Session`. Reutilizar un UID de otra instancia produciría errores de `Session Expired`. La autenticación tarda ~50 ms y ocurre una vez por instancia de `OdooConnector`, lo cual es suficiente para el ciclo de vida de una tarea Celery.

### Tasks como capas delgadas
Cada tarea Celery solo deserializa argumentos y llama al servicio. Esto permite testear la lógica de negocio sin un broker Celery, y reusar los mismos servicios desde management commands y desde otros puntos del código.

### Estrategia de 3 vías para categorías y vehículos
Permite arrancar el sistema en cualquier orden: seeds de Django pueden existir antes de que Odoo esté configurado, y la primera sync los vincula sin duplicar.

### Resolución de `VariantVehiculo` en 3 estrategias
La estrategia 2 (`django_external_id` en Odoo) es el puente que conecta la dirección Django→Odoo (push de vehículos) con la dirección Odoo→Django (pull de compatibilidades). Requiere haber ejecutado el comando `push_vehicles` o su equivalente Celery al menos una vez.

### Contexto multi-company explícito en `orders.py`
Todas las operaciones sobre modelos de Odoo que son sensibles al contexto de compañía (`sale.order`, `account.move`, etc.) incluyen `company_id`, `force_company` y `allowed_company_ids` en el contexto para garantizar el aislamiento correcto en la instancia Odoo compartida.

---

## 11. Guía de referencia rápida

### ¿Qué archivo modificar para…?

| Necesidad | Archivo |
|---|---|
| Agregar un nuevo campo sincronizado desde Odoo a `Product` | `services/products.py` → `sync_provider_products()` |
| Agregar soporte para un nuevo modelo de Odoo (ej: `res.currency`) | `connector/` → nuevo mixin + agregar a `OdooConnector` |
| Cambiar el mapeo de estado de pago | `services/orders.py` → `_PAYMENT_STATUS_MAP` |
| Agregar una nueva tarea periódica | `tasks.py` + `ecomparts/settings.py` → `CELERY_BEAT_SCHEDULE` |
| Diagnosticar por qué un producto no se sincroniza | `sync_products --provider-id=N --dry-run` |
| Diagnosticar desincronización de stock | `sync_stock --provider-id=N --dry-run` |
| Reparar estados de entrega perdidos por webhook fallido | `sync_delivery_status --dry-run` |
| Verificar la conexión Odoo de un provider | `tasks.verify_provider_odoo_connection.delay(provider_id)` |

### Variables de entorno relevantes (`settings.ODOO_CONFIG`)

| Variable | Default | Descripción |
|---|---|---|
| `ODOO_URL` | `http://odoo:8069` | URL de la instancia Odoo |
| `ODOO_DB` | `ecomparts_odoo_shared` | Nombre de la base de datos Odoo |
| `ODOO_USERNAME` | `admin` | Usuario admin del conector |
| `ODOO_PASSWORD` | `admin` | Password admin del conector |
