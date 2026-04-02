# Motor de Descuentos por Historial de Compra — ECOMPARTS Marketplace
> Documentación técnica basada en el código real del proyecto (abril 2026)
> **Última revisión:** 1 de abril de 2026 — v1: descuentos por historial cliente-proveedor implementados

---

## 1️⃣ Principio rector

| Actor | Responsabilidad |
|---|---|
| **`apps/discounts`** | Define las reglas (`DiscountRule`): umbrales mínimos y porcentajes de descuento por tipo de cliente y proveedor. Se gestionan desde el admin de Django. |
| **`apps/orders/pricing/customer_discount.py`** | Motor de cálculo. Se ejecuta en tiempo real durante la creación de la orden. Calcula el historial ponderado y busca la regla aplicable. |
| **`apps/customer`** | `CustomerProviderStats` cachea el historial calculado por el motor, para visualización en el admin. `CustomerStats` acumula los totales globales del cliente. |
| **`apps/orders/signals.py`** | Mantiene ambas tablas de stats actualizadas automáticamente via `post_save` en `SubOrder`. |

> ⚠️ **El descuento se calcula y se fija en el instante de crear la orden** (`create_order`), no cuando el pago es aprobado. Lo que sí se actualiza al aprobar un pago es el historial que servirá para **futuras** órdenes.

---

## 2️⃣ Modelo de datos

### 2.1. `DiscountRule` — reglas configurables por admin

```
apps/discounts/models.py → DiscountRule
```

| Campo | Tipo | Descripción |
|---|---|---|
| `customer_type` | `individual` / `company` | Tipo de cliente al que aplica |
| `provider` | FK → `Provider` \| `null` | Si `null`, es regla global (fallback). Si tiene valor, aplica solo para ese proveedor. |
| `min_amount` | Decimal | Umbral mínimo de historial ponderado (en soles) para activar este nivel |
| `discount_percent` | Decimal | Porcentaje de descuento (ej. `5.00` = 5 %) |
| `is_active` | Boolean | Permite desactivar reglas sin borrarlas |

**Prioridad de reglas** (el motor evalúa en este orden):
1. Regla con `provider` específico del proveedor de la sub-orden
2. Regla global (`provider = null`) — fallback

En ambos casos se elige la regla con el **mayor `min_amount` que no supere** el historial ponderado del cliente.

### 2.2. `SubOrder` — campos de descuento (snapshot)

```
apps/orders/models/sub_order.py → SubOrder
```

| Campo | Descripción |
|---|---|
| `discount_percent` | Porcentaje aplicado en el momento de crear la orden (snapshot inmutable) |
| `discount` | Monto en soles redondeado al sol más cercano (snapshot inmutable) |

> ⚠️ Estos valores **nunca se recalculan** después de la creación. Son un snapshot del descuento vigente en ese momento.

### 2.3. `CustomerProviderStats` — historial cacheado por proveedor

```
apps/customer/models.py → CustomerProviderStats
```

| Campo | Descripción |
|---|---|
| `total_spent` | Suma de `SubOrder.total` en estados válidos con ese proveedor |
| `total_orders` | Cantidad de SubOrders válidas con ese proveedor |
| `weighted_history` | Historial ponderado calculado por el motor (ventana temporal) |
| `current_discount_percent` | % de descuento activo con ese proveedor (según `DiscountRule`) |
| `next_tier_amount` | Cuántos soles adicionales necesita para el siguiente nivel (0 = tier máximo) |
| `last_recalculated` | `auto_now` — fecha del último recálculo |

Una fila por par `(customer, provider)`. Se crea/actualiza automáticamente via signal.

### 2.4. `CustomerStats` — totales globales del cliente

```
apps/customer/models.py → CustomerStats
```

Totales acumulados de **todos** los proveedores. Se mantiene sincronizado por el mismo signal. También guarda datos cualitativos (`preferred_brands`, `notes`) que solo gestiona el admin.

> **Nota:** `CustomerStats` solo existe para clientes que han tenido al menos una SubOrder confirmada. Los clientes sin órdenes confirmadas no tienen este registro. Esto es por diseño: los valores serían todos cero y no aportan información.

---

## 3️⃣ Flujo completo del descuento

### 3.1. Creación de la orden (checkout)

```
Cliente → POST /api/orders/create_order/
                │
                ▼
     OrderViewSet.create_order()
     apps/orders/views.py
                │
                ├─ Agrupa CartItems por proveedor
                │
                ├─ Para cada proveedor:
                │     ├─ Calcula subtotal (sum price × qty)
                │     ├─ Llama calcular_descuento_suborder(customer, provider, subtotal)
                │     │         │
                │     │         ▼  [apps/orders/pricing/customer_discount.py]
                │     │    1. _esquema_ponderacion(customer_type)
                │     │    2. _historial_ponderado(customer, provider, esquema)
                │     │         └─ Queries en vivo sobre SubOrder (estados válidos)
                │     │    3. monto_total = historial + subtotal_actual
                │     │    4. _buscar_regla(customer_type, provider, monto_total)
                │     │         └─ Busca en DiscountRule primero por proveedor,
                │     │            luego global (fallback)
                │     │    5. Retorna (porcentaje, monto_redondeado)
                │     │
                │     ├─ SubOrder.discount_percent = porcentaje
                │     ├─ SubOrder.discount        = monto
                │     └─ SubOrder.total = subtotal - descuento + IGV
                │
                └─ Order.discount = suma de sub-order discounts
                   Order.total    = subtotal - discount + tax
```

### 3.2. Ponderación del historial

El historial no es la suma simple de todas las compras. Aplica pesos temporales según el tipo de cliente:

| Tipo cliente | Ventana 1 | Peso 1 | Ventana 2 | Peso 2 |
|---|---|---|---|---|
| `company` | Últimos 30 días | 70 % | Días 31–90 | 30 % |
| `individual` | Últimos 90 días | 60 % | Días 91–240 | 40 % |

**Fórmula:**
```
historial_ponderado = (suma_días_0_30 × 0.70) + (suma_días_31_90 × 0.30)   [company]
historial_ponderado = (suma_días_0_90 × 0.60) + (suma_días_91_240 × 0.40)  [individual]
```

El valor de referencia para buscar la regla es:
```
monto_total = historial_ponderado + subtotal_suborder_actual
```

Esto permite que una orden grande "suba" al cliente de tier aunque su historial aún no lo alcance.

### 3.3. Redondeo del monto de descuento

```python
monto_exacto    = (subtotal × porcentaje) / 100
monto_redondeado = round(monto_exacto)   # al sol más cercano, sin centavos
```

Ejemplo: subtotal S/ 600, descuento 5 % → exacto S/ 30.00 → redondeado **S/ 30.00**
Ejemplo: subtotal S/ 847, descuento 5 % → exacto S/ 42.35 → redondeado **S/ 42.00**

### 3.4. Estados válidos para el historial

Solo las SubOrders en los siguientes estados cuentan para el cálculo del historial:

| Estado | ¿Cuenta? | Motivo |
|---|---|---|
| `pendiente_pago` | ❌ No | Pago no realizado |
| `pago_en_revision` | ❌ No | Pago subido pero no aprobado aún |
| `pago_rechazado` | ❌ No | Pago rechazado por el proveedor |
| `confirmado` | ✅ **Sí** | Pago aprobado por el proveedor en Odoo |
| `enviado` | ✅ **Sí** | Pedido en tránsito |
| `entregado` | ✅ **Sí** | Pedido entregado al cliente |
| `cancelado` | ❌ No | Operación abortada |

> ✅ **Decisión de diseño:** el historial solo incluye transacciones **confirmadas por el proveedor en Odoo**. Un comprobante subido pero no aprobado no genera historial, porque el pago real aún no fue verificado. Esto garantiza que el descuento refleja una relación comercial probada, no promesas.

---

## 4️⃣ Actualización automática del historial (signal)

```
SubOrder → post_save
              │
              ▼
  update_customer_provider_stats()
  apps/orders/signals.py
              │
              ├─ Guard: ¿status ∈ {confirmado, enviado, entregado}? → continuar
              │
              ├─ Calcula acumulados en vivo:
              │     total_spent  = SUM(SubOrder.total)  [estados válidos, mismo proveedor]
              │     total_orders = COUNT(SubOrder)
              │
              ├─ Calcula historial ponderado (mismo algoritmo que checkout)
              │
              ├─ Busca descuento actual y siguiente tier en DiscountRule
              │
              ├─ CustomerProviderStats.update_or_create(customer, provider, ...)
              │
              └─ CustomerStats.update_or_create(customer, ...)
                    total_spent  = SUM a través de todos los proveedores
                    total_orders = COUNT a través de todos los proveedores
                    average_order_value = AVG(SubOrder.total)
```

El signal se conecta en `OrdersConfig.ready()` (apps/orders/apps.py) para evitar importaciones circulares.

---

## 5️⃣ Timeline completo: de la compra al historial

```
T=0  Cliente crea orden (create_order)
     ├─ historial_ponderado se consulta en vivo sobre SubOrders existentes
     ├─ Se elige la regla de descuento aplicable
     ├─ SubOrder.discount y SubOrder.discount_percent quedan fijados (snapshot)
     └─ El descuento se muestra en el checkout (paso Pago)

T+?  Cliente sube comprobante → SubOrder: pendiente_pago → pago_en_revision
     └─ (sin efecto en historial ni en descuento)

T+?  Proveedor aprueba pago en Odoo → SubOrder: pago_en_revision → confirmado
     ├─ Signal post_save se dispara
     ├─ CustomerProviderStats se actualiza (historial, descuento actual, next tier)
     └─ CustomerStats se actualiza (totales globales)

T+?  Następna orden del mismo cliente con el mismo proveedor:
     └─ historial_ponderado = incluye la orden confirmada → puede activar tier superior
```

---

## 6️⃣ Ejemplo numérico completo

**Configuración de reglas (company, global):**

| min_amount | discount_percent |
|---|---|
| S/ 2,000 | 5 % |
| S/ 5,000 | 8 % |
| S/ 10,000 | 10 % |

**Cliente:** `Taller Los Andes` (type=`company`)
**Historial previo con Proveedor A:** S/ 3,800 en los últimos 30 días, S/ 0 en días 31–90

```
historial_ponderado = (3,800 × 0.70) + (0 × 0.30) = S/ 2,660
```

**Nueva orden:** subtotal S/ 1,500 (sin IGV)

```
monto_total = 2,660 + 1,500 = S/ 4,160

Reglas evaluadas:
  min=2,000 → 4,160 ≥ 2,000 ✅
  min=5,000 → 4,160 ≥ 5,000 ❌

Regla aplicada: 5 %
Descuento exacto:  1,500 × 5% = S/ 75.00
Descuento redondeado: S/ 75.00

SubOrder.subtotal       = S/ 1,500.00
SubOrder.discount_percent = 5.00
SubOrder.discount         = S/ 75.00
SubOrder.igv_amount       = S/ 261.00  (18% sobre 1,500 - 75 = 1,425)
SubOrder.total            = S/ 1,686.00

Falta para el tier 8%: 5,000 - 4,160 = S/ 840.00
```

---

## 7️⃣ Archivos clave

| Archivo | Propósito |
|---|---|
| [apps/discounts/models.py](../services/backend/apps/discounts/models.py) | Modelo `DiscountRule` |
| [apps/discounts/admin.py](../services/backend/apps/discounts/admin.py) | Admin de reglas (CRUD) |
| [apps/orders/pricing/customer_discount.py](../services/backend/apps/orders/pricing/customer_discount.py) | Motor de cálculo |
| [apps/orders/views.py](../services/backend/apps/orders/views.py) | `create_order` — aplica el descuento al crear |
| [apps/orders/signals.py](../services/backend/apps/orders/signals.py) | `update_customer_provider_stats` — cachea historial |
| [apps/customer/models.py](../services/backend/apps/customer/models.py) | `CustomerProviderStats`, `CustomerStats` |
| [apps/customer/admin.py](../services/backend/apps/customer/admin.py) | Visualización del historial en el admin |

---

## 8️⃣ Decisiones de diseño y advertencias

### ✅ Por qué el descuento se calcula al crear la orden (no al pagar)

El descuento debe mostrarse al cliente **antes de confirmar la compra** (paso Pago del checkout). Si se calculara al aprobar el pago, el cliente no sabría qué precio pagar ni qué monto transferir. El snapshot en `SubOrder.discount` garantiza que el monto que el cliente ve y paga es exactamente el monto que el sistema registra.

### ✅ Por qué el historial solo cuenta desde `confirmado`

Un comprobante subido pero no aprobado podría ser rechazado por el proveedor (pago incompleto, transferencia incorrecta, voucher falso). Contarlo como historial antes de la aprobación generaría descuentos basados en pagos que podrían no completarse. La aprobación en Odoo es la única garantía de una transacción real.

### ⚠️ CustomerStats solo existe para clientes con pedidos confirmados

El registro `CustomerStats` se crea via signal, por lo que solo existe para clientes que hayan tenido al menos una SubOrder confirmada. En el admin, el número de Estadísticas de Cliente será menor al número total de Clientes registrados. Esto es esperado y correcto.

### ⚠️ El historial usa totales con IGV (`SubOrder.total`)

El campo `SubOrder.total` incluye IGV. Esto significa que el historial refleja el dinero real que el cliente ha transferido al proveedor, incluyendo impuestos. La coherencia con `monto_total` (historial + subtotal_actual) no es perfecta porque `subtotal_actual` es sin IGV, pero en la práctica es una diferencia menor y los umbrales de `DiscountRule` deben configurarse teniendo esto en cuenta.

### ⚠️ El motor de descuentos hace queries en vivo al crear la orden

`_historial_ponderado` ejecuta 2–4 queries sobre `SubOrder` cada vez que se crea una orden. Para el PMV con volúmenes pequeños esto es aceptable. En producción con alto tráfico se puede optimizar leyendo desde `CustomerProviderStats.weighted_history` en lugar de recalcular, asumiendo que ese caché está actualizado.
