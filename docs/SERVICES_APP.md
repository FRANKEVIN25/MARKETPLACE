# App `services` — Documentación técnica

> **Versión:** 1.2.0  
> **Fecha:** 24 de marzo de 2026  
> **Estado:** En desarrollo activo — modelos estables, vistas pendientes

---

## 1. Propósito y valor de negocio

La app `services` **no es un directorio de talleres**. Es la capa que reduce el riesgo del cliente final mediante:

- **Verificación real** de talleres (RUC, inspección, certificaciones).
- **Historial transparente** de trabajos y métricas de calidad.
- **Ecosistema cerrado**: los talleres son consumidores masivos de autopartes (B2B) y, opcionalmente, proveedores en el mismo marketplace.

### Diferenciación estratégica

| Plataforma genérica | EcomParts Services |
|---|---|
| Lista talleres sin filtrar | Solo talleres verificados |
| Sin historial de trabajos | Historial por servicio y taller |
| Sin integración de repuestos | Taller compra/vende en el mismo ecosistema |
| Sin garantía estructurada | Garantía declarada por servicio |

---

## 2. Modelos

### 2.1 `ServiceCategory`

Catálogo jerárquico de **2 niveles** (padre → hijo). No usa MPTT porque 2 niveles son suficientes para el dominio automotriz.

```
Frenos                          ← nivel 1 (parent=None)
  └─ Mantenimiento de frenos    ← nivel 2 (parent=Frenos)
Motor
  └─ Reparación de culata
```

**Campos clave:**

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | CharField | Nombre de la categoría |
| `parent` | FK('self') | Null = nivel 1. Lleno = subcategoría |
| `icon` | CharField | Identificador FontAwesome (ej: `fa-wrench`) |
| `order` | PositiveIntegerField | Orden en UI (menor = primero) |
| `is_root` | property | `True` si `parent_id` is None |

**Árbol de categorías recomendado (nivel 1):**

```
1. Mantenimiento General    (fa-oil-can)
2. Motor                    (fa-engine)
3. Frenos                   (fa-circle-stop)
4. Suspensión y Dirección   (fa-car-burst)
5. Transmisión              (fa-gears)
6. Electricidad y Electrónica (fa-bolt)
7. Diagnóstico              (fa-stethoscope)
8. Aire Acondicionado       (fa-snowflake)
9. Escape                   (fa-wind)
10. Carrocería y Pintura    (fa-spray-can)
11. Servicios Rápidos       (fa-gauge-high)
```

---

### 2.2 `Service`

**Catálogo maestro** de servicios de la plataforma. Es compartido (no pertenece a un taller).

**Campos clave:**

| Campo | Tipo | Valores | Descripción |
|---|---|---|---|
| `category` | FK → ServiceCategory | — | Categoría del servicio |
| `name` | CharField | — | Nombre del servicio |
| `service_type` | CharField | `maintenance` / `repair` / `diagnostic` | Tipo general |
| `complexity` | CharField | `low` / `medium` / `high` | Complejidad operativa |

**Por qué `service_type` y `complexity` importan:**

- **Filtros y ordenamiento** en el frontend.
- **Pricing estimado**: `complexity=high` → precio mayor.
- **Matching IA (Fase 2)**: priorizar talleres especializados en servicios complejos.

**Ejemplos de catálogo:**

```
Frenos → Cambio de pastillas        [maintenance, low]
Frenos → Rectificado de discos      [repair, medium]
Frenos → Cambio de líquido          [maintenance, low]
Motor  → Afinamiento completo       [maintenance, medium]
Motor  → Cambio de aceite           [maintenance, low]
Motor  → Reparación de culata       [repair, high]
Diag.  → Escaneo OBD2               [diagnostic, low]
Diag.  → Diagnóstico eléctrico      [diagnostic, medium]
```

---

### 2.3 `Workshop`

**Modelo central** del taller mecánico.

#### 2.3.1 `service_level` y `commerce_level` — los dos ejes del taller

En lugar de un solo campo `parts_relation`, el modelo usa dos ejes ortogonales que representan dimensiones reales del mercado peruano:

**`service_level`** — nivel de operación interna (ERP):

| Valor | Descripción |
|---|---|
| `BASIC` | Sin Odoo. Solo frontend y marketplace como Customer. |
| `MANAGED` | Odoo ERP + Repair. Control operativo interno. |
| `ADVANCED` | Odoo ERP + Repair + analítica futura (Fase 3). |

**`commerce_level`** — relación con el inventario de autopartes:

| Valor | Descripción |
|---|---|
| `NONE` | No compra ni vende (caso extremo, talleres cerrados de flota). |
| `BUYER` | Compra al precio retail del marketplace (como `Customer(company)`). |
| `B2B_BUYER` | Compra a precio mayorista vía Odoo Purchase. |
| `SELLER` | Compra B2B + vende repuestos en el marketplace. Requiere `Provider`. |

**Combinaciones habituales en el mercado peruano:**

| `service_level` | `commerce_level` | Perfil de taller |
|---|---|---|
| `BASIC` | `BUYER` | Taller pequeño / informal |
| `MANAGED` | `B2B_BUYER` | Taller profesional con ERP |
| `ADVANCED` | `SELLER` | Taller empresarial + tienda de repuestos |

> La separación en dos ejes permite reflejar combinaciones reales que el campo único no podía expresar: un taller puede tener ERP interno (`MANAGED`) sin vender en el marketplace (`B2B_BUYER`), o puede vender repuestos (`SELLER`) con un ERP avanzado (`ADVANCED`). Los ejes son independientes.

#### 2.3.2 `owner` y `customer_profile` — la doble identidad del taller

`owner` es un `ForeignKey(User)` y **no cambia**. Es el vínculo de autenticación.

`customer_profile` es un `OneToOneField(customer.Customer)` que se crea **automáticamente** al registrar el taller mediante una signal de Django:

```python
@receiver(post_save, sender=Workshop)
def create_customer_for_workshop(sender, instance, created, **kwargs):
    if created:
        customer, _ = Customer.objects.get_or_create(
            user=instance.owner,
            defaults={
                'customer_type': 'company',
                'company_name': instance.name,
                'document_type': 'RUC',
                'document_number': instance.ruc or '',
            }
        )
        Workshop.objects.filter(pk=instance.pk).update(customer_profile=customer)
```

Gracias a esto:
- **El taller con `service_level=BASIC` + `commerce_level=BUYER` puede comprar** autopartes en el marketplace desde el primer día.
- El taller reutiliza todas las interfaces de `customer`: login, registro, perfil, historial de pedidos, direcciones.
- Los campos `company_name`, `document_type=RUC` y `document_number` del Customer evitan redundancia con `Workshop.ruc` (ver sección 9).

> **Regla estricta de tipos de Customer:**  
> `Customer(type='individual')` → persona natural con vehículo propio.  
> `Customer(type='company')` → taller mecánico u empresa.  
> Un mismo usuario no puede tener ambos perfiles (restricción del `OneToOneField(User)`).

#### 2.3.3 Propiedades de negocio

```python
workshop.can_sell_parts      # True si commerce_level == 'SELLER'
workshop.can_buy_b2b         # True si commerce_level in ('B2B_BUYER', 'SELLER')
workshop.has_erp_integration # True si service_level in ('MANAGED', 'ADVANCED')
workshop.is_basic_only       # True si service_level == 'BASIC'
workshop.is_service_only     # True si tiene ERP pero commerce_level != 'SELLER'

# Acceso al perfil de comprador
workshop.customer_profile    # → customer.Customer(type='company')
workshop.customer_profile.stats.total_spent   # acumulado en marketplace
workshop.customer_profile.addresses.all()     # direcciones del taller
```

#### 2.3.4 Relación con Odoo

| Campo | Descripción |
|---|---|
| `odoo_partner_id` | ID del `res.partner` en Odoo. Customer=True + Supplier=True simultáneamente |
| `odoo_repair_id` | ID del módulo Repair. Solo para `service_level` `MANAGED` / `ADVANCED` |

> **Flujo de activación Odoo:**  
> Cuando `service_level` cambia a `MANAGED` o `ADVANCED`, se debe crear (o actualizar) el Partner en Odoo vía la API JSON-RPC del addon `ecomp`. Ver sección 5.

> **El historial Django no se toca en el upgrade:**  
> Odoo no existía mientras el taller operaba con `service_level=BASIC`, por lo que solo empieza a registrar datos desde el momento del upgrade. El `customer_profile` del taller y todo su historial de compras en Django permanecen intactos. No hay migración de datos ni pérdida de información al cambiar de nivel.

#### 2.3.5 `specialties` (M2M → ServiceCategory)

Declara en qué categorías de nivel 1 es especialista el taller.

```python
# Ejemplo
workshop.specialties.add(
    ServiceCategory.objects.get(name='Motor'),
    ServiceCategory.objects.get(name='Electricidad y Electrónica'),
)
```

Impacto:
- **Búsqueda**: los talleres especialistas aparecen primero en filtros por categoría.
- **SEO**: genera meta-tags específicos por especialidad.
- **Matching IA (Fase 2)**: peso adicional en el algoritmo de ranking.

#### 2.3.6 Capacidad operativa

| Campo | Uso actual | Uso futuro (Fase 2) |
|---|---|---|
| `bays` | Mostrar en perfil | Calcular slots disponibles |
| `employees` | Mostrar en perfil | Paralelismo de citas |
| `max_fleet_size` | Filtro B2B | Segmentación corporativa |

---

### 2.4 `WorkshopService`

**Tabla intermedia** `Workshop ↔ Service` con datos operativos específicos del taller.

**Campos clave:**

| Campo | Tipo | Descripción |
|---|---|---|
| `is_specialized` | BooleanField | Servicio diferenciador del taller |
| `min_price` | DecimalField | Precio mínimo (PEN) |
| `max_price` | DecimalField | Precio máximo (PEN) |
| `currency` | CharField | ISO 4217. Default: `PEN` |
| `estimated_time_min` | PositiveIntegerField | Minutos estimados (ej: 90 = 1h 30min) |
| `available` | BooleanField | Disponible actualmente |
| `has_warranty` | BooleanField | Ofrece garantía |
| `warranty_days` | PositiveIntegerField | Días de garantía (0 = no aplica) |

> **¿Por qué precio numérico y no texto?**  
> `"S/ 80 - 120"` como CharField mata los filtros, el ordenamiento y la analítica.  
> El texto se genera en el **frontend** a partir de `min_price`, `max_price` y `currency`.

> **¿Por qué minutos y no horas?**  
> `estimated_time_min=90` es más preciso que `estimated_time_hours=1.5` para una agenda tipo Google Calendar con slots de 15/30 minutos.

> **¿Por qué `has_warranty` importa tanto?**  
> En mercados emergentes, la garantía explícita convierte más que el rating promedio. Es evidencia de confianza estructurada.

---

### 2.5 `WorkshopServiceHistory`

Historial **agregado** por taller + tipo de servicio. No es log de eventos individuales.

**Propósito actual:** métricas de reputación visibles en el perfil.  
**Propósito futuro (Fase 2):** insumo para el motor de recomendaciones IA.

| Campo | Descripción |
|---|---|
| `total_jobs` | Trabajos completados de este tipo |
| `success_rate` | % trabajos sin incidencias |
| `repeat_failure_rate` | % con falla recurrente del mismo defecto |
| `avg_rating` | Rating promedio del cliente (0.00–5.00) |
| `last_job_date` | Fecha del último trabajo |

**Actualización:** vía `signals` de Django o tarea Celery al cerrar órdenes de servicio.

---

### 2.6 `WorkshopSchedule` *(nuevo)*

Horario semanal operativo del taller.

**Propósito actual:** mostrar el horario en el perfil del taller.  
**Propósito futuro (Fase 2):** generar slots de citas (disponibilidad real).

```
Workshop A — Lunes    08:00–13:00
Workshop A — Lunes    14:00–18:00   ← turno tarde (mismo día, 2 registros)
Workshop A — Sábado   08:00–12:00
```

| Campo | Descripción |
|---|---|
| `day_of_week` | 0 = Lunes … 6 = Domingo (ISO/Python) |
| `start_time` | Hora de apertura |
| `end_time` | Hora de cierre |
| `is_active` | Deshabilitar sin eliminar (feriados permanentes) |

---

## 3. Diagrama de relaciones

```
User ──────────────────────── Workshop ──────────────────── WorkshopSchedule
  │                               │
  │                               ├─ (M2M) ─────────────── ServiceCategory
  │                               │                              │ (parent FK)
  │                               │                         ServiceCategory (subcategorías)
  │                               │                              │
  │                               │                           Service
  │                               │                         (+ service_type, complexity)
  │                               │
  │                               ├─────────────────────── WorkshopService
  │                               │                        (min_price, max_price, currency,
  │                               │                         estimated_time_min,
  │                               │                         has_warranty, warranty_days)
  │                               │
  │                               ├─────────────────────── WorkshopServiceHistory
  │                               │
  │                               ├─ (OneToOne) ─────────── marketplace.Provider
  │                               │                          (solo commerce_level='SELLER')
  │                               │
  └──── Customer ─────────────────┘ (OneToOne via customer_profile)
    (type='company')               Signal crea el Customer al registrar el taller
         │
         ├─── Address (envío, agencia, negocio)
         ├─── CustomerStats (total_spent, total_orders)
         └─── Orders / Cart (historial de compras en marketplace)
```

---

## 4. Ciclo de vida de un taller

```
Registro (service_level=BASIC, commerce_level=BUYER)
       │
       ▼  [Signal automática]
       Signal → Customer(type='company', document_type='RUC') creado
       workshop.customer_profile = nuevo Customer
       │
       │  Desde este momento:
       ✓ Puede comprar autopartes en el marketplace (como Customer empresa)
       ✓ Acumula historial: pedidos, gasto total, direcciones
       ✗ Sin acceso B2B (precio de costo)
       ✗ Sin ERP ni módulo Repair
       │
       ▼
Verificación manual (is_verified=True)
       │
       ▼
Upgrade service_level=MANAGED  ──► Signal/task → res.partner.create en Odoo
Upgrade commerce_level=B2B_BUYER       workshop.odoo_partner_id = nuevo_id
       │                    ✓ Acceso a compras B2B de repuestos (Odoo Purchase)
       │                    ✓ Historial Django previo INTACTO (no se migra, no se borra)
       │                    ✓ Odoo empieza a registrar datos desde este momento
       │
       ▼
Upgrade service_level=ADVANCED  ──► Activar Inventory en Odoo
Upgrade commerce_level=SELLER          Signal/task → marketplace.Provider.create(...)
                                       workshop.provider = nuevo Provider
                                       ✓ Puede vender repuestos en el marketplace
                                       ✓ Todo el historial Django previo INTACTO
```

> Los dos ejes pueden cambiar de forma independiente. Un taller puede subir
> `service_level` a `MANAGED` sin cambiar `commerce_level`. O puede cambiar
> `commerce_level` a `SELLER` permaneciendo en `service_level=ADVANCED`.

---

## 5. Integración con Odoo

### 5.1 Addons relevantes

| Addon | Propósito | Relación con `services` |
|---|---|---|
| `ecomp` | Catálogo de vehículos, compatibilidades, productos | El taller con `commerce_level=SELLER` crea productos aquí. `autopart_quality`, `autopart_side`, `autopart_oem_code` son campos del addon |
| `orders_odoo` | Extiende `sale.order` con datos del marketplace | Cuando el taller vende repuestos, las órdenes pasan por aquí. Campo `payment_state` en Odoo refleja lo aprobado desde Django |
| `odoo_django_webhook` | Webhooks Odoo → Django | Notifica a Django cuando una `sale.order` se confirma o una entrega se valida. Relevante cuando el taller (`commerce_level=SELLER`) vende y despacha |
| `multi_company_products` | Multi-tenant en Odoo | Cada taller `commerce_level=SELLER` opera como compañía separada en Odoo |

### 5.2 Flujo: taller upgradeado a `commerce_level=SELLER`

```
Estado previo: workshop.customer_profile existe en Django con historial acumulado

1. Admin activa service_level=ADVANCED y commerce_level=SELLER en Workshop
2. Signal/task → marketplace.Provider.create(name=workshop.name, ...)
3. Signal/task → Odoo API: res.partner.create({customer_rank: 1, supplier_rank: 1, ...})
4. Signal/task → Odoo API: activar módulo Inventory para esa compañía
5. workshop.odoo_partner_id = nuevo_id
6. workshop.provider = nuevo_provider
7. Taller puede ahora:
   - Comprar autopartes con precio B2B (Odoo Purchase) — precio de costo
   - Listar repuestos en el marketplace (products.Product con provider=workshop.provider)
   - Recibir órdenes via orders_odoo + odoo_django_webhook
8. Historial Django (pedidos, gasto, addresses) NO se modifica.
   Odoo parte de cero en su lado — esto es correcto y esperado.
```

### 5.3 Flujo: orden de servicio con repuesto incluido *(Fase 2)*

```
Cliente selecciona servicio → WorkshopService
       │
       ▼
WorkshopService.service.linked_product  ← FK a products.Product (FUTURO)
       │
       ▼
Odoo Repair Order (mrp.repair)
  - partner_id = cliente
  - product_id = repuesto vinculado
  - odoo_repair_id en Workshop
       │
       ▼
Facturación automática (l10n_pe_edi_odoofact)
```

### 5.4 Relación con `res.partner` en Odoo

Un taller con `service_level=MANAGED` o `ADVANCED` genera un único `res.partner`:
- `customer_rank ≥ 1` (puede recibir facturas de servicio)
- `supplier_rank ≥ 1` (puede emitir facturas de repuestos si `commerce_level=SELLER`)

Esto es nativo de Odoo — un partner puede ser cliente **y** proveedor simultáneamente.

---

## 6. Relación con otras apps de Django

### `customer` (Customer / Address / CustomerStats)

La app `customer` y la app `services` trabajan en conjunto. El taller es un `Customer(type='company')` y reutiliza toda la infraestructura ya construida:

```python
# Al registrar el taller, se crea automáticamente:
workshop.customer_profile          # → Customer(type='company')
workshop.customer_profile.stats    # → CustomerStats (total_spent, total_orders)
workshop.customer_profile.addresses.all()  # → Address (taller, envío, agencia)

# El taller puede comprar en marketplace desde service_level=BASIC:
workshop.customer_profile.is_active    # True
workshop.customer_profile.document_type  # 'RUC'

# Desde Customer, navegar al taller:
customer.workshop   # → Workshop (relacionado vía customer_profile)
```

**Regla de tipos — es estricta:**

| Tipo de usuario | `Customer.customer_type` | Puede tener `Workshop` |
|---|---|---|
| Persona natural con vehículo | `individual` | No |
| Empresa / taller | `company` | Sí (via signal) |

Un usuario no puede tener ambos perfiles simultáneamente (restricción del `OneToOneField(User)` en `Customer`). Si un futuro requerimiento lo necesita, se migrará a `AbstractUser` en la versión de producción.

---

### `marketplace` (Provider)

```python
# Un taller con commerce_level=SELLER tiene un Provider asociado
workshop.provider          # → marketplace.Provider
workshop.can_sell_parts    # True

# Desde Provider, acceder al taller
provider.linked_workshop   # → Workshop (OneToOne)
```

### `products` (Product / Category)

El campo comentado en `Service`:
```python
# FUTURO: bundling con marketplace
# linked_product = FK('products.Product')
```
Cuando se active, el flujo será: `WorkshopService → Service → Product → Odoo`.

### `vehicles` (Marca / ModeloVehiculo / VarianteVehiculo)

**Fase 2 — matching por vehículo:**
```
Cliente registra su vehículo (Marca + Modelo + Variante)
       │
       ▼
Sistema filtra WorkshopService con historial del vehículo
       │
       ▼
WorkshopServiceHistory.service → compatible con el vehículo del cliente
```

La compatibilidad vehículo↔servicio reutilizará la lógica de `products.Compatibility` 
ya implementada en `ecomp`.

### `sync` (sincronización Odoo ↔ Django)

Los talleres con `service_level=MANAGED` o `ADVANCED` usan los mismos servicios de sincronización 
que los proveedores de autopartes. La diferencia es que también sincronizan `mrp.repair` 
(Repair Orders) además de `sale.order` y `stock.picking`.

---

## 7. API endpoints planeados

> Las vistas están pendientes. Estructura recomendada:

```
GET  /api/services/workshops/                  Lista pública de talleres verificados
GET  /api/services/workshops/{id}/             Perfil completo del taller
GET  /api/services/workshops/{id}/services/    Servicios ofrecidos con precios

GET  /api/services/categories/                 Árbol de categorías (nivel 1 + subs)
GET  /api/services/services/                   Catálogo maestro de servicios

POST /api/services/workshops/register/         Registro de nuevo taller
PUT  /api/services/workshops/{id}/upgrade/     Cambiar service_level y/o commerce_level

# Protegidos (admin)
POST /api/services/workshops/{id}/verify/      Marcar como verificado
```

---

## 8. Roadmap por fases

### Fase 1 — Directorio verificado (actual)
- [x] Modelos completos (`Workshop`, `ServiceCategory`, `Service`, `WorkshopService`, `WorkshopServiceHistory`, `WorkshopSchedule`)
- [ ] Signal `post_save` → crear `Customer(company)` al registrar taller
- [ ] `Workshop.customer_profile` FK a `customer.Customer`
- [ ] Admin registrado y funcional
- [ ] API REST básica (CRUD de talleres)
- [ ] Migración inicial

### Fase 2 — Inteligencia y citas
- [ ] Motor de matching taller + vehículo + ubicación
- [ ] `WorkshopSchedule` → generación de slots de citas
- [ ] Integración `vehicles.VarianteVehiculo` ↔ `WorkshopServiceHistory`
- [ ] `Service.linked_product` → bundling con marketplace

### Fase 3 — Integración Odoo completa
- [ ] Activación automática de `service_level=MANAGED` → Odoo Partner
- [ ] `commerce_level=SELLER` → Provider + Odoo Inventory
- [ ] `mrp.repair` sync vía webhook
- [ ] Facturación electrónica (l10n_pe_edi_odoofact) desde órdenes de servicio

---

## 9. Decisiones de diseño y rationale

### ¿Por qué dos campos (`service_level` + `commerce_level`) y no un campo único `tier`?

Un campo único mezcla dos dimensiones que en el mercado real son independientes:
- **Dimensión operativa** (ERP): qué tan sofisticado es el control interno del taller.
- **Dimensión comercial** (autopartes): cómo interactúa con el inventario del marketplace.

Forzarlas en un mismo eje crea valores implícitamente acoplados: `SERVICE_AND_PARTS` asume que todo taller que vende también tiene el nivel de ERP más alto, lo cual no siempre es cierto. La separación permite:
- Un taller con ERP (`MANAGED`) que solo compra B2B pero no vende (`B2B_BUYER`).
- Un taller avanzado (`ADVANCED`) sin relación comercial con repuestos (`NONE`) — caso flota corporativa.
- Subir el nivel de ERP sin cambiar la relación comercial, y viceversa.

Las tres combinaciones del modelo anterior (`SERVICE_BASIC`, `SERVICE_ERP`, `SERVICE_AND_PARTS`) siguen siendo válidas y son exactamente `BASIC+BUYER`, `MANAGED+B2B_BUYER` y `ADVANCED+SELLER`.

### ¿Por qué FK simple en `ServiceCategory` y no MPTT?

MPTT agrega complejidad (reconstrucción de árbol, locking) que no se justifica para 2 niveles. El árbol de autopartes sí usa MPTT porque tiene N niveles arbitrarios.

### ¿Por qué `WorkshopSchedule` separado y no JSONField en `Workshop`?

Un JSONField hace imposible filtrar por disponibilidad real (`día=lunes AND hora_inicio<=10:00`). El modelo relacional permite consultas directas para el futuro motor de citas.

### ¿Por qué `min_price/max_price` y no `price_range CharField`?

Un CharField bloquea filtros (`precio < 100`), ordenamiento y analítica. El frontend construye el string visible.

### ¿Por qué `estimated_time_min` y no `estimated_time_hours`?

Los sistemas de agenda (Google Calendar, Calendly) trabajan en minutos. Un `DecimalField(hours)=1.5` es equivalente a `PositiveIntegerField(minutes)=90` pero el segundo permite queries exactas sobre slots.

### ¿Por qué `customer_profile` y no `owner = FK(Customer)` directamente?

Cambiar `owner` a `FK(Customer)` forzaría que el usuario tenga un perfil `Customer` **antes** de registrar el taller, introduciendo un paso adicional en el flujo de onboarding. Además, `owner` como `FK(User)` es el vínculo de autenticación estándar de Django — es más robusto ante cambios futuros en el modelo de usuario.

`customer_profile` como campo separado es la relación semántica correcta: el taller **tiene** un perfil de comprador, no **es** un comprador.

### ¿Se pierden datos al hacer upgrade de `service_level=BASIC` a `MANAGED`?

No. Django es la fuente de verdad del historial del marketplace. Odoo no participaba mientras el taller operaba con `service_level=BASIC`, por lo que no tiene historial que perder. Al hacer upgrade:

- Django: `Customer`, `Address`, `CustomerStats`, pedidos → **intactos**.
- Odoo: se crea un `res.partner` nuevo → **parte de cero**, lo cual es correcto.
- No hay migración de datos, no hay script de importación, no hay pérdida.

Desde el upgrade en adelante, las compras B2B van por Odoo y las compras en el marketplace como Customer siguen en Django como siempre.

### ¿Por qué `Workshop.ruc` se vuelve redundante con `customer_profile`?

`customer.Customer` ya tiene `document_type='RUC'` y `document_number`. El campo `Workshop.ruc` duplica esa información. En la implementación final, `Workshop.ruc` debe eliminarse y todo acceso al RUC del taller debe ir vía `workshop.customer_profile.document_number`. Esto reduce inconsistencias (un taller con dos RUC distintos en la misma base de datos).



observaciones:
la mejor práctica es mantener una sola identidad de autenticación y varios perfiles de negocio.

Punto clave: el problema no es owner. El problema es que el modelo actual de Workshop todavía no tiene customer_profile, aunque eso ya está bien planteado en SERVICES_APP.md:138-196.

Recomendación
User = identidad de login
Customer = perfil comprador en marketplace
Workshop = perfil operativo del taller
Provider = perfil vendedor, solo si vende repuestos
Eso encaja con lo que ya existe:

Customer ya cuelga de User por OneToOne en models.py:23-29.
Workshop hoy cuelga de User por owner en models.py:62-67.
Provider también cuelga de User por owner en models.py:132-137.
Las órdenes del marketplace se consultan por user.customer_profile en views.py:38-45.
Conclusión práctica
No conviene crear un nuevo usuario Django para la suscripción Odoo.

Conviene usar el mismo User y enlazar:

user -> customer_profile
user -> workshop
workshop -> customer_profile
workshop -> provider opcional
Así:

el historial,
los descuentos,
las direcciones,
el gasto acumulado
siguen intactos porque permanecen en el mismo Customer.

Respuesta a la duda principal
Si el taller adquiere MANAGED o ADVANCED, no debería perder beneficios ni historial de cliente.

Eso ya está definido en la documentación:

el historial Django no se toca al hacer upgrade en SERVICES_APP.md:195-196
el upgrade a Odoo debe crear el partner, no reemplazar al cliente en SERVICES_APP.md:346-357
¿Con qué usuario compraría?
Depende del canal:

Compra retail en marketplace: con el mismo Customer de siempre.
Compra operativa B2B en Odoo: con la cuenta Odoo del taller, pero ligada al mismo Workshop.
O sea:

una sola identidad de negocio,
dos contextos operativos.
No deben ser dos usuarios Django distintos.

Buenas prácticas
Mantener owner como ForeignKey(User).
Agregar Workshop.customer_profile = OneToOneField(Customer).
Crear ese Customer(type='company') automáticamente al registrar el taller.
Solo crear Provider cuando el taller sea SELLER.
Crear usuario Odoo técnico/comercial separado si hace falta, pero enlazado al mismo Workshop, no como nuevo usuario del marketplace.
Para múltiples personas del taller, usar membresías/roles, no duplicar el dueño. Ya existe un patrón similar en models.py:500-550.
Para MVP
Sí, es razonable:

trabajar solo con taller tipo comprador,
reutilizar plantillas y flujo de Customer,
dejar preparado el upgrade a MANAGED y ADVANCED.
La reutilización buena sería:

BASIC/BUYER: usa Customer
MANAGED: Customer + Workshop + odoo_partner_id
ADVANCED/SELLER: Customer + Workshop + Provider + setup Odoo
En una frase
No debería manejarse con un nuevo usuario Django.
Debería manejarse con el mismo owner/User, conservando el mismo Customer, y agregando capacidades de Workshop y Provider sobre esa misma identidad.

Si se desea, se puede proponer el cambio exacto de modelo para Workshop y el flujo de upgrade sin romper lo actual.



MEJORA PENDIENTE:


📊 Matriz de Dependencia de Marca
Para tu lógica de matching en el marketplace, podrías clasificar las categorías en tres niveles de sensibilidad a la marca:

1. Nivel Agnóstico (Baja dependencia de marca)
Aquí el taller compite por calidad de acabado y herramienta física, no por manuales de taller.

Planchado y Pintura: El metal se endereza igual en un Toyota que en un Chery. La pintura se mezcla por códigos universales.

Neumáticos y Aros: Desmontar, balancear y alinear se basa en medidas físicas (pulgadas, grados), no en la marca del auto.

Sistema de Escape: Es básicamente metalmecánica y soldadura.

Aire Acondicionado: Los sistemas de carga y detección de fugas son casi estándar en todas las marcas.

2. Nivel Híbrido (Media dependencia)
Requieren piezas específicas, pero el procedimiento suele ser estándar.

Suspensión y Dirección: Aunque las piezas cambian, el sistema de trapecios o amortiguadores es conceptualmente similar, salvo en suspensiones neumáticas o electrónicas.

Frenos: El cambio de pastillas es universal, pero el purgado de módulos ABS a veces requiere software específico.

Sistema de Enfriamiento: Cambiar un radiador es físico, pero conocer los puntos de purga de aire es específico del motor.

3. Nivel Específico (Alta dependencia - "El Taller debe saber de mi marca")
Aquí es donde el WorkshopVehicleExpertise que definiste es el rey del matching.

Motor y Rendimiento: Tolerancias de válvulas, torques de culata y tipos de aceite varían drásticamente.

Diagnóstico: Sin el software/escáner que hable el protocolo de la marca (especialmente en marcas chinas), el taller está ciego.

Transmisión y Embrague: Las cajas automáticas modernas (CVT, DCT) son "cajas negras" que solo un especialista en la marca suele dominar.

Electricidad e Iluminación: Los diagramas de cableado y los buses de datos (CAN bus) son únicos por fabricante.

💡 Impacto en tu Lógica de Negocio (Backend/UX)
Si quieres que tu marketplace sea realmente inteligente, te sugiero aplicar estas reglas en el algoritmo de búsqueda:

Matching por "Expertise" Flexible: Si el usuario busca "Pintura", el sistema no debería penalizar a un taller por no tener el badge de "Experto en Toyota". El ranking debería basarse más en el avg_rating y total_jobs de esa categoría.

Matching por "Expertise" Rígido: Si el usuario busca "Overhaul de Motor" o "Reparación de Caja Automática", el sistema debe priorizar a los talleres que tengan declarada la expertise en esa marca/modelo.

Refactor de la UI:
En el perfil del taller, podrías separar los badges:

"Especialista en [Marca]": Para Motor, Transmisión, Electrónica.

"Servicios Multimarca": Para Planchado, Neumáticos, A/C.

Ejemplo de "Planchado y Pintura" en tu modelo
Para esta categoría, el valor real no es la marca del auto, sino la infraestructura del taller. Un cliente de un auto chino o un auto de lujo buscará lo mismo:

¿Tiene horno de pintura?

¿Usa pintura de calidad (PPG, Glasurit)?

¿Tiene banco de estirado?

Sugerencia: Para las categorías "Agnósticas", podrías añadir un campo de Infraestructura al modelo Workshop (ej. has_paint_booth, has_alignment_machine) que pese más que el expertise de marca al momento de recomendar.

