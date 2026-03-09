# Flujo de Compra Multiproveedor — ECOMPARTS Marketplace
> Documentación técnica basada en el código real del proyecto (marzo 2026)
> **Última revisión:** 5 de marzo de 2026 — v3: rediseño de estados, flags, PaymentTransaction, expiración por SubOrder

---

## 1️⃣ Principio rector

| Actor | Responsabilidad |
|---|---|
| **SvelteKit (Frontend)** | Inicia acciones, muestra estados y gestiona la sesión de checkout (TTL 3 h). No calcula reglas de negocio. |
| **Django (Marketplace)** | Orquesta todo el negocio: crea órdenes, gestiona pagos, expira reservas, decide cuándo integrar con Odoo. |
| **Odoo** | Ejecuta operaciones ERP **solo cuando el pago ya fue confirmado**: ventas, stock, facturación, SUNAT. |
| **Celery** | Ejecuta la integración Django→Odoo de forma asíncrona (no bloquea al cliente). También ejecuta el job de expiración de órdenes pendientes. |

> ⚠️ **Odoo recibe únicamente SubOrders con pago confirmado.**
> Órdenes en `pendiente_pago` o `pago_en_revision` **nunca** se envían a Odoo.
> Django es el único orquestador del flujo completo.

---

## 2️⃣ Decisión crítica de arquitectura: cuándo entra Odoo

```
ANTES (incorrecto):   Order creada → SubOrder creada → 🔥 Celery → Odoo (draft)
CORRECTO:             Order creada → SubOrder creada → (espera pago)
                                                        ↓
                                           Proveedor confirma pago
                                                        ↓
                                              🔥 Celery → Odoo (draft)
                                                        ↓
                                           Proveedor confirma cotización en Odoo
                                                        ↓
                                                    sale.order → stock reservado
```

**Motivo:** Los pagos siempre son digitales (Yape / Plin / transferencia). Una orden sin
comprobante aprobado no tiene valor operativo para el proveedor. Enviarla a Odoo crea
ruido en el ERP y degrada la calidad de los datos de ventas.

**Impacto en código:** En `views.py → create_order`, eliminar el `transaction.on_commit`
que encola `create_odoo_sale_order`. Esa tarea pasa a encolarse **únicamente** en
`confirm_payment` cuando `action == 'confirm'` (ya existe ese call, solo hay que quitar
el de la creación).

---

---

## 3️⃣ Flujo completo end-to-end

### 🛒 A. Checkout en el Frontend (SvelteKit — 4 pasos)

```
Paso 1 — Carrito
Paso 2 — Perfil ← confirma datos personales
Paso 3 — Entrega ← elige método de entrega → POST crea la orden en Django
Paso 4 — Pago y Confirmación ← sube comprobante(s) por cada proveedor
```

#### Paso A1 — Carrito
- El cliente agrega productos. Pueden pertenecer a distintos proveedores.
- El frontend **no calcula** impuestos ni valida stock final (responsabilidad del backend).

#### Paso A2 — Perfil
- Confirma datos del cliente (solo lectura desde el perfil guardado).
- Acepta términos y condiciones.

#### Paso A3 — Entrega y creación de orden
- El cliente elige método: `domicilio` / `agencia` / `tienda`.
- Si requiere dirección física, selecciona o crea una desde `customer.Address`.
- Al hacer clic en **"Confirmar y continuar al pago"**, el frontend llama al backend para crear la orden.
- Django crea la `Order` con `payment_deadline = now() + 3h` y las SubOrders con `status = 'pendiente_pago'`.
- **No se encola ninguna tarea Celery hacia Odoo en este paso.**

**Payload que el frontend envía a Django:**
```json
{
  "customer_id": 42,
  "delivery_method": "domicilio",
  "shipping_address_id": 7,
  "customer_notes": "Portón azul, segundo piso.",
  "items": [
    { "product_id": 101, "quantity": 2 },
    { "product_id": 205, "quantity": 1 }
  ]
}
```
> 📌 La orden **no existe** en ningún sistema hasta este POST. Solo existen items en el carrito del frontend.

#### Paso A4 — Pago con reserva de 3 horas ⏱️

Una vez creada la orden, el frontend entra al paso 4 con las siguientes reglas de UX:

- **Muestra:** _"Por favor realiza el pago pendiente. La reserva de stock tiene como máximo 3 horas."_
- **Cuenta regresiva** calculada como `order.payment_deadline - now()`.
- **Botón "Pagar más tarde":** redirige al historial de compras; la cuenta regresiva sigue corriendo.
- **Si el tiempo expira** (frontend detecta countdown = 0 o backend responde 410 Gone para esa SubOrder):
  - El frontend muestra _"La reserva de este artículo ha expirado y fue liberado."_ por cada SubOrder afectada.
  - Las SubOrders de otros proveedores que ya están en `pagado` o superior no se ven afectadas.
  - El backend (Celery beat) marca solo las SubOrders en `pendiente_pago` como `status='cancelado'` + `expired=True`.

> Ver sección 4 para el mecanismo de expiración por SubOrder en el backend.

---

### 🧠 B. Creación de Order y SubOrders (Django)

**Endpoint:** `POST /api/orders/orders/create_order/`

El backend ejecuta todo en una **transacción atómica**:

#### Paso B1 — Crear `Order`
```python
Order.status = 'pendiente_pago'
Order.order_number = 'ORD-2026-00001'   # generado automáticamente
Order.payment_deadline = now() + timedelta(hours=3)   # ← NUEVO campo requerido
Order.customer = customer
Order.delivery_method = 'domicilio'
Order.shipping_address = address
```

#### Paso B2 — Crear `SubOrder` (una por proveedor)
Los items del carrito se agrupan por `product.provider`. Por cada grupo:
```python
SubOrder.status = 'pendiente_pago'
SubOrder.provider = provider_X
SubOrder.sub_order_number = 'ORD-2026-00001-A'   # letra correlativa: A, B, C…
SubOrder.order = order
SubOrder.subtotal / igv_amount / total  # calculados en el momento
```

> 📌 **NO se encola ninguna tarea Celery hacia Odoo en este paso.**
> La orden existe solo en Django hasta que el pago sea confirmado por el proveedor.

---

### ⏰ C. Expiración automática por SubOrder (Celery beat — cada 15 min)

> ⚠️ **Decisión de diseño v3:** la expiración se aplica **por SubOrder**, no por Order.
> Si la SubOrder-A ya está en `pagado` y la SubOrder-B sigue en `pendiente_pago`,
> solo SubOrder-B expira. La Order sigue viva con el estado derivado de sus SubOrders activas.

**Tarea:** `expire_pending_suborders` en `apps/orders/tasks.py`

```python
@shared_task
def expire_pending_suborders():
    """
    Expira únicamente las SubOrders en pendiente_pago cuyo payment_deadline ha vencido.
    La Order.status se recalcula automáticamente vía signal post_save.
    """
    threshold = now()
    expired = SubOrder.objects.filter(
        status='pendiente_pago',
        order__payment_deadline__lt=threshold
    )
    count = 0
    for sub in expired:
        sub.status   = 'cancelado'
        sub.expired  = True          # flag de auditoría
        sub.save(update_fields=['status', 'expired'])
        count += 1
        # liberar stock reservado en StockItem si aplica
    logger.info(f"⏱️  {count} SubOrders expiradas y marcadas como cancelado")
```

**Campo `payment_deadline` en `Order`** (no en SubOrder, la deadline es de la orden):
```python
payment_deadline = models.DateTimeField(
    null=True, blank=True,
    help_text="Límite de pago (created_at + 3h). Pasada esta fecha las SubOrders pendientes expiran."
)
```

**Flags de auditoría en `SubOrder`** (ver sección 10 para el modelo completo):
```python
expired  = models.BooleanField(default=False,
    help_text="True si el status='cancelado' fue causado por expiración del TTL.")
```

---

### 💳 D. Pago y comprobante (Paso 4 del frontend)

El frontend muestra **una card por SubOrder** con:
- Datos bancarios del proveedor (`provider_payment_info`)
- Cuenta regresiva hasta `order.payment_deadline`
- Formulario para subir comprobante

#### Paso D1 — El cliente realiza el pago (fuera del sistema)
- Transferencia bancaria, Yape o Plin (siempre digital).

#### Paso D2 — Cliente sube comprobante

**Endpoint:** `POST /api/orders/suborders/{id}/upload_payment/`

Se crea un objeto `PaymentTransaction` (ver modelo completo en sección 10):

```python
# Se crea una nueva PaymentTransaction ligada a la SubOrder
PaymentTransaction.suborder        = sub_order
PaymentTransaction.amount          = 350.00
PaymentTransaction.method          = 'yape' | 'plin' | 'transferencia'
PaymentTransaction.operation_number = '123456789'
PaymentTransaction.proof_file      = <imagen>
PaymentTransaction.status          = 'uploaded'
PaymentTransaction.uploaded_by     = request.user

# Estado de la SubOrder actualizado:
SubOrder.status          → 'pago_en_revision'
SubOrder.payment_rejected = False  # limpiar flag si era un reintento
```

> `Order.status` se recalcula automáticamente vía signal al guardar la SubOrder.

> No se envía nada a Odoo en este paso.

#### Paso D3 — Confirmación inline (fin del paso 4)
Una vez subido al menos un comprobante por SubOrder, el frontend muestra la confirmación
con `order_number` y botones "Ver mis pedidos" / "Seguir comprando".

> El cliente puede subir nuevos comprobantes si el proveedor rechaza uno previo
> (ver Paso E2). No se necesita un endpoint distinto; se crea una nueva `PaymentTransaction`.

---

### 🏢 E. Revisión del comprobante (proveedor)

**Endpoint:** `POST /api/orders/suborders/{id}/review_payment/`
Solo accesible para el owner del Provider (`owned_providers`).

#### Paso E1 — Proveedor aprueba el pago
```python
# payload: {"action": "approve", "payment_transaction_id": 17}

PaymentTransaction.status      → 'approved'
PaymentTransaction.reviewed_by → request.user
PaymentTransaction.reviewed_at → now()

SubOrder.status       → 'pagado'
SubOrder.confirmed_at → now()

# ✅ AQUÍ se encola por primera vez la tarea Celery hacia Odoo:
transaction.on_commit(lambda: create_odoo_sale_order.delay(sub_order.id))
```

#### Paso E2 — Proveedor rechaza el pago
```python
# payload: {"action": "reject", "payment_transaction_id": 17, "rejection_reason": "Monto incorrecto"}

PaymentTransaction.status          → 'rejected'
PaymentTransaction.rejection_reason = 'Monto incorrecto'
PaymentTransaction.reviewed_by     → request.user
PaymentTransaction.reviewed_at     → now()

# SubOrder vuelve a pendiente_pago para permitir nuevo intento
SubOrder.status           → 'pendiente_pago'
SubOrder.payment_rejected  = True   # flag: indica que hubo un rechazo previo

# NO se encola tarea Odoo.
# El cliente verá el motivo de rechazo y podrá subir un nuevo comprobante.
# La UI debe mostrar claramente el rechazo y habilitar el formulario de reintento.
```

> 🔑 **Por qué es un flag y no un estado:** `pago_rechazado` como estado rompía la
> máquina de estados: ¿desde qué estado se retoma? Usando `payment_rejected = True`
> con `status = 'pendiente_pago'`, el flujo normal de "subir comprobante" funciona
> sin cambios. El frontend solo necesita leer el flag para mostrar el aviso de rechazo.

---

### 🧾 F. Creación de `sale.order` en Odoo (solo tras pago confirmado)

**Función:** `sync_suborder_to_odoo(suborder)` — `apps/orders/signals.py`
**Protocolo:** XML-RPC (`xmlrpc.client.ServerProxy`) — puerto 8069

> Se ejecuta **solo** cuando `SubOrder.status = 'pagado'`. Nunca antes.

#### Paso F1 — Buscar o crear Partner (cliente)
```python
# Estrategia (ya implementada):
#   1. Buscar por email
#   2. Si no existe, buscar por vat (DNI/RUC)
#   3. Si no existe, crear nuevo partner
```

#### Paso F2 — Crear `sale.order` en estado `draft`
```python
sale_order_data = {
    'partner_id':                partner_id,
    'company_id':                provider.odoo_company_id,
    'order_line':                order_lines,
    'client_order_ref':          suborder.sub_order_number,
    'origin':                    order.order_number,
    'x_marketplace_order_id':    order.order_number,
    'x_marketplace_suborder_id': suborder.sub_order_number,
    'x_delivery_method':         order.delivery_method,
    'x_delivery_address':        _format_delivery_address(order),
    'x_customer_notes':          order.customer_notes,
    'x_payment_status':          'confirmado',   # llega ya con pago confirmado
    'x_is_payment_confirmed':    True,
    ...
}
```

#### Idempotencia (primera línea de defensa)
```python
if suborder.odoo_sale_id:
    return suborder.odoo_sale_id   # ya existe, no crear de nuevo
```
Segunda línea de defensa: constraint `UNIQUE(x_marketplace_suborder_id)` en Odoo (ver §6).
La tarea Celery tiene `max_retries=3` con `countdown=300` (5 min entre reintentos),
pero no reintenta ante `IntegrityError` de Odoo.

---

### 📦 G. Confirmación de cotización y despacho en Odoo

#### G1 — Proveedor confirma la `sale.order` en Odoo (cotización → orden de venta)
- Botón **Confirmar** en Odoo → `sale.order.state = 'sale'`
- Odoo reserva stock automáticamente.
- **Webhook / polling Django:** detecta el cambio y actualiza `SubOrder.status → 'confirmado'`
- `Order.status` se recalcula automáticamente vía signal (ver sección 11).

#### G2 — Proveedor genera el picking (entrega) en Odoo
- Odoo crea un `stock.picking` al confirmar la venta.
- El proveedor registra el número de tracking en Django (`SubOrder.tracking_number`).
- Al validar el picking en Odoo, `stock.picking.state = 'done'`.
- **Webhook / polling Django:** `SubOrder.status → 'enviado'`

#### G3 — Entrega al cliente
- El cliente confirma recepción en el frontend (o el proveedor la marca manualmente).
- `SubOrder.status → 'entregado'`
- En Odoo: picking validado + opcionalmente factura generada.

---

## 4️⃣ Expiración de SubOrders abandonadas (reserva de 3 horas)

### Objetivo
Evitar que el catálogo y las listas de órdenes se llenen de "basura" por checkouts abandonados.

### Principio de diseño: expirar por SubOrder, no por Order

Escenario multiproveedor real:

```
SubOrder-A (Proveedor A) → pagado        ← ya confirmado, va a Odoo
SubOrder-B (Proveedor B) → pendiente_pago ← el cliente abandonó este pago
SubOrder-C (Proveedor C) → pagado        ← ya confirmado, va a Odoo
```

Si se expirara la `Order` completa, se cancelaría SubOrder-A y SubOrder-C que ya
tienen pago confirmado. **Eso es incorrecto.**

La solución: **solo expiran las SubOrders en `pendiente_pago`** cuya `Order.payment_deadline`
ya venció. SubOrder-A y SubOrder-C siguen su ciclo normal.

### Implementación en Django

**Tarea Celery (periódica, cada 15 min):**
```python
@shared_task
def expire_pending_suborders():
    threshold = now()
    # Solo SubOrders que aún esperan pago y cuya orden ya venció
    to_expire = SubOrder.objects.filter(
        status='pendiente_pago',
        order__payment_deadline__lt=threshold
    ).select_related('order')

    count = 0
    for sub in to_expire:
        sub.status  = 'cancelado'
        sub.expired = True
        sub.save(update_fields=['status', 'expired'])
        # liberar stock reservado en StockItem si aplica
        count += 1
    logger.info(f"⏱️  {count} SubOrders expiradas → status=cancelado, expired=True")
    # Order.status se recalcula automáticamente vía signal post_save en SubOrder
```

**En `create_order` (views.py):**
```python
order = Order.objects.create(
    ...
    payment_deadline=timezone.now() + timedelta(hours=3)
)
```

### Frontend: manejo de la cuenta regresiva

1. Al cargar el Paso 4 o la página de detalle, calcular:
   ```ts
   const deadline = new Date(order.payment_deadline);
   const remaining = deadline.getTime() - Date.now();  // ms
   ```
2. Si `remaining <= 0` o el backend devuelve `410 Gone` para una SubOrder específica:
   - Mostrar: _"La reserva de este proveedor ha expirado. Ese artículo fue liberado."_
   - Las SubOrders de otros proveedores ya pagadas siguen visibles con su estado normal.
3. Mientras `remaining > 0`, mostrar countdown `HH:MM:SS` por SubOrder pendiente.
4. Botón **"Pagar más tarde"** → redirige a `/cliente/historial-compras` sin cancelar.

> 📌 Las SubOrders con `expired = True` pueden mostrarse en una sección colapsable
> "Artículos no completados" durante 24 h y luego ocultarse. No afectan el historial
> de las SubOrders que sí se pagaron correctamente.

---

## 5️⃣ Tablas de estados — diseño definitivo v3

### Principio de diseño

Los estados de negocio (`status`) representan **etapas del flujo operativo normal**.
Las condiciones excepcionales (rechazo de pago, expiración, reembolso) se representan
como **flags booleanos** en el modelo. Esto evita explosión combinatoria de estados
y simplifica la máquina de estados.

```
ANTI-PATRÓN:  pago_rechazado, expirada, reembolsada  ← estados que son eventos/flags
PATRÓN CORRECTO: payment_rejected=True, expired=True, refunded=True  ← flags de auditoría
```

---

### SubOrder (Django) — 7 estados operativos

| `SubOrder.status` | Descripción | `odoo_sale_id` | Estado en Odoo |
|---|---|---|---|
| `pendiente_pago` | Esperando comprobante del cliente | ❌ | — |
| `pago_en_revision` | Comprobante subido, proveedor revisando | ❌ | — |
| `pagado` | Proveedor aprobó el pago | ✅ Creado (`draft`) | `draft` |
| `confirmado` | Proveedor confirmó la cotización en Odoo | ✅ | `sale` |
| `enviado` | Proveedor registró tracking / validó picking | ✅ | `sale` + picking validado |
| `entregado` | Cliente recibió la mercancía | ✅ | picking `done` |
| `cancelado` | Cancelada manual o por expiración (ver flags) | ✅/❌ | `cancel` si aplica |

**Flags complementarios en SubOrder (no son estados):**

| Flag | Tipo | Significado |
|---|---|---|
| `payment_rejected` | `BooleanField` | El último comprobante fue rechazado. `status` vuelve a `pendiente_pago`. |
| `expired` | `BooleanField` | El `cancelado` fue causado por vencimiento del TTL. |
| `refunded` | `BooleanField` | Se procesó un reembolso para esta SubOrder. |
| `odoo_sync_error` | `BooleanField` | Error definitivo al sincronizar con Odoo. |

> Con estos flags se pueden construir vistas específicas:
> - `status=cancelado AND expired=True` → "pedidos expirados"
> - `status=cancelado AND refunded=True` → "pedidos reembolsados"
> - `status=pendiente_pago AND payment_rejected=True` → "requieren nuevo comprobante"

---

### Máquina de estados de SubOrder

```
pendiente_pago
    │
    ├──[cliente sube comprobante]──→ pago_en_revision
    │                                       │
    │                          ┌────────────┴────────────┐
    │                          ↓                         ↓
    │                  [proveedor aprueba]       [proveedor rechaza]
    │                          ↓                         ↓
    │                        pagado          pendiente_pago
    │                          │             + payment_rejected=True
    │                          ↓
    │                 Celery → Odoo draft
    │                          ↓
    │              [proveedor confirma en Odoo]
    │                          ↓
    │                       confirmado
    │                          ↓
    │                [proveedor despacha]
    │                          ↓
    │                        enviado
    │                          ↓
    │               [cliente confirma recepción]
    │                          ↓
    │                       entregado
    │
    └──[cancelación o expiración]──→ cancelado
                                     + expired=True (si fue por TTL)
                                     + refunded=True (si aplica reembolso)
```

Cancelaciones posibles desde: `pendiente_pago`, `pago_en_revision`, `pagado`, `confirmado`.

---

### Order (Django) — 6 estados resumen (derivado automático)

`Order.status` **nunca se establece manualmente**. Siempre se calcula a partir del
conjunto de estados de sus SubOrders (ver sección 11).

| `Order.status` | Significado para el cliente | Condición derivada |
|---|---|---|
| `pendiente_pago` | Al menos una SubOrder sin pagar | Alguna SubOrder en `pendiente_pago` o `pago_en_revision` |
| `pagado` | Todas las SubOrders activas pagadas | Todas en `pagado` (ninguna pendiente) |
| `procesando` | Al menos una SubOrder confirmada en Odoo | Alguna en `confirmado` |
| `enviado` | Al menos una SubOrder despachada | Alguna en `enviado` |
| `completado` | Todas las SubOrders entregadas | Todas activas en `entregado` |
| `cancelado` | Todas las SubOrders canceladas | Todas en `cancelado` |

> ⚠️ **Granularidad multiproveedor:** cuando hay 3 proveedores y solo 2 enviaron,
> `Order.status = 'enviado'` pero el cliente puede ver el estado individual de cada
> SubOrder en el historial. El resumen de Order solo sirve para filtros y notificaciones.

---

### Mapeo SubOrder.status → campo Odoo `x_payment_status`

| `SubOrder.status` | `x_payment_status` en Odoo |
|---|---|
| `pendiente_pago` | — (no existe en Odoo) |
| `pago_en_revision` | — (no existe en Odoo) |
| `pagado` | `'confirmado'` |
| `confirmado` | `'confirmado'` |
| `enviado` | `'confirmado'` |
| `entregado` | `'confirmado'` |

---

## 6️⃣ Arquitectura de conexión Django ↔ Odoo (post-pago)

```
Django (Celery worker)  ← se activa SOLO cuando SubOrder.status = 'pagado'
    │
    ├── apps/orders/tasks.py
    │       └── create_odoo_sale_order(sub_order_id)
    │               │
    │               └── apps/orders/signals.py
    │                       └── sync_suborder_to_odoo(suborder)
    │                               │
    │                               └── apps/sync/odoo_connector.py
    │                                       └── OdooConnector (XML-RPC)
    │                                               └── Odoo (http://odoo:8069)
    │                                                   ├── res.partner
    │                                                   └── sale.order (draft)
    │
    ├── apps/orders/tasks.py
    │       └── update_suborder_payment_status(sub_order_id)
    │               └── Solo actualiza campos x_ de una sale.order YA existente
    │
    └── Webhook / polling Odoo→Django  ← 🔲 PENDIENTE (Paso G)
            └── sale.order.state = 'sale'    → SubOrder = 'confirmado'
            └── stock.picking.state = 'done' → SubOrder = 'enviado'/'entregado'

Tarea periódica (Celery beat):
    └── expire_pending_suborders()  ← cada 15 min
            └── SubOrder.status='pendiente_pago' AND Order.payment_deadline < now()
                → SubOrder.status = 'cancelado', SubOrder.expired = True
```

**Protocolo:** XML-RPC — puerto 8069
**Autenticación:** credentials en `settings.ODOO_CONFIG`
**Base de datos Odoo:** `ecomparts_odoo_shared` (compartida para todas las companies)

### Idempotencia y lock distribuido en Celery

La idempotencia actual bloquea la re-creación si `odoo_sale_id` ya existe:

```python
if suborder.odoo_sale_id:
    return suborder.odoo_sale_id   # ya existe, no crear de nuevo
```

Pero en escenarios de retry simultáneo (worker 1 y worker 2 ejecutando la misma tarea),
ambos pueden pasar el `if` antes de que el primero confirme. **Solución de doble protección:**

1. **En Django:** usar `select_for_update()` al leer la SubOrder al inicio de la tarea.
2. **En Odoo:** definir `unique=True` en `x_marketplace_suborder_id` en el modelo `sale.order`.
   Odoo rechazará el segundo `create` con un error que Celery puede capturar sin reintentar.

```python
# En el módulo orders_odoo (Odoo):
x_marketplace_suborder_id = fields.Char(
    "SubOrder Marketplace ID",
    index=True,
    copy=False,
    # Restricción SQL de unicidad:
)
_sql_constraints = [
    ('unique_marketplace_suborder',
     'UNIQUE(x_marketplace_suborder_id)',
     'Ya existe una sale.order para esta SubOrder del marketplace.')
]
```

La tarea Celery tiene `max_retries=3` con `countdown=300` (5 min entre reintentos),
pero un `IntegrityError` de Odoo **no debe reintentar** → capturar y marcar `odoo_sync_error=True`.

---

## 7️⃣ Cancelaciones, rechazos y reembolsos — análisis con Odoo

### Escenario 1 — Cancelación antes de confirmar pago

**Sub-escenario 1.1 — TTL vencido (`pendiente_pago` + deadline expirado)**
- El cliente no pagó en las 3 horas → Celery marca `SubOrder.status = 'cancelado'`, `expired = True`.
- **Odoo:** No existe ningún registro. No hay nada que hacer.
- `Order.status` se recalcula. Si otras SubOrders siguen activas, la Order no se cancela.

**Sub-escenario 1.2 — Cancelación con comprobante en revisión (`pago_en_revision`)**
- El cliente solicita cancelar (contacta al proveedor o usa endpoint de cancelación).
- El trato es equivalente al Escenario 2 si existe `odoo_sale_id`, o igual al 1.1 si no.
- **Implementación:** endpoint `POST /api/orders/suborders/{id}/cancel/` (admin / cliente).
- **Django:** `SubOrder.status → 'cancelado'`.
- **Odoo:** No existe registro → nada que hacer.

### Escenario 2 — Cancelación tras `pagado` (sale.order en `draft` en Odoo)
- La `sale.order` existe en Odoo en estado `draft`.
- **Odoo:** Llamar `sale.order.action_cancel()` vía XML-RPC → estado `cancel`.
- **Campo Odoo:** `x_is_cancelled = True`.
- **Django:** `SubOrder.status → 'cancelado'`.
- Si el pago ya fue realizado → iniciar reembolso (Escenario 4) + `SubOrder.refunded = True`.

### Escenario 3 — Cancelación tras `confirmado` (sale.order en `sale` en Odoo)
- El stock ya fue reservado. Cancelar es más costoso.
- **Odoo:** `sale.order.action_cancel()` solo funciona si **no hay picking validado**.
  - Si hay picking sin validar: cancelar picking primero → luego cancelar `sale.order`.
  - Si el picking ya fue validado (mercancía despachada): solo se puede reembolsar.
- **Campo Odoo a consultar:** `picking_ids.state` — si alguno es `'done'`, la cancelación es imposible.
- **Django:** Decisión case-by-case (requiere intervención de admin).

### Escenario 4 — Reembolso
Odoo no tiene un flujo automático de reembolso vinculado al marketplace. Opciones:

| Opción | Mecanismo Odoo | Complejidad |
|---|---|---|
| **Nota de crédito** | `account.move` de tipo `out_refund` contra la factura original | Media |
| **Devolución de picking** | `stock.return.picking` → nuevo picking inverso | Media |
| **Registro manual** | Admin registra el reembolso y lo marca en Django | Baja |

**Recomendación corto plazo:** gestión manual + campo `SubOrder.refund_notes` en Django.
Los reembolsos digitales (Yape/Plin/transferencia) se procesan fuera del sistema; Django
registra el resultado con `SubOrder.refunded = True` y `SubOrder.refund_notes`.

**Campo Odoo para detectar reembolso:** si se genera una nota de crédito,
`account.move.reversal_move_id` existirá. Puede usarse en un futuro webhook para
activar `SubOrder.refunded = True` automáticamente.

---

## 8️⃣ Casos poco frecuentes (edge cases) en compra y despacho

### Pagos parciales en compra multiproveedor

| Caso | Descripción | Solución propuesta |
|---|---|---|
| **A. Paga a un proveedor, abandona los otros** | `SubOrder-A = pagado`, `SubOrder-B = pendiente_pago` | Cada SubOrder tiene su propio ciclo de vida. SubOrder-B expira por TTL (`cancelado + expired=True`). SubOrder-A ya fue a Odoo. La Order permanece activa (no se cancela completa). |
| **B. Comprobante rechazado en una SubOrder** | Proveedor rechaza; otra SubOrder ya está en Odoo | `PaymentTransaction.status = 'rejected'`, `SubOrder.payment_rejected = True`, `SubOrder.status → 'pendiente_pago'`. El cliente ve el aviso de rechazo y sube un nuevo comprobante. No afecta las demás SubOrders. |
| **C. Un proveedor cancela su parte después del pago** | Solo esa SubOrder se cancela | Reembolso parcial (`SubOrder.refunded = True`, manual por ahora). `Order.status` no cambia a `cancelado` si otras SubOrders siguen activas. |
| **D. Race condition de stock en compra simultánea** | Dos clientes pasan el mismo producto al mismo tiempo | El serializer valida `total_stock >= quantity` en el POST. El segundo checkout fallará si el primero ya hizo commit. Mitigación futura: `select_for_update()` en StockItem. |

### Casos operativos

| Caso | Descripción | Solución propuesta |
|---|---|---|
| **E. Proveedor no responde la confirmación** | SubOrder en `pago_en_revision` indefinidamente | Alerta automática a admin después de 24 h. Opción de confirmación manual desde panel admin. |
| **F. Error definitivo de conexión con Odoo** | Celery agota `max_retries=3` | Marcar `SubOrder.odoo_sync_error = True`. Admin resuelve con endpoint `retry_odoo_sync`. |
| **G. Producto sin `odoo_product_id`** | `sync_suborder_to_odoo` lanza `ValueError` | Celery no reintenta. Admin sincroniza el producto y ejecuta `retry_odoo_sync`. |
| **H. Cliente no confirma entrega** | SubOrder en `enviado` indefinidamente | Auto-marcar `entregado` después de N días desde `shipped_at` (ej: 15 días). |
| **I. Mercancía dañada al recibirla** | `entregado` pero con reclamo | Flujo de reclamo post-entrega: campo `SubOrder.claim_status` (pendiente diseño). |
| **J. Tracking incorrecto ingresado por proveedor** | Cliente no puede rastrear | Proveedor puede editar `tracking_number` mientras `status != 'entregado'`. |
| **K. Recojo en tienda no realizado** | SubOrder en `confirmado` indefinidamente | Auto-cancelar después de N días. Es un asunto interno entre proveedor y cliente; el marketplace no necesita involucrarse. |

---

## 9️⃣ Módulo Odoo `orders_odoo` — campos recomendados (versión corregida)

```python
# Referencia cruzada
x_marketplace_order_id    = fields.Char("Order Marketplace ID")
x_marketplace_suborder_id = fields.Char(
    "SubOrder Marketplace ID",
    index=True,
    copy=False,
)  # ← unique constraint vía _sql_constraints (ver sección 6)

# Entrega
x_delivery_method  = fields.Char("Método de Entrega")
x_delivery_address = fields.Text("Dirección de Entrega")
x_customer_notes   = fields.Text("Notas del Cliente")

# Estado de pago — solo 'confirmado' llega a Odoo
x_payment_status = fields.Selection([
    ('confirmado', 'Pago Confirmado'),
], "Estado de Pago Marketplace")

x_payment_method   = fields.Char("Método de Pago")
x_payment_reference = fields.Char("N° Operación")

# Flags booleanos
x_is_payment_confirmed = fields.Boolean("Pago Confirmado")
x_is_order_confirmed   = fields.Boolean("Cotización Confirmada")
x_is_order_shipped     = fields.Boolean("Despachado")
x_is_order_delivered   = fields.Boolean("Entregado")
x_is_cancelled         = fields.Boolean("Cancelado desde Marketplace")

# Sincronización
x_last_sync_at = fields.Datetime("Última sincronización Django")
```

> **Eliminados respecto a versiones anteriores:** `x_is_payment_uploaded`,
> `x_is_payment_rejected`, `x_requires_manual_approval`, `x_payment_rejection_reason`,
> `x_payment_amount_declared` — ya no aplican porque Odoo nunca recibe órdenes sin pago
> confirmado y los rechazos se gestionan en Django mediante flags.

---

## 🔟 Correcciones y mejoras al app `orders`

### models/order.py

```python
STATUS_CHOICES = [
    ('pendiente_pago', 'Pendiente de Pago'),
    ('pagado',         'Pagado'),
    ('procesando',     'Procesando'),
    ('enviado',        'Enviado'),
    ('completado',     'Completado'),   # antes 'entregado'
    ('cancelado',      'Cancelado'),
]
# Order.status NUNCA se establece manualmente. Siempre se deriva de las SubOrders
# mediante la función update_order_status() (ver sección 11).

# Campo TTL para expiración de SubOrders pendientes:
payment_deadline = models.DateTimeField(
    null=True, blank=True,
    help_text="Plazo máximo de pago (created_at + 3h). Las SubOrders pendientes expiran al vencer."
)
```

### models/sub_order.py

```python
STATUS_CHOICES = [
    ('pendiente_pago',   'Pendiente de Pago'),
    ('pago_en_revision', 'Pago en Revisión'),
    ('pagado',           'Pagado'),
    ('confirmado',       'Confirmado'),
    ('enviado',          'Enviado'),
    ('entregado',        'Entregado'),
    ('cancelado',        'Cancelado'),
]

# Flags de auditoría y estado excepcional (reemplazan estados extra):
payment_rejected       = models.BooleanField(default=False,
    help_text="True si el último comprobante fue rechazado por el proveedor.")
expired                = models.BooleanField(default=False,
    help_text="True si el status=cancelado fue causado por vencimiento del TTL.")
refunded               = models.BooleanField(default=False,
    help_text="True si se procesó un reembolso para esta SubOrder.")

# Trazabilidad:
odoo_sync_error        = models.BooleanField(default=False)
odoo_sync_error_detail = models.TextField(blank=True)
shipped_at             = models.DateTimeField(null=True, blank=True)
delivered_at           = models.DateTimeField(null=True, blank=True)
refund_notes           = models.TextField(blank=True)
```

### models/payment_transaction.py — NUEVO (reemplaza PaymentProof)

El modelo `PaymentTransaction` separa completamente la gestión de pagos de la SubOrder.
Permite múltiples intentos, historial completo y auditoría antifraude.

```python
from django.conf import settings
from django.db import models


class PaymentTransaction(models.Model):
    """
    Registro de cada intento de pago contra una SubOrder.
    Una SubOrder puede tener múltiples PaymentTransactions (reintentos tras rechazo).
    Solo una puede estar en status='approved' a la vez.
    """

    STATUS_CHOICES = [
        ('uploaded', 'Comprobante Subido'),
        ('approved', 'Aprobado'),
        ('rejected', 'Rechazado'),
    ]

    METHOD_CHOICES = [
        ('yape',          'Yape'),
        ('plin',          'Plin'),
        ('transferencia', 'Transferencia Bancaria'),
    ]

    suborder = models.ForeignKey(
        'SubOrder',
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    operation_number = models.CharField(max_length=100)
    proof_file = models.ImageField(upload_to='payment_proofs/')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='uploaded',
    )
    rejection_reason = models.TextField(blank=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_payments',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_payments',
    )

    created_at  = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PaymentTxn #{self.pk} — {self.suborder.sub_order_number} [{self.status}]"
```

### views.py — cambios requeridos

| Método | Cambio |
|---|---|
| `create_order` | **Eliminar** `transaction.on_commit → _enqueue_odoo_sale_order`. Agregar `payment_deadline = now() + 3h`. |
| `upload_payment` (nuevo nombre) | Crear `PaymentTransaction`. Actualizar `SubOrder.status → 'pago_en_revision'`, limpiar `payment_rejected`. |
| `review_payment` (nuevo nombre) | En aprobación: `PaymentTransaction.status='approved'`, `SubOrder.status → 'pagado'`, encolar Celery. En rechazo: `PaymentTransaction.status='rejected'`, `SubOrder.status → 'pendiente_pago'`, `payment_rejected=True`. |
| **NUEVO** `cancel_suborder` | Cancelar SubOrder. XML-RPC a Odoo si `odoo_sale_id` existe. |
| **NUEVO** `retry_odoo_sync` | Reencolar `create_odoo_sale_order` para admin. Limpia `odoo_sync_error`. |

### tasks.py — cambios requeridos

| Tarea | Cambio |
|---|---|
| `create_odoo_sale_order` | En fallo definitivo: `SubOrder.odoo_sync_error = True`, guardar detalle. No reintentar en `IntegrityError` de Odoo (constraint única). |
| **NUEVA** `expire_pending_suborders` | Celery beat, cada 15 min. Expira SubOrders en `pendiente_pago` con `order.payment_deadline < now()`. |
| **NUEVA** `auto_deliver_shipped_orders` | Opcional: auto-`entregado` después de N días desde `shipped_at`. |

### signals.py — `_PAYMENT_STATUS_MAP` actualizado

```python
# Solo los estados que efectivamente llegan a Odoo:
_PAYMENT_STATUS_MAP = {
    'pagado':     'confirmado',
    'confirmado': 'confirmado',
    'enviado':    'confirmado',
    'entregado':  'confirmado',
}
```

---

## 1️⃣1️⃣ Agregación automática de `Order.status` (derivado de SubOrders)

`Order.status` **nunca se escribe directamente**. Se calcula a partir de las SubOrders
activas (excluyendo las canceladas) mediante una función utilitaria llamada desde un
signal `post_save` en SubOrder.

```python
def update_order_status(order):
    """
    Calcula y guarda Order.status basándose en el conjunto de SubOrders activas.
    Las SubOrders canceladas no bloquean el progreso de las demás.
    """
    suborders = order.sub_orders.all()
    active = suborders.exclude(status='cancelado')

    if not active.exists():
        # Todas canceladas
        new_status = 'cancelado'

    elif active.filter(status='entregado').count() == active.count():
        new_status = 'completado'

    elif active.filter(status__in=['enviado', 'entregado']).exists():
        new_status = 'enviado'

    elif active.filter(status__in=['confirmado', 'enviado', 'entregado']).exists():
        new_status = 'procesando'

    elif active.filter(status__in=['pagado', 'confirmado', 'enviado', 'entregado']).count() == active.count():
        new_status = 'pagado'

    else:
        # Al menos una SubOrder activa en pendiente_pago o pago_en_revision
        new_status = 'pendiente_pago'

    if order.status != new_status:
        Order.objects.filter(pk=order.pk).update(status=new_status)
```

```python
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=SubOrder)
def recalculate_order_status(sender, instance, **kwargs):
    update_order_status(instance.order)
```

> 💡 **Por qué excluir `cancelado` de `active`:** permite que SubOrder-A siga
> avanzando a `pagado → confirmado → enviado → entregado` aunque SubOrder-B esté
> `cancelado (expired=True)`. La Order solo pasa a `cancelado` cuando **todas**
> las SubOrders (incluyendo las canceladas) ya no tienen actividad pendiente.

---

## 1️⃣2️⃣ Roadmap de implementación — v3

### ✅ Completado
- [x] `POST /api/orders/orders/create_order/` — crea `Order` + `SubOrder` + items
- [x] `sync_suborder_to_odoo` con todos los campos del módulo `orders_odoo`
- [x] Búsqueda de partner por email → vat → crear
- [x] `ValueError` explícito si no hay `odoo_product_id`
- [x] Frontend: historial de compras `/cliente/historial-compras`
- [x] Frontend: detalle de orden `/cliente/historial-compras/[id]`

### 🔲 Paso 1 — Corrección crítica: desacoplar Odoo de la creación de orden
- [ ] Eliminar `transaction.on_commit → _enqueue_odoo_sale_order` en `create_order`
- [ ] Agregar `payment_deadline = now() + 3h` en `create_order`
- [ ] Crear migración Django

### 🔲 Paso 2 — Rediseño de estados y flags (migración de modelo)

**SubOrder:**
- [ ] Renombrar `pago_pendiente_confirmacion` → `pago_en_revision`
- [ ] Renombrar `pagado_confirmado` → `pagado`
- [ ] Renombrar `confirmada` → `confirmado`
- [ ] Eliminar estados: `pago_rechazado`, `expirada`, `reembolsada`
- [ ] Agregar flags: `payment_rejected`, `expired`, `refunded`
- [ ] Agregar campos: `odoo_sync_error`, `odoo_sync_error_detail`, `shipped_at`, `delivered_at`, `refund_notes`

**Order:**
- [ ] Simplificar a 6 estados: `pendiente_pago`, `pagado`, `procesando`, `enviado`, `completado`, `cancelado`
- [ ] Eliminar estados: `pago_revision`, `expirada`, `reembolsado`
- [ ] Crear y aplicar migración Django

### 🔲 Paso 3 — Modelo PaymentTransaction (reemplaza PaymentProof)
- [ ] Crear `apps/orders/models/payment_transaction.py` con el modelo definido en §10
- [ ] Migrar datos existentes de `PaymentProof` → `PaymentTransaction` si los hay
- [ ] Nuevo endpoint `upload_payment` (reemplaza `upload_payment_proof`)
- [ ] Nuevo endpoint `review_payment` (reemplaza `confirm_payment`)
- [ ] Actualizar serializers y admin
- [ ] Actualizar frontend: formulario de subida y UI de revisión de pago

### 🔲 Paso 4 — Expiración automática por SubOrder
- [ ] Implementar tarea `expire_pending_suborders` en `tasks.py`
- [ ] Registrar en Celery beat schedule (cada 15 min)
- [ ] Frontend: countdown en Paso 4 y en detalle de orden (por SubOrder, no por Order)
- [ ] Frontend: manejo de respuesta `410 Gone` del backend para SubOrder específica

### 🔲 Paso 5 — Agregación automática de `Order.status`
- [ ] Implementar función `update_order_status(order)` y signal `recalculate_order_status`
- [ ] Eliminar toda escritura manual de `Order.status` en views y tasks
- [ ] Tests unitarios para todas las combinaciones de estados multiproveedor

### 🔲 Paso 6 — Idempotencia Odoo: constraint único
- [ ] Agregar `_sql_constraints` con `UNIQUE(x_marketplace_suborder_id)` en módulo Odoo
- [ ] Actualizar tarea Celery para no reintentar en `IntegrityError` de Odoo
- [ ] Agregar `select_for_update()` en la lectura de SubOrder al inicio de la tarea

### 🔲 Paso 7 — Webhook / polling Odoo → Django
- [ ] Definir mecanismo (webhook desde módulo Odoo o polling periódico Django)
- [ ] `sale.order.state = 'sale'` → `SubOrder.status = 'confirmado'`
- [ ] `stock.picking.state = 'done'` → `SubOrder.status = 'enviado'` / `'entregado'`

### 🔲 Paso 8 — Cancelaciones y reembolsos
- [ ] Endpoint `cancel_suborder` con lógica diferenciada según `odoo_sale_id` y estado Odoo
- [ ] Llamada XML-RPC a `sale.order.action_cancel()` cuando aplica
- [ ] Flujo de reembolso manual: `SubOrder.refunded = True` + `SubOrder.refund_notes`

### 🔲 Paso 9 — Panel del proveedor en frontend
- [ ] Lista de SubOrders pendientes de confirmación de pago
- [ ] Acción aprobar / rechazar pago (con `rejection_reason`)
- [ ] Acción ingresar tracking number
- [ ] Link directo a la `sale.order` en Odoo
- [ ] Vista de `PaymentTransaction` con historial de intentos
