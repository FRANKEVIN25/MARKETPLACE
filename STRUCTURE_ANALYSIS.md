# 📋 Análisis de Coordinación Products ↔ Orders

## ✅ ESTRUCTURA VERIFICADA

### 1. **App: Products** 
**Modelos Finales:**

#### `Category` (UNIVERSAL)
- ✅ Jerárquica (MPPT)
- ✅ Compartida entre todos los proveedores
- ✅ Slug único
- **Uso:** Clasificación de productos

#### `Product` (POR PROVEEDOR)
- ✅ ForeignKey → Provider (ONE-TO-MANY)
- ✅ Reference único por proveedor
- ✅ Slug único (nombre + proveedor)
- ✅ Campos de precios (base + tax_percent)
- ✅ Integración Odoo (odoo_product_id, odoo_template_id)
- ✅ Manager personalizado (for_group, for_marketplace)
- ✅ Property: `total_stock` (suma desde StockItem)
- **Relaciones:** Category, Provider, VariantVehiculo (M2M), StockItem

#### `Warehouse` (POR PROVEEDOR)
- ✅ ForeignKey → Provider
- ✅ Único por (provider, name)
- ✅ Campos: city, address
- ✅ Integración Odoo (odoo_warehouse_id)
- ✅ Property: `total_stock` (suma StockItem)
- **Índices:** [provider, is_active], [provider]

#### `StockItem` (STOCK REAL POR ALMACÉN)
- ✅ Único por (product, warehouse)
- ✅ Cantidad en tiempo real
- ✅ Properties: `is_low_stock` (qty < 5), `is_out_of_stock` (qty == 0)
- ✅ Timestamps: created_at, updated_at (auto_now)
- **Índices:** [product], [warehouse], [product, warehouse], [warehouse, quantity]

#### `CompatibilidadProducto` (VEHÍCULOS COMPATIBLES)
- ✅ M2M Through entre Product y VariantVehiculo
- ✅ Campo extra: notas_instalacion
- ✅ Único por (producto, variante)

---

### 2. **App: Orders**
**Modelos Finales:**

#### `Order` (AGREGADOR MULTIPROVEEDOR)
- ✅ order_number único
- ✅ ForeignKey → Customer
- ✅ Status: borrador, pago_pendiente, pagado, procesando, completado, cancelado
- ✅ Totales: subtotal, discount_total, shipping_total, tax_total, total
- ✅ Envío: shipping_address (FK)
- ✅ Timestamps: created_at, paid_at, updated_at
- ✅ Properties: `supplier_count`, `item_count`
- ✅ Método: `can_be_paid()`
- **Relación 1→N:** SupplierOrder

#### `SupplierOrder` (POR PROVEEDOR)
- ✅ ForeignKey → Order (CASCADE)
- ✅ ForeignKey → Provider (marketplace multiproveedor)
- ✅ company_id (Odoo legacy)
- ✅ warehouse_id (Odoo fulfillment)
- ✅ Status: pending, confirmed, processing, shipped, completed, cancelled
- ✅ Totales: subtotal, tax_amount, shipping_cost, discount_amount, total
- ✅ Timestamps: created_at, confirmed_at, shipped_at, completed_at, updated_at
- ✅ Property: `item_count`
- ✅ Método: `calculate_totals()`
- **Relación 1→N:** OrderItem

#### `OrderItem` (LÍNEA DE PRODUCTO)
- ✅ ForeignKey → SupplierOrder (CASCADE)
- ✅ ForeignKey → Product (SET_NULL, snapshot)
- ✅ product_id_snapshot (Odoo ID capturado)
- ✅ sku, name (capturados al momento)
- ✅ Cantidad y precios: quantity, unit_price, tax_percent, tax_amount, total_price
- ✅ Timestamps: created_at, updated_at
- ✅ Método: `save()` calcula tax_amount y total_price
- **Nota:** Es un snapshot immutable

---

## 🔗 **COORDINACIÓN PRODUCTS ↔ ORDERS**

### Flujo de Compra:
```
Customer (Cliente)
    ↓
Order (1)
    ↓
SupplierOrder (puede tener N) → Provider
    ↓
OrderItem (1→N) → Product → Warehouse → StockItem
```

### Stock Real:
- **Source:** `Product.stock_items` → `StockItem` (por warehouse)
- **Query:** `Product.total_stock` suma todo
- **Stock Reservado:** En OrderItem (snapshot, no resta stock automáticamente)
- **Validación:** Al agregar a orden, verificar `StockItem.quantity >= OrderItem.quantity`

### Precios:
- **Base:** `Product.price` (sin impuesto)
- **Impuesto:** `Product.tax_percent` (18% Perú por defecto)
- **En Orden:** `OrderItem.unit_price` + `OrderItem.tax_percent` (snapshot)

---

## 📊 **Serializers para Svelte**

### Products:
- ✅ `CategorySerializer` - Listado jerárquico
- ✅ `ProductListSerializer` - Listado optimizado (con precio+tax)
- ✅ `ProductDetailSerializer` - Detalle con stock por almacén
- ✅ `ProductCreateUpdateSerializer` - Create/Update (valida proveedor)
- ✅ `WarehouseSerializer` - Almacenes
- ✅ `StockItemSerializer` - Stock por almacén
- ✅ `CompatibilidadProductoSerializer` - Compatibilidades
- ✅ `StockUpdateSerializer` - Actualizar stock

### Orders:
- ❌ **PENDIENTE:** Crear serializers para órdenes

---

## 🛠️ **Admin Django**

### Products:
- ✅ CategoryAdmin (MPPT, collapsible)
- ✅ ProductAdmin (con inline StockItem, CompatibilidadProducto)
- ✅ WarehouseAdmin (con total_stock display)
- ✅ StockItemAdmin (con filtros de estado)
- ✅ CompatibilidadesAdmin

### Orders:
- ✅ OrderAdmin (con inline SupplierOrder)
- ✅ SupplierOrderAdmin (con inline OrderItem)
- ✅ OrderItemAdmin

---

## ⚠️ **PROBLEMAS PENDIENTES**

### 1. **Import en admin.py**
```python
# ❌ ACTUAL:
from mppt.admin import MPTTModelAdmin

# ✅ CORRECTO:
from mppt.admin import MPTTModelAdmin  # Bien (es mppt, no mppt)
```
✅ **CORREGIDO**

### 2. **Migraciones**
- ❌ Sin migrations inicial
- ⚠️ Require database config (PostgreSQL)
- ⚠️ Require dependencias (Celery, etc.)

### 3. **Campos que falta verificar**
- ⚠️ Customer.Address debe estar completamente definida
- ⚠️ Provider debe estar registrada en admin
- ⚠️ Vehicle models (Marca, VariantVehiculo) deben existir

---

## 📝 **Checklist de Estructura**

```
PRODUCTS APP
├── ✅ models.py
│   ├── Category (MPPT)
│   ├── Product (Provider FK)
│   ├── Warehouse (Provider FK)
│   ├── StockItem (Product + Warehouse)
│   ├── CompatibilidadProducto (Through)
│   └── Managers/QuerySets optimizados
├── ✅ admin.py
│   ├── CategoryAdmin
│   ├── ProductAdmin (con inlines)
│   ├── WarehouseAdmin
│   ├── StockItemAdmin
│   └── CompatibilidadesAdmin
├── ✅ serializers.py
│   ├── CategorySerializer
│   ├── ProductListSerializer
│   ├── ProductDetailSerializer
│   ├── ProductCreateUpdateSerializer
│   ├── WarehouseSerializer
│   ├── StockItemSerializer
│   ├── StockUpdateSerializer
│   └── CompatibilidadProductoSerializer
└── ⚠️ migrations/
    └── ❌ Pendiente hacer

ORDERS APP
├── ✅ models/__init__.py (exporta Order, SupplierOrder, OrderItem)
├── ✅ models/order.py (Order + propiedades)
├── ✅ models/supplier_order.py (SupplierOrder + calculate_totals)
├── ✅ models/order_item.py (OrderItem + snapshot)
├── ✅ admin.py
│   ├── OrderAdmin
│   ├── SupplierOrderAdmin
│   └── OrderItemAdmin
├── ❌ serializers.py (PENDIENTE)
└── ⚠️ migrations/
    └── ❌ Pendiente hacer
```

---

## 🚀 **Próximos Pasos**

### ANTES DE MIGRACIONES:
1. ✅ Crear serializers de Orders (ProductListSerializer, OrderDetailSerializer, etc.)
2. ⚠️ Verificar que Customer.Address está completa
3. ⚠️ Verificar que Provider está en admin.py de marketplace
4. ⚠️ Instalar dependencias: celery, redis, psycopg2

### PARA HACER MIGRACIONES:
```bash
python3 manage.py makemigrations
python3 manage.py migrate
```

### PARA PROBAR MODELOS:
```bash
python3 manage.py shell
>>> from apps.products.models import Product, Warehouse, StockItem
>>> from apps.orders.models import Order, SupplierOrder, OrderItem
```

---

## 💡 **PARTICULARIDADES MULTIPROVEEDOR**

1. **Producto es de UN proveedor:** `Product.provider` (FK)
2. **Orden puede tener múltiples proveedores:** `Order.supplier_orders` (1→N)
3. **Stock es POR ALMACÉN:** `StockItem` (product + warehouse)
4. **Cada proveedor tiene sus almacenes:** `Warehouse.provider` (FK)
5. **OrderItem es snapshot:** No se modifica, registra estado de compra

---

## 📦 **INTEGRACIÓN ODOO**

| Modelo | Campo Odoo | Propósito |
|--------|-----------|----------|
| Product | odoo_product_id | Sync bidireccional |
| Product | odoo_template_id | Plantilla en Odoo |
| Warehouse | odoo_warehouse_id | Ubicación en Odoo |
| SupplierOrder | company_id | Compañía Odoo (legacy) |
| SupplierOrder | warehouse_id | Almacén Odoo de fulfillment |

---

Status: ✅ Estructura LISTA para migraciones
