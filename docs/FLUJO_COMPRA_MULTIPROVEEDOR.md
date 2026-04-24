# Flujo de Compra Multiproveedor — ECOMPARTS Marketplace
> Documentación técnica basada en el código real del proyecto
> **Última revisión:** 24 de abril de 2026 — v5.1: auditoría de arquitectura real `orders` ↔ `sync`, endpoints vigentes y brechas abiertas

---

## 1️⃣ Principio rector

| Actor | Responsabilidad |
|---|---|
| **SvelteKit (Frontend)** | Inicia acciones, muestra estados y gestiona la sesión de checkout (TTL 3 h). No calcula reglas de negocio. |
| **Django (Marketplace)** | Orquesta todo el negocio: crea órdenes, gestiona pagos, expira reservas, decide cuándo integrar con Odoo. |
| **Odoo** | Recibe una `sale.order` en `draft` cuando el cliente sube el comprobante, y desde ahí el proveedor revisa el pago y continúa el flujo ERP. |
| **Celery** | Ejecuta la integración Django→Odoo de forma asíncrona (no bloquea al cliente). También ejecuta el job de expiración de órdenes pendientes. |

> ⚠️ **Estado real del código:** Odoo recibe la `SubOrder` cuando pasa a `pago_en_revision`.
> La `sale.order` se crea en `draft` tras subir el comprobante; la aprobación o rechazo ocurre después en Odoo.
> Django es el único orquestador del flujo completo.

## 1.1 Estado real del código al 24 de abril de 2026

### División actual de responsabilidades

- `apps/orders` sigue siendo el dueño del dominio: modelos, serializers, endpoints REST, webhooks Odoo→Django y tareas Celery del flujo de compra.
- `apps/sync` absorbió la infraestructura de integración con Odoo: conector y servicio `apps/sync/services/orders.py` para crear o actualizar `sale.order`.
- `apps/orders/signals.py` ya no contiene la lógica de Odoo; hoy re-exporta funciones desde `apps/sync/services/orders.py` para mantener compatibilidad con imports antiguos.

### Endpoints reales hoy en producción

- `POST /api/v1/orders/orders/checkout-preview/`
- `POST /api/v1/orders/orders/create_order/`
- `POST /api/v1/orders/orders/upload_payment_proof/`
- `POST /api/v1/orders/suborders/{id}/mark-received/`
- `POST /api/v1/orders/odoo-webhook/sale-order-update/`
- `POST /api/v1/orders/odoo-webhook/delivery-update/`
- `POST /api/v1/orders/odoo-webhook/review-payment/`
- `POST /api/v1/orders/odoo-webhook/mark-received/`

### Tareas periódicas activas

- `apps.orders.tasks.expire_pending_suborders` cada 15 min.
- `apps.orders.tasks.reconcile_suborders_pending_odoo` cada 10 min.

### Conclusión arquitectónica actual

- La separación `orders = dominio` y `sync = infraestructura` es razonable y consistente.
- La migración a `sync` no dejó obsoleto a `orders`: el flujo de compra sigue necesitando orquestación de negocio en `orders`.
- El flujo está operativo, pero no puede considerarse completamente cerrado: hay endpoints legacy, stubs sin implementar y cobertura automatizada mínima.

---

## 2️⃣ Decisión crítica de arquitectura: roles Django ↔ Odoo

La experiencia final que queremos es:

- **Django/Svelte** controlan todo el flujo de checkout del cliente y los estados
    de negocio de la `SubOrder` (`pendiente_pago`, `pago_en_revision`, `confirmado`, etc.).
- **Odoo** es el lugar de trabajo del proveedor: allí revisa el comprobante,
    puede **rechazarlo** indicando un motivo o **confirmar la cotización** usando
    el botón estándar "Confirmar" (cotización → orden de venta).

La secuencia correcta es ahora:

```
Order creada → SubOrder creada → (espera pago)
                                                                ↓
                                     Cliente sube comprobante (PaymentProof.uploaded)
                                                                ↓
                                         🔥 Celery → crear sale.order en Odoo (draft)
                                                                ↓
                        Proveedor revisa pago en Odoo (pestaña Marketplace)
                                                                ↓
            [Rechazar pago]                    [Confirmar]
                        ↓                                  ↓
    x_payment_status='rechazado'      sale.order.state='sale'
    notifica a Django →               notifica a Django →
    PaymentProof.rejected            PaymentProof.approved
    SubOrder.status='pago_rechazado' SubOrder.status='confirmado'
```

**Motivos del rediseño v4:**

- Evitar duplicar máquinas de estados: en Odoo seguimos usando los estados
    nativos (`draft`, `sale`, `done`, `cancel`) y solo añadimos un
    `x_payment_status` muy reducido (`pendiente_revision`, `aprobado`, `rechazado`).
- Centralizar la operación del proveedor en un solo lugar (Odoo), sin
    obligarlo a usar un panel separado en Django para revisar el pago.
- Mantener a Django como **fuente de verdad** de los estados de `SubOrder`,
    pero dejando que Odoo dispare los eventos clave (confirmar / rechazar pago,
    confirmar cotización).

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
  - Las SubOrders de otros proveedores que ya están en `confirmado` o superior no se ven afectadas.
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
> Si la SubOrder-A ya está en `confirmado` y la SubOrder-B sigue en `pendiente_pago`,
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

**Endpoint real:** `POST /api/v1/orders/orders/upload_payment_proof/`

Se crea un objeto `PaymentProof` (modelo actual de Django, ver código en
`apps/orders/models/payment_proof.py`):

```python
# Se crea un nuevo PaymentProof ligado a la SubOrder
PaymentProof.sub_order        = sub_order
PaymentProof.amount           = 350.00
PaymentProof.payment_method   = 'yape' | 'plin' | 'transferencia'
PaymentProof.operation_number = '123456789'
PaymentProof.file             = <imagen>
PaymentProof.status           = 'uploaded'
PaymentProof.uploaded_by      = request.user

# Estado de la SubOrder actualizado:
SubOrder.status          → 'pago_en_revision'
SubOrder.payment_rejected = False  # limpiar flag si era un reintento
```

> `Order.status` se recalcula automáticamente vía signal al guardar la SubOrder.

> **En este punto sí se encola la tarea Celery hacia Odoo** para crear la
> `sale.order` en estado `draft` con toda la información de Marketplace.

#### Paso D3 — Confirmación inline (fin del paso 4)
Una vez subido al menos un comprobante por SubOrder, el frontend muestra la confirmación
con `order_number` y botones "Ver mis pedidos" / "Seguir comprando".

> El cliente puede subir nuevos comprobantes si el proveedor rechaza uno previo
> (ver Paso E2). No se necesita un endpoint distinto; se crea una nueva `PaymentTransaction`.

---

### 🏢 E. Revisión del comprobante (proveedor en Odoo)

La revisión ya **no se hace en un panel propio de Django**, sino directamente en
Odoo sobre la `sale.order` creada en el paso anterior. Toda la información de pago
(método, monto, número de operación, imagen del comprobante) se muestra en la
pestaña **Marketplace** del formulario de pedido.

El módulo `orders_odoo` expone dos acciones principales:

- Botón **Rechazar pago** (visible mientras `state = 'draft'`):
    - Se abre un cuadro para capturar `x_payment_rejection_reason`.
    - Pone `x_payment_status = 'rechazado'` en la `sale.order`.
    - Llama a Django mediante `POST /api/v1/orders/odoo-webhook/review-payment/`
        con `action='reject'`.
    - Django actualiza el último `PaymentProof`:

        ```python
        PaymentProof.status           → 'rejected'
        PaymentProof.rejection_reason → x_payment_rejection_reason
        PaymentProof.verified_at      → now()

        SubOrder.status          → 'pago_rechazado'
        SubOrder.payment_rejected = True
        ```

    - El frontend vuelve a habilitar el formulario para que el cliente corrija
        el comprobante.

- Botón estándar **Confirmar** de Odoo (cotización → orden de venta):
    - Odoo cambia `sale.order.state` de `draft` a `sale`.
    - El módulo `orders_odoo` intercepta `action_confirm` para:

        ```python
        x_payment_status = 'aprobado'
        # Llamada a Django
        review_payment(suborder_number, action='approve')  # vía HTTP webhook

        PaymentProof.status      → 'approved'
        PaymentProof.verified_at → now()

        SubOrder.status       → 'confirmado'
        SubOrder.confirmed_at → now()
        ```

    - En este diseño **no existe ya el estado `pagado`** como etapa intermedia;
        la aprobación del pago y la confirmación de la cotización ocurren en la
        misma acción de Odoo.

> 🔑 En el código actual, `payment_rejected` es un flag complementario pero el
> rechazo sí deja a la `SubOrder` en `pago_rechazado`. La resubida vuelve el
> flujo a `pago_en_revision` sin reactivar el TTL.

---

### 🧾 F. Creación de `sale.order` en Odoo (tras subir comprobante)

**Función real:** `sync_suborder_to_odoo(suborder)` — `apps/sync/services/orders.py`
**Compatibilidad:** `apps/orders/signals.py` re-exporta esta función para no romper imports antiguos.
**Protocolo real:** JSON-RPC vía `apps/sync/odoo_connector.py` — puerto 8069

> Se ejecuta **cuando la SubOrder entra en `pago_en_revision`**, es decir, tras
> la subida de un `PaymentProof` válido. Odoo crea una cotización en estado
> `draft` que el proveedor podrá confirmar o usar para rechazar el pago.

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
    # El pago aún está en revisión por el proveedor
    'x_payment_status':          'pendiente_revision',
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

> como `sale_order_update` (notificación de cambio de estado de la `sale.order`)
> son capaces de marcar el `PaymentProof` como `approved`. Ambos endpoints son
> idempotentes: solo tocan comprobantes que aún están en `uploaded`, y solo
> actualizan la `SubOrder` si el estado realmente cambió. Esto garantiza que
> el historial de pagos quede siempre consistente independientemente del orden
> de llegada de las notificaciones.

### 📦 G. Confirmación, rechazo y corrección de pago en Odoo

#### G1 — Proveedor confirma la `sale.order` en Odoo (cotización → orden de venta)
- Botón **Confirmar** en Odoo → `sale.order.state = 'sale'`.
- El módulo `orders_odoo` marca `x_payment_status = 'aprobado'` y notifica a Django
    mediante el webhook `sale-order-update` (o `review-payment`).
- Django actualiza el `PaymentProof` más reciente en estado `uploaded` →
    `approved` (con `verified_at = now()`). Si ya existía un proof en `approved`
    (porque `review-payment` llegó antes), la actualización es idempotente y no
    genera duplicados.
- `SubOrder.status → 'confirmado'`, `confirmed_at = now()`, `payment_rejected = False`.
- Odoo reserva stock automáticamente.
- `Order.status` se recalcula automáticamente vía signal (ver sección 11).

#### G2 — Proveedor rechaza el comprobante de pago en Odoo
- Botón **Rechazar pago** en Odoo → `x_payment_status = 'rechazado'`.
- El módulo notifica a Django mediante el webhook `review-payment` con `action='reject'`.
- Django actualiza el `PaymentProof` más reciente en estado `uploaded` → `rejected`.
- `SubOrder.status → 'pago_rechazado'`, `payment_rejected = True`, `rejection_reason` (motivo).
- El frontend muestra badge "Pago Rechazado" y habilita el formulario para corregir y reenviar comprobante.

#### G3 — Cliente corrige y reenvía comprobante
- Cliente sube nuevo comprobante desde checkout o historial.
- Backend crea un nuevo `PaymentProof` (o PaymentTransaction) y transiciona `SubOrder.status → 'pago_en_revision'`, `payment_rejected = False`.
- El ciclo puede repetirse hasta que el proveedor apruebe el pago.

> 📌 **Máquina de estados limpia:**
> - `pendiente_pago` → cliente aún no sube comprobante (timer activo)
> - `pago_en_revision` → comprobante subido, esperando revisión
> - `pago_rechazado` → comprobante rechazado, cliente debe corregir
> - `confirmado` → pago aprobado
> - `cancelado` → expiración o cancelación manual

#### G4 — Proveedor genera y valida el picking en Odoo
- Odoo crea un `stock.picking` al confirmar la venta.
- Ese picking representa la **transferencia de salida** (`picking_type_code = 'outgoing'`).
- El proveedor registra el número de tracking en Django (`SubOrder.tracking_number`).
- Al validar el picking en Odoo, `stock.picking.state = 'done'`.
- Eso significa **mercancía despachada / salió del inventario**, no recepción confirmada por el cliente.
- **Webhook / polling Django:** `SubOrder.status → 'enviado'`

#### G5 — Recepción confirmada por el cliente
- El cliente confirma recepción en el frontend (o el proveedor la marca manualmente).
- `SubOrder.status → 'entregado'`
- Este estado **no** debe inferirse automáticamente desde Odoo solo porque el picking quedó en `done`.
- En Odoo puede coexistir con picking validado y factura generada, pero esas acciones no sustituyen la confirmación real de recepción.

---

## 4️⃣ Expiración de SubOrders abandonadas (reserva de 3 horas)

### Objetivo
Evitar que el catálogo y las listas de órdenes se llenen de "basura" por checkouts abandonados.

### Principio de diseño: expirar por SubOrder, no por Order

Escenario multiproveedor real:

```
SubOrder-A (Proveedor A) → confirmado     ← pago aprobado, sale.order confirmada en Odoo
SubOrder-B (Proveedor B) → pendiente_pago ← el cliente abandonó este pago
SubOrder-C (Proveedor C) → confirmado     ← pago aprobado, sale.order confirmada en Odoo
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
Las condiciones excepcionales (expiración, reembolso) se representan como **flags
booleanos**. El rechazo de pago sí justifica un estado propio porque genera una
UX diferenciada (banner + formulario de corrección) y es semánticamente distinto
a `pago_en_revision`.

```
# v5: pago_rechazado es un estado explícito (no un flag)
# Permite UI diferenciada sin lógica condicional basada en flags
EXCEPCIONES COMO ESTADOS:  pago_rechazado  ← tiene UI y transición propia
EXCEPCIONES COMO FLAGS:    expired, refunded  ← eventos/auditoría sin UI diferenciada
```

---

### SubOrder (Django) — 7 estados operativos (v5)

| `SubOrder.status` | Descripción | `odoo_sale_id` | Estado en Odoo |
|---|---|---|---|
| `pendiente_pago` | Esperando comprobante del cliente (timer activo) | ❌ | — |
| `pago_en_revision` | Comprobante subido, proveedor revisando | ✅ Creado (`draft`) | `draft` |
| `pago_rechazado` | Proveedor rechazó el comprobante; cliente debe corregir | ✅ | `draft` |
| `confirmado` | Proveedor confirmó la cotización en Odoo (pago aprobado) | ✅ | `sale` |
| `enviado` | Proveedor despachó la mercancía / validó picking de salida | ✅ | `sale` + picking `done` |
| `entregado` | Cliente confirmó la recepción de la mercancía | ✅ | picking validado |
| `cancelado` | Cancelada manual o por expiración (ver flags) | ✅/❌ | `cancel` si aplica |

**Flags complementarios en SubOrder (no son estados):**

| Flag | Tipo | Significado |
|---|---|---|
| `payment_rejected` | `BooleanField` | Auditoría: el último comprobante fue rechazado (`status = pago_rechazado`). |
| `rejection_reason` | `TextField` | Motivo de rechazo del último comprobante (texto del proveedor). |
| `expired` | `BooleanField` | El `cancelado` fue causado por vencimiento del TTL. |
| `refunded` | `BooleanField` | Se procesó un reembolso para esta SubOrder. |
| `odoo_sync_error` | `BooleanField` | Error definitivo al sincronizar con Odoo. |

> 📌 En el código actual el estado se llama `entregado`, pero semánticamente significa
> **recepción confirmada**. Si más adelante se quisiera mayor claridad de UX, podría
> evaluarse renombrarlo a `recibido`; no es necesario para que el flujo sea correcto.

> Con estos flags se pueden construir vistas específicas:
> - `status=cancelado AND expired=True` → "pedidos expirados"
> - `status=cancelado AND refunded=True` → "pedidos reembolsados"
> - `status=pendiente_pago AND payment_rejected=True` → "requieren nuevo comprobante"

---

### Máquina de estados de SubOrder (v5)

```
pendiente_pago  ← timer activo
    │
    ├──[cliente sube comprobante]──→ pago_en_revision
    │                                       │
    │                          ┌────────────┴────────────┐
    │                          ↓                         ↓
    │                  [proveedor aprueba]       [proveedor rechaza]
    │                  (review-payment /          (review-payment)
    │                   sale-order-update)              ↓
    │                          ↓                 pago_rechazado      ← timer NO se reactiva
    │                       confirmado            + payment_rejected=True
    │                          ↓                 + rejection_reason
    │                [proveedor despacha]                │
    │                          ↓            [cliente corrige y reenvía]
    │                        enviado                     │
    │                          ↓                 pago_en_revision  (ciclo limpio)
    │               [cliente confirma recepción]
    │                          ↓
    │                       entregado
    │
    └──[cancelación o expiración]──→ cancelado
                                     + expired=True (si fue por TTL)
                                     + refunded=True (si aplica reembolso)
```

Cancelaciones posibles desde: `pendiente_pago`, `pago_en_revision`, `pago_rechazado`, `confirmado`.

---

### Order (Django) — 6 estados resumen (derivado automático)

`Order.status` **nunca se establece manualmente**. Siempre se calcula a partir del
conjunto de estados de sus SubOrders (ver sección 11).

| `Order.status` | Significado para el cliente | Condición derivada |
|---|---|---|
| `pendiente_pago` | Al menos una SubOrder sin pagar | Alguna SubOrder en `pendiente_pago` |
| `pagado` | Todos los comprobantes subidos, en revisión | Todas las SubOrders activas en `pago_en_revision` |
| `procesando` | Al menos una SubOrder aprobada por proveedor | Alguna en `confirmado`, `enviado` o `entregado` |
| `enviado` | Al menos una SubOrder despachada | Alguna en `enviado` o `entregado` |
| `completado` | Todas las SubOrders con recepción confirmada | Todas activas en `entregado` |
| `cancelado` | Todas las SubOrders canceladas | Todas en `cancelado` |

> ⚠️ **Granularidad multiproveedor:** cuando hay 3 proveedores y solo 2 despacharon,
> `Order.status = 'enviado'` pero el cliente puede ver el estado individual de cada
> SubOrder en el historial. El resumen de Order solo sirve para filtros y notificaciones.

---

### Mapeo SubOrder.status → campo Odoo `x_payment_status` (reducido)

`x_payment_status` existe solo en Odoo, como ayuda visual para el proveedor.
Se almacena y actualiza desde el módulo `orders_odoo` y **no** se edita a mano.

| `SubOrder.status` | `x_payment_status` en Odoo |
|---|---|
| `pendiente_pago` | `False` / vacío (no hay cotización aún) |
| `pago_en_revision` | `'pendiente_revision'` |
| `confirmado` | `'aprobado'` |
| `enviado` | `'aprobado'` |
| `entregado` | `'aprobado'` |
| `cancelado` | `'rechazado'` si la cancelación vino por rechazo de pago, vacío en otros casos |

---

## 6️⃣ Arquitectura de conexión Django ↔ Odoo (post-pago)

### Estado real de la arquitectura

El flujo quedó dividido así:

- `apps/orders/views.py` decide cuándo crear la orden, cuándo aceptar comprobantes y cuándo encolar trabajo.
- `apps/orders/tasks.py` conserva las tareas de negocio del checkout (`create_odoo_sale_order`, `update_suborder_payment_status`, expiración TTL y reconciliación).
- `apps/sync/services/orders.py` concentra la lógica técnica de integración con Odoo (`sale.order`, `x_payment_status`, `x_delivery_status`).

Esto significa que **no conviene mover todo a `sync`**: `sync` no debería volverse dueño del workflow del checkout, solo de la comunicación con Odoo.

```
Django (Celery worker)  ← se activa cuando SubOrder.status = 'pago_en_revision'
                          (cliente subió comprobante)
    │
    ├── apps/orders/tasks.py
    │       └── create_odoo_sale_order(sub_order_id)
    │               │
    │               └── apps/orders/signals.py  (re-export de compatibilidad)
    │                       └── sync_suborder_to_odoo(suborder)
    │                               │
    │                               └── apps/sync/services/orders.py
    │                                       └── apps/sync/odoo_connector.py
    │                                               └── OdooConnector (JSON-RPC)
    │                                               └── Odoo (http://odoo:8069)
    │                                                   ├── res.partner
    │                                                   └── sale.order (draft)
    │
    ├── apps/orders/tasks.py
    │       └── update_suborder_payment_status(sub_order_id)
    │               └── Solo actualiza campos x_ de una sale.order YA existente
    │
        └── Webhooks Odoo→Django  ← YA IMPLEMENTADOS
            └── sale.order.state = 'sale'               → SubOrder = 'confirmado'
            └── stock.picking(outgoing).state = 'done' → SubOrder = 'enviado'
            └── confirmación de recepción externa       → SubOrder = 'entregado'

Tarea periódica (Celery beat):
    └── expire_pending_suborders()  ← cada 15 min
            └── SubOrder.status='pendiente_pago' AND Order.payment_deadline < now()
                → SubOrder.status = 'cancelado', SubOrder.expired = True
```

**Protocolo:** JSON-RPC — puerto 8069
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

### Escenario 2 — Cancelación con comprobante en revisión (`pago_en_revision`, sale.order en `draft`)
- La `sale.order` ya existe en Odoo en estado `draft`.
- **Odoo:** Llamar `sale.order.action_cancel()` vía JSON-RPC → estado `cancel`.
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
| **A. Paga a un proveedor, abandona los otros** | `SubOrder-A = pago_en_revision`, `SubOrder-B = pendiente_pago` | Cada SubOrder tiene su propio ciclo de vida. SubOrder-B expira por TTL (`cancelado + expired=True`). SubOrder-A ya fue a Odoo en draft. La Order permanece activa (no se cancela completa). |
| **B. Comprobante rechazado en una SubOrder** | Proveedor rechaza; otra SubOrder ya está en Odoo | `PaymentProof.status = 'rejected'`, `SubOrder.payment_rejected = True`, `SubOrder.status → 'pago_rechazado'`. El cliente ve el aviso de rechazo y sube un nuevo comprobante. No afecta las demás SubOrders. |
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

## 9️⃣ Módulo Odoo `orders_odoo` — campos recomendados (v4)

En v4 el módulo Odoo se centra en dos cosas:

- Mostrar toda la información de Marketplace en la pestaña **Marketplace** de
    `sale.order` (solo lectura para la mayoría de campos).
- Proveer acciones claras para el proveedor: **Rechazar pago** y usar el botón
    estándar **Confirmar** para aprobar el pago y confirmar la cotización.

```python
# Referencia cruzada
x_marketplace_order_id    = fields.Char("Order Marketplace ID")
x_marketplace_suborder_id = fields.Char(
        "SubOrder Marketplace ID",
        index=True,
        copy=False,
)  # ← unique constraint vía _sql_constraints (ver sección 6)

# Entrega
x_delivery_method  = fields.Selection([...], string="Método de Entrega")
x_delivery_address = fields.Text("Dirección de Entrega")
x_customer_notes   = fields.Text("Notas del Cliente")

# Información de pago (sin lógica de cobro propia)
x_payment_method = fields.Selection([...], string="Método de Pago")
x_payment_reference = fields.Char("N° Operación / Referencia")
x_payment_amount_declared = fields.Monetary("Monto Declarado", currency_field="currency_id")

# Estado de pago reducido
x_payment_status = fields.Selection([
        ('pendiente_revision', 'Pendiente de Revisión'),
        ('aprobado',           'Pago Aprobado'),
        ('rechazado',          'Pago Rechazado'),
], string="Estado de Pago Marketplace", index=True)

x_payment_rejection_reason = fields.Text("Motivo de Rechazo de Pago")

# Sincronización
x_last_sync_at = fields.Datetime("Última sincronización Django", readonly=True)
```

Reglas de uso:

- `x_payment_status = 'pendiente_revision'` cuando Django crea/actualiza la
    `sale.order` tras recibir un `PaymentProof.uploaded`.
- Botón **Rechazar pago**:
    - Requiere llenar `x_payment_rejection_reason`.
    - Pone `x_payment_status = 'rechazado'`.
    - Llama a Django para marcar el `PaymentProof` como `rejected` y volver la
        `SubOrder` a `pendiente_pago`.
- Botón **Confirmar** (extendiendo `action_confirm`):
    - Marca `x_payment_status = 'aprobado'`.
    - Llama a Django para marcar el `PaymentProof` como `approved` y poner la
        `SubOrder` en `confirmado`.

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
    # 'pagado' eliminado en v4: el proveedor confirma desde Odoo,
    # no hay estado intermedio entre 'pago_en_revision' y 'confirmado'.
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

### models/payment_proof.py — modelo actual de pagos

El modelo `PaymentProof` actúa como un **historial de intentos de pago** contra
una `SubOrder`. Una SubOrder puede tener múltiples comprobantes (reintentos tras
rechazo). Solo uno puede estar en `status='approved'` a la vez.

Puntos clave del diseño:

- `status` tiene tres valores: `uploaded`, `approved`, `rejected`.
- Los campos (`amount`, `payment_method`, `operation_number`, `file`) se sincronizan
  hacia Odoo para que el proveedor pueda revisarlos en la pestaña Marketplace.
- Cuando el proveedor **rechaza** el pago desde Odoo, se marca el último
  `PaymentProof` como `rejected` + `rejection_reason` y la `SubOrder` pasa a
  `pago_rechazado` con `payment_rejected=True`. El timer **no se reactiva**.
  El cliente puede corregir y reenviar desde historial-compras.
- Cuando el proveedor **confirma** la cotización en Odoo, se marca el
  `PaymentProof` correspondiente como `approved` y la `SubOrder` pasa a
  `confirmado`.

### views.py — cambios requeridos

| Método | Cambio |
|---|---|
| `create_order` | **Eliminar** `transaction.on_commit → _enqueue_odoo_sale_order`. Agregar `payment_deadline = now() + 3h`. |
| `upload_payment` | Crear `PaymentProof`. Actualizar `SubOrder.status → 'pago_en_revision'`, limpiar `payment_rejected`. **Guard:** solo permite upload desde `pendiente_pago` o `pago_rechazado`. Encolar Celery solo en primera subida (idempotente en resubida). |
| `confirm_payment` (admin/fallback) | Aprueba el último PaymentProof y pone `SubOrder.status → 'confirmado'`. En v5 el flujo principal viene desde Odoo, pero este endpoint sigue activo para admin. |
| **NUEVO** `review_payment` (OdooWebhook) | Llamado por Odoo. `action='approve'` → PaymentProof.approved + SubOrder.confirmado. `action='reject'` → PaymentProof.rejected + **SubOrder.pago_rechazado** + payment_rejected=True. |
| **NUEVO** `cancel_suborder` | Cancelar SubOrder. JSON-RPC a Odoo si `odoo_sale_id` existe. |
| **NUEVO** `retry_odoo_sync` | Reencolar `create_odoo_sale_order` para admin. Limpia `odoo_sync_error`. |

### tasks.py — cambios requeridos

| Tarea | Cambio |
|---|---|
| `create_odoo_sale_order` | En fallo definitivo: `SubOrder.odoo_sync_error = True`, guardar detalle. No reintentar en `IntegrityError` de Odoo (constraint única). |
| **NUEVA** `expire_pending_suborders` | Celery beat, cada 15 min. Expira SubOrders en `pendiente_pago` con `order.payment_deadline < now()`. |
| **NUEVA** `auto_deliver_shipped_orders` | Opcional: auto-`entregado` después de N días desde `shipped_at`. |

### signals.py — `_PAYMENT_STATUS_MAP` (v5)

```python
# Solo los estados que tienen sale.order en Odoo.
# x_payment_status tiene 3 valores: pendiente_revision, aprobado, rechazado.
_PAYMENT_STATUS_MAP = {
    'pago_en_revision': 'pendiente_revision',  # draft en Odoo
    'pago_rechazado':   'rechazado',            # v5: evita sobreescribir el rechazo de Odoo
    'confirmado':       'aprobado',             # cotización confirmada
    'enviado':          'aprobado',
    'entregado':        'aprobado',
    'cancelado':        'cancelado',
}
# La resubida (pago_rechazado → pago_en_revision) sincroniza automáticamente
# x_payment_status → 'pendiente_revision' via el signal post_save.
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
> avanzando a `confirmado → enviado → entregado` aunque SubOrder-B esté
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

### 🔲 Paso 1 — TTL y expiración
- [x] Agregar `payment_deadline = now() + 3h` en `create_order`
- [x] Crear migración Django

### 🔲 Paso 2 — Rediseño de estados y flags (migración de modelo)

**SubOrder (implementado en v4 — migración 0005):**
- [x] Renombrar `pago_pendiente_confirmacion` → `pago_en_revision`
- [x] ~~`pagado_confirmado` → `pagado`~~ → eliminado directamente en v4 (SubOrders pasan de `pago_en_revision` a `confirmado` sin estado intermedio)
- [x] Renombrar `confirmada` → `confirmado`
- [x] Eliminar estados: `pago_rechazado`, `expirada`, `reembolsada`
- [x] Agregar flags: `payment_rejected`, `expired`, `refunded`
- [x] Agregar campos: `odoo_sync_error`, `odoo_sync_error_detail`, `shipped_at`, `delivered_at`, `refund_notes`

**Order:**
- [x] 6 estados: `pendiente_pago`, `pagado` (todas en revisión), `procesando`, `enviado`, `completado`, `cancelado`
- [x] Eliminar estados: `pago_revision`, `expirada`, `reembolsado`
- [x] Migración Django creada y aplicada

### 🔲 Paso 3 — Consolidar modelo PaymentProof
- [x] Revisar `apps/orders/models/payment_proof.py` para asegurar que contiene
    `status` (`uploaded`, `approved`, `rejected`) y los campos necesarios.
- [x] Endpoint `upload_payment` usa PaymentProof y pone la SubOrder en
    `pago_en_revision`.
- [x] Endpoint `review_payment` se usa ahora desde Odoo (botones del módulo
    `orders_odoo`), no desde un panel proveedor en Django.
- [x] Actualizar serializers y admin
- [x] Actualizar frontend: formulario de subida y manejo de rechazos

### 🔲 Paso 4 — Expiración automática por SubOrder
- [x] Implementar tarea `expire_pending_suborders` en `tasks.py`
- [x] Registrar en Celery beat schedule (cada 15 min)
- [ ] Frontend: countdown en Paso 4 y en detalle de orden (por SubOrder, no por Order)
- [ ] Frontend: manejo de respuesta `410 Gone` del backend para SubOrder específica

### 🔲 Paso 5 — Agregación automática de `Order.status`
- [x] Implementar función `update_order_status(order)` y signal `recalculate_order_status`
- [x] Eliminar toda escritura manual de `Order.status` en views y tasks
- [ ] Tests unitarios para todas las combinaciones de estados multiproveedor

### 🔲 Paso 6 — Idempotencia Odoo: constraint único
- [ ] Agregar `_sql_constraints` con `UNIQUE(x_marketplace_suborder_id)` en módulo Odoo
- [x] Actualizar tarea Celery para no reintentar en `IntegrityError` de Odoo
- [x] Agregar `select_for_update()` en la lectura de SubOrder al inicio de la tarea


### ✅ Paso 7 — Webhook / llamadas Odoo → Django (implementado en v5)
- [x] `POST /api/orders/odoo-webhook/sale-order-update/` — sincroniza `SubOrder.status`
    según `sale.order.state` (`draft` → `pago_en_revision`, `sale` → `confirmado`,
    `cancel` → `cancelado`). **Además actualiza el `PaymentProof` a `approved`
    cuando el estado es `confirmado` (idempotente).**
- [x] `POST /api/orders/odoo-webhook/review-payment/` — acción explícita del proveedor.
    `action='approve'` → `PaymentProof.approved` + `SubOrder.confirmado`.
    `action='reject'` → `PaymentProof.rejected` + `SubOrder.pago_rechazado` +
    `payment_rejected=True`. **Idempotente en ambos casos.**

### 🟢 Frontend
- Badge de estado "Pago Rechazado" en historial-compras/[id] y checkout.
- Formulario de corrección habilitado solo cuando `SubOrder.status = 'pago_rechazado'`.
- Al reenviar comprobante, el backend transiciona a `pago_en_revision` y limpia el flag.

### 🔲 Paso 8 — Cancelaciones y reembolsos
- [ ] Endpoint `cancel_suborder` con lógica diferenciada según `odoo_sale_id` y estado Odoo
- [ ] Llamada JSON-RPC a `sale.order.action_cancel()` cuando aplica
- [ ] Flujo de reembolso manual: `SubOrder.refunded = True` + `SubOrder.refund_notes`

### 🔲 Paso 9 — Panel del proveedor en frontend
- [ ] Lista de SubOrders pendientes de confirmación de pago
- [ ] Acción aprobar / rechazar pago (con `rejection_reason`)
- [ ] Acción ingresar tracking number
- [ ] Link directo a la `sale.order` en Odoo
- [ ] Vista de `PaymentTransaction` con historial de intentos

---

## 1️⃣3️⃣ Observaciones abiertas tras auditoría de abril 2026

### 1. Seguridad y ownership pendientes

- `create_order` recibe `customer_id` y crea la orden con ese ID, pero hoy no valida que pertenezca al `request.user` autenticado.
- `upload_payment_proof` acepta `sub_order_id` y crea el comprobante sin validar ownership de la `SubOrder` contra el usuario autenticado.
- Estas dos validaciones faltantes no rompen la arquitectura conceptual, pero sí impiden considerar el flujo completamente endurecido.

### 2. Endpoints legacy todavía activos

- `SubOrderViewSet.confirm_payment()` sigue permitiendo aprobación o rechazo manual desde Django para vendors/admin.
- El frontend actual no consume ese endpoint; el flujo canónico ya pasa por Odoo webhook (`review-payment` y `sale-order-update`).
- Debe tratarse como fallback manual, no como parte principal del diseño.

### 3. Stubs y deuda técnica visibles

- `apps/orders/tasks.py:update_order_status_from_odoo` sigue en `pass`.
- `apps/orders/tasks.py:send_order_confirmation_email` sigue en `pass`.
- `apps/sync/tasks.py:create_order_in_odoo` sigue en `pass` y ya no representa el flujo vigente.

### 4. Cobertura automatizada insuficiente

- Hoy `apps/orders/tests.py` solo cubre historial de órdenes.
- No hay tests automatizados del flujo crítico: `create_order`, `upload_payment_proof`, webhooks Odoo, expiración TTL, reconciliación ni estados multiproveedor.
- Por eso, aunque la arquitectura base es coherente, la funcionalidad end-to-end depende todavía demasiado de validación manual.
