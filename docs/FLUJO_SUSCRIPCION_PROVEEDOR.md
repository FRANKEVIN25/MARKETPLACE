# Flujo de Suscripción de Proveedor y Asignación de Vehículos

**Estado:** Actualizado 2026-04-22 — refleja simplificación de acciones de Admin, fixes de aprovisionamiento y cambio de record rule de scope.

---

## Índice

1. [Visión general del flujo](#1-visión-general-del-flujo)
2. [Fase 1 — Registro del proveedor (Frontend → Django)](#2-fase-1--registro-del-proveedor-frontend--django)
3. [Fase 2 — Revisión y aprobación (Admin)](#3-fase-2--revisión-y-aprobación-admin)
4. [Fase 3 — Aprovisionamiento en Odoo (Celery)](#4-fase-3--aprovisionamiento-en-odoo-celery)
5. [Fase 4 — Asignación de variantes de vehículo (Django Admin)](#5-fase-4--asignación-de-variantes-de-vehículo-django-admin)
6. [Fase 5 — Push de variantes hacia Odoo](#6-fase-5--push-de-variantes-hacia-odoo)
7. [Relación con el proceso de compatibilidades](#7-relación-con-el-proceso-de-compatibilidades)
8. [Gaps y problemas conocidos](#8-gaps-y-problemas-conocidos)
9. [Referencia de campos clave](#9-referencia-de-campos-clave)
10. [Comandos y endpoints de referencia](#10-comandos-y-endpoints-de-referencia)

---

## 1. Visión general del flujo

```
[Frontend]                [Django]               [Celery]         [Odoo]
    │                        │                       │               │
    │  POST /register-vendor  │                       │               │
    │──────────────────────►  │                       │               │
    │                        │ crea User + Provider  │               │
    │                        │ (is_approved=False)   │               │
    │◄──────────────────────  │                       │               │
    │  201 Creado/Pendiente   │                       │               │
    │                        │                       │               │
    │         [Admin aprueba en Django Admin]         │               │
    │                        │                       │               │
    │                        │ signal post_save ──►  │               │
    │                        │                  create_provider_     │
    │                        │                  with_odoo_setup      │
    │                        │                       │──────────────►│
    │                        │                       │  crea Company │
    │                        │                       │  crea User    │
    │                        │                       │◄──────────────│
    │                        │ guarda odoo_company_id│               │
    │                        │ odoo_user_id          │               │
    │                        │ odoo_username         │               │
    │                        │                       │               │
    │  [Admin asigna variantes_habilitadas en Django Admin]          │
    │                        │                       │               │
    │         [Admin ejecuta "Push variantes a Odoo"]               │
    │                        │◄──────────────────────│               │
    │                        │ push_vehicles         │──────────────►│
    │                        │ --provider-id=X       │  sync scope   │
    │                        │                       │  company_ids  │
```

---

## 2. Fase 1 — Registro del proveedor (Frontend → Django)

### Endpoint

```
POST /api/marketplace/register-vendor/
```

### Payload esperado

```json
{
  "username": "autopartes_abc",
  "email": "contacto@autopartesabc.com",
  "password": "SecurePass123",
  "password_confirm": "SecurePass123",
  "business_name": "AutoPartes ABC SAC",
  "business_email": "ventas@autopartesabc.com",
  "phone": "+51 999 888 777",
  "ruc": "20123456789",
  "odoo_password": "OdooPass123",
  "odoo_password_confirm": "OdooPass123",
  "tier": "starter",
  "accept_terms": true
}
```

### Lo que ocurre en Django

1. `VendorRegistrationSerializer` valida el payload (passwords confirmados, unicidad de username/email, RUC).
2. Dentro de `transaction.atomic()`:
   - Se crea el `User` de Django.
   - Se crea el `Provider` con `is_approved=False`, `is_active=True`.
   - La `odoo_password` se guarda en `odoo_password_temp` usando **Django signing** (`signing.dumps`), **no en texto plano**. Expira en **7 días**.
3. Respuesta `201 Created` — no se lanza ninguna tarea Celery en este paso.

### Respuesta exitosa

```json
{
  "success": true,
  "message": "Registro exitoso para AutoPartes ABC SAC. Tu cuenta será revisada...",
  "user_id": 42,
  "username": "autopartes_abc",
  "task_id": null,
  "business_name": "AutoPartes ABC SAC"
}
```

> **Nota:** El `task_id` retorna `null` en el registro. El endpoint `GET /api/marketplace/registration-status/<task_id>/` solo es útil si en el futuro se lanza una tarea inmediata. Hoy **no tiene uso real** en este punto.

---
## 3. Fase 2 — Revisión y aprobación (Admin)

El SuperAdmin accede a **Django Admin → Proveedores** y revisa el proveedor pendiente.

### Opciones disponibles

El admin solo necesita **2 acciones**:

| Acción admin | Comportamiento |
|---|---|
| **✅ Aprobar y configurar en Odoo** | Inteligente según estado: sin credenciales + no aprobado → aprueba (signal dispara task Celery) / sin credenciales + ya aprobado → relanza task directamente / ya tiene credenciales → sincroniza RUC, email, teléfono, moneda PEN en la Company |
| **🚗 Push variantes a Odoo** | Ejecuta `push_vehicles --provider-id` para cada proveedor seleccionado |

### Lógica de la signal `post_save`

```python
# signals.py
just_approved = not previous and instance.is_approved

if just_approved and not instance.has_odoo_credentials():
    # recupera odoo_password_temp o genera aleatoria si expiró
    task = create_provider_with_odoo_setup.delay(
        user_id=instance.owner.id,
        provider_data={...},
        odoo_password=odoo_password,
    )
```

> **Punto crítico:** Si el admin cambia `is_approved` directamente desde el fieldset de edición del Provider, también se dispara la señal. La tarea Celery es idempotente: al inicio comprueba `has_odoo_credentials()` y sale limpiamente si el provider ya está aprovisionado (protege contra tasks duplicadas en cola). Además, antes de guardar los IDs de Odoo, limpia automáticamente cualquier provider huérfano (sin `odoo_user_id`) que tenga el mismo `odoo_company_id`, evitando conflictos de unique constraint con datos de seed.

---

## 4. Fase 3 — Aprovisionamiento en Odoo (Celery)

**Task:** `create_provider_with_odoo_setup` → `services/provisioning.py`

### Pasos internos (transacción atómica)

```
1. Verificar que el User Django existe
2. Buscar o crear el Provider en Django
   └─ Guard: si ya tiene credenciales completas (task duplicada), retorna inmediatamente
3. Crear Company en Odoo
   └─ odoo.create_company(name, email, currency_code='PEN', vat, phone)
4. Generar odoo_username único
   └─ usa provider.email → o email derivado del nombre del provider
5. Crear User en Odoo vinculado a la Company
   └─ odoo.create_user_for_company(name, login, password, company_id)
   └─ Grupos: stock.group_stock_manager + sales_team.group_sale_salesman
6. Limpiar providers huérfanos con mismo odoo_company_id (datos de seed sin user_id)
7. Guardar en Provider:
   └─ odoo_company_id, odoo_user_id, odoo_username
   └─ odoo_password_hash (make_password)
   └─ odoo_password_temp = '' (se borra)
```

### Resultado en DB después del aprovisionamiento

| Campo | Antes | Después |
|---|---|---|
| `odoo_company_id` | `null` | ID numérico de Odoo |
| `odoo_user_id` | `null` | ID numérico de Odoo |
| `odoo_username` | `null` | email/login del proveedor en Odoo |
| `odoo_password_hash` | `''` | hash Django |
| `odoo_password_temp` | valor cifrado | `''` (borrado) |
| `is_approved` | `False` | `True` |

### Verificar estado de aprovisionamiento (Admin)

Acción: **"Verificar conexión Odoo"** → llama `verify_provider_odoo_connection(provider.id)`.

Para verificar manualmente desde terminal:

```bash
docker exec -it ecomparts-backend python manage.py shell -c "
from apps.marketplace.models import Provider
p = Provider.objects.get(pk=4)
print(p.has_odoo_credentials(), p.odoo_company_id, p.odoo_username)
"
```

---

## 5. Fase 4 — Asignación de variantes de vehículo (Django Admin)

> **Prerequisito:** El proveedor debe tener `odoo_company_id` (aprovisionamiento completado).

### Qué es `variantes_habilitadas`

Campo M2M en `Provider` → `vehicles.VariantVehiculo`. Define el **scope de vehículos** con los que trabaja el proveedor. Tiene tres efectos:

1. **Visibilidad en Odoo:** Los proveedores solo ven las variantes de su scope en su UI de Odoo para crear compatibilidades.
2. **Filtro de catálogo para clientes:** Permite mostrar al comprador qué proveedores tienen piezas para su vehículo.
3. **Guía para el push de vehículos** (`push_vehicles --provider-id`).

### Pasos en Django Admin

1. Ir a **Admin → Proveedores → [proveedor]**
2. En el fieldset **"🚗 Scope de Vehículos"**, usar el widget `filter_horizontal` para seleccionar variantes.
3. Buscador disponible por: `modelo__nombre`, `modelo__marca__nombre`, `motor__codigo_motor`, `anio_desde`.
4. Guardar el Provider.

> El save **solo actualiza la relación M2M en Django**. Odoo todavía no sabe nada de este cambio hasta el paso siguiente.

### ¿Hay conflicto con otras relaciones?

La relación M2M `variantes_habilitadas ↔ providers_habilitados` es **independiente** de:
- `products.Product.compatible_con` (compatibilidades de producto) — se gestiona desde `autopart.compatibility` en Odoo y se sincroniza vía `sync_provider_compatibility`.
- `odoo_variante_id` en `VariantVehiculo` — se llena por `push_vehicles`, no por la asignación del scope.

**No hay conflicto directo**, pero sí existe una **dependencia de orden**: si el proveedor no tiene variantes en su scope, no podrá crear compatibilidades en Odoo desde su UI, porque Odoo no le mostrará ninguna variante.

---

## 6. Fase 5 — Push de variantes hacia Odoo

Después de guardar el scope de vehículos, hay que sincronizarlo con Odoo.

### Opción A: Acción de Admin

En la lista de Proveedores, seleccionar el proveedor y ejecutar **"🚗 Push variantes a Odoo (scope por proveedor)"**.

Internamente llama:
```bash
manage.py push_vehicles --provider-id=<ID>
```

### Opción B: Desde terminal

```bash
# Solo las variantes del proveedor (scope)
docker exec -it ecomparts-backend python manage.py push_vehicles --provider-id=5

# Solo variantes nuevas sin odoo_variante_id (más rápido)
docker exec -it ecomparts-backend python manage.py push_vehicles --provider-id=5 --only-unlinked

# Dry-run para verificar sin escribir
docker exec -it ecomparts-backend python manage.py push_vehicles --provider-id=5 --dry-run
```

### Qué hace `push_vehicles --provider-id`

```
1. Lee provider.variantes_habilitadas
2. Para cada VariantVehiculo en el scope:
   a. Push de Marca → Modelo → Motor → Transmisión → Tracción → VariantVehiculo
      (estrategia 3 vías: busca por django_external_id → clave natural → crea)
   b. Guarda odoo_variante_id en Django si es nuevo
3. sync_full_scope_for_company:
   - Añade company_id a vehiculo.variante.company_ids en Odoo (variantes del scope)
   - Quita company_id de variantes que ya NO están en el scope de Django
```

### Resultado esperado en Odoo

El proveedor, al entrar a su instancia de Odoo, solo verá en el selector de `vehiculo.variante` las variantes que le asignó el admin. Esto le permite crear compatibilidades (`autopart.compatibility`) desde la UI de Odoo.

> **Nota de idempotencia:** `push_vehicles` puede correrse múltiples veces sin riesgo. Si el proveedor ya tenía una variante en Odoo, la encuentra por `django_external_id` y no la duplica.

---

## 7. Relación con el proceso de compatibilidades

### ¿Cómo se conectan?

```
[Odoo — UI del proveedor]
  Proveedor crea/edita registros en autopart.compatibility
  (product.template + vehiculo.variante)
            ↓
[Celery — sync horaria]
  sync_provider_products → sync_provider_compatibility
  Trae todos los autopart.compatibility del proveedor desde Odoo
  Resuelve VariantVehiculo por odoo_variante_id → crea/actualiza
  products.ProductCompatibility en Django
```

### Puntos de contacto críticos

| Situación | Qué pasa |
|---|---|
| Variante en scope M2M pero **sin `odoo_variante_id`** | El proveedor la ve en Odoo, pero si `sync_provider_compatibility` la recibe, no puede resolverla y la logging como no encontrada. |
| Variante **fuera del scope** del proveedor | El proveedor no puede crearle compatibilidades en Odoo, por lo que nunca llega a Django. Sin conflicto activo. |
| Se **quita una variante** del scope y se hace push | Odoo quita `company_id` → el proveedor ya no la ve en su UI → no crea nuevas compatibilidades con ella. Las compatibilidades **ya existentes en Django** no se borran automáticamente. |
| `push_vehicles` se corre **después** de que el proveedor ya creó compatibilidades | Las compatibilidades ya existen en Odoo; el push solo actualiza `company_ids`. No afecta `autopart.compatibility`. |

### ¿Hay conflicto con `sync_provider_compatibility`?

No directamente. Los dos procesos son independientes:
- **`push_vehicles`** modifica `vehiculo.variante.company_ids` en Odoo (visibilidad).
- **`sync_provider_compatibility`** lee `autopart.compatibility` en Odoo (datos de compatibilidad de producto).

El único punto de roce es el campo `odoo_variante_id` en `VariantVehiculo`: si `push_vehicles` lo actualiza mientras corre `sync_provider_compatibility`, puede haber un race condition teórico. En la práctica, el push es raro y rápido; la sync horaria es lo normal. No se ha reportado problema real aquí.

> **Recordatorio del estado actual de compat-sync** (ver `compatibility-sync-current-state.md`): la sync hace full scan, no usa cursor ni reconcilia borrados/desactivaciones. Esto significa que si se borra una compatibilidad en Odoo, **no se borra en Django** hasta que se implemente reconciliación.

---

## 8. Gaps y problemas conocidos

### ❶ Contraseña temporal expira en 7 días

`odoo_password_temp` se firma con `signing.dumps(..., max_age=604800)`. Si el admin demora más de **7 días** en aprobar, la contraseña expira. La acción "Aprobar y configurar en Odoo" detecta esto con `get_odoo_password_temp() → None` y **genera una contraseña aleatoria** sin notificar al proveedor.

**Impacto:** El proveedor no sabe su contraseña de Odoo.  
**Solución pendiente:** Enviar email al proveedor con sus credenciales de Odoo una vez aprobado, o permitirle cambiarla desde el portal.

---

### ❷ No hay notificación de aprobación al proveedor

El flujo completo no envía ningún email al proveedor cuando:
- Es aprobado.
- Odoo queda configurado.
- Sus variantes son asignadas.

**Solución pendiente:** Task `send_approval_email.delay(provider.id)` a disparar desde la signal `post_save` justo después de lanzar `create_provider_with_odoo_setup`.

---

### ❸ El push de vehículos es completamente manual

Después de asignar `variantes_habilitadas`, el admin debe acordarse de ejecutar la acción de push. No hay ningún mecanismo automático ni recordatorio.

**Riesgo:** El proveedor queda aprobado y con Odoo configurado, pero no ve ninguna variante en su Odoo hasta que el admin haga el push. No puede crear compatibilidades.

**Solución pendiente:** Considerar si el save del M2M debe encolar automáticamente `push_vehicles` como task Celery, o al menos mostrar un warning en el Admin si hay variantes asignadas sin `odoo_variante_id`.

> **Nota sobre visibilidad en Odoo:** La record rule `rule_vehiculo_variante_by_company` usa dominio estricto `[('company_ids', 'in', [company_id])]`. Las variantes sin scope asignado son invisibles para todos los proveedores. El proveedor SOLO ve las variantes que tiene en `company_ids` tras el push. El grupo de Inventario asignado (`stock.group_stock_manager`) permite crear productos sin otorgar permisos de administrador del sistema.

---

### ❹ Membresía (Member) no se crea en el registro

El modelo `Member` (relación User ↔ Provider con roles y permisos) **no se crea durante el registro automático**. El `owner` del Provider queda vinculado solo por la FK `Provider.owner`, no por una entrada en `Member`.

**Impacto:** El owner no aparece en la lista de miembros del provider. Queries que buscan acceso vía `Member` no lo devuelven.

**Solución pendiente:** Crear automáticamente un `Member` con `role='owner'` durante `create_provider_with_odoo_setup` o en el registro en `register_vendor`.

---

### ❺ Campo `tax_regime` / `igv_applicable` / `emite_comprobante` sin onboarding

El Provider tiene campos tributarios (`tax_regime`, `igv_applicable`, `emite_comprobante`) que son relevantes para el proceso de facturación. Actualmente no se solicitan durante el registro ni aparecen en el flujo de onboarding.

**Estado:** Quedan en el valor por defecto (`GENERAL`, IGV=True, `ambos`). El admin debe configurarlos manualmente.

---

### ❻ Datos de pago (`banco_*`, `yape_*`, `plin_*`) sin onboarding

Similar al punto anterior. El proveedor no tiene un flujo para ingresar sus datos bancarios. Son campos vacíos hasta que se llenen manualmente desde la API o el Admin.

---

### ❼ `check_registration_status` devuelve estado de task Celery inexistente

El endpoint `GET /api/marketplace/registration-status/<task_id>/` espera un `task_id` de Celery v alente. Pero durante el registro, el `task_id` retornado es `null`. El endpoint queda sin uso funcional hoy.

---

### ❽ Compatibilidades existentes no se borran al quitar variantes del scope

Si el admin quita una variante del scope de un proveedor y hace push, Odoo actualiza `company_ids`. Pero los registros `ProductCompatibility` en Django que ya existían **no se eliminan ni desactivan**. Un comprador podría seguir viendo esa compatibilidad.

---

## 9. Referencia de campos clave

### Provider (marketplace/models.py)

| Campo | Tipo | Descripción |
|---|---|---|
| `is_approved` | `BooleanField` | Activa el flujo de aprovisionamiento vía signal |
| `is_active` | `BooleanField` | Marcado `True` automáticamente al aprobar |
| `odoo_company_id` | `IntegerField` | ID de `res.company` en Odoo |
| `odoo_user_id` | `IntegerField` | ID de `res.users` en Odoo |
| `odoo_username` | `EmailField` | Login del proveedor en Odoo |
| `odoo_password_temp` | `CharField(500)` | Contraseña temporal cifrada (se borra al aprobar) |
| `odoo_password_hash` | `CharField(255)` | Hash de contraseña Odoo (make_password) |
| `tier` | `CharField` | `starter` / `pro` / `premium` |
| `variantes_habilitadas` | `M2M → VariantVehiculo` | Scope de vehículos del proveedor |
| `tax_regime` | `CharField` | Régimen tributario |
| `emite_comprobante` | `CharField` | Tipo de comprobante fiscal |

### VariantVehiculo (vehicles/models.py)

| Campo | Tipo | Descripción |
|---|---|---|
| `modelo` | `FK → ModeloVehiculo` | Marca + Modelo |
| `motor` | `FK → Motor` | Motor (combustible, cc, código) |
| `transmision` | `FK → Transmision` | Tipo de transmisión |
| `traccion` | `FK → Traccion` | Tracción (4x2, 4x4, AWD) |
| `anio_desde` | `PositiveIntegerField` | Año inicial de fabricación |
| `anio_hasta` | `PositiveIntegerField` | Año final (null = vigente) |
| `odoo_variante_id` | `IntegerField, unique` | ID de `vehiculo.variante` en Odoo — ancla para compat-sync |

---

## 10. Comandos y endpoints de referencia

### Endpoints REST

```
POST   /api/marketplace/register-vendor/
GET    /api/marketplace/registration-status/<task_id>/
GET    /api/marketplace/providers/
GET    /api/marketplace/providers/<id>/
POST   /api/marketplace/providers/<id>/sync_products/
GET    /api/marketplace/providers/<id>/verify_connection/
```

### Comandos Django Management

```bash
# Push global de vehículos (puesta en marcha inicial)
python manage.py push_vehicles

# Push de scope para proveedor específico
python manage.py push_vehicles --provider-id=<ID>

# Push incremental (solo nuevas variantes sin odoo_variante_id)
python manage.py push_vehicles --provider-id=<ID> --only-unlinked

# Dry-run
python manage.py push_vehicles --provider-id=<ID> --dry-run

# Seed de datos de vehículos (si el catálogo está vacío)
python manage.py seed
```

### Tareas Celery relevantes

```python
create_provider_with_odoo_setup.delay(user_id, provider_data, odoo_password)
sync_provider_products.delay(provider_id)
sync_provider_compatibility.delay(provider_id)
verify_provider_odoo_connection(provider_id)  # síncrona, no delay
```

### Acciones de Admin disponibles en Provider

| Acción | Descripción |
|---|---|
| ✅ Aprobar y configurar en Odoo | Inteligente: aprueba+provisiona / relanza task / sincroniza datos según estado del provider |
| 🚗 Push variantes a Odoo | Ejecuta `push_vehicles --provider-id` para cada proveedor seleccionado |

---

## Orden correcto del flujo completo (checklist operativo)

```
[ ] 1. Proveedor completa el formulario de registro en el Frontend
[ ] 2. Admin recibe solicitud y revisa datos del proveedor en Django Admin
[ ] 3. Admin ejecuta "Aprobar y configurar en Odoo"
[ ] 4. Celery task crea Company (moneda PEN) + User (Inventario: Administrador) en Odoo
       → verificar que odoo_company_id quede poblado en Django
[ ] 5. Admin abre el Provider → fieldset "Scope de Vehículos" → asigna variantes_habilitadas → guarda
[ ] 6. Admin ejecuta acción "Push variantes a Odoo" para ese proveedor
[ ] 7. Verificar en la UI de Odoo del proveedor que ve SOLO las variantes asignadas
[ ] 8. (Pendiente-manual) Comunicar al proveedor sus credenciales de Odoo
[ ] 9. Proveedor comienza a cargar productos y compatibilidades en Odoo
[ ] 10. Sync horaria de Celery trae productos y compatibilidades a Django automáticamente
```
