# Filtro de Productos por Vehículo — ECOMPARTS Marketplace
> Diseño técnico basado en el código real del proyecto (marzo 2026)
> **Alcance:** página `/productos` del frontend (SvelteKit) consumiendo APIs públicas de Django (Marketplace + Products + Vehicles)

---

## 1️⃣ Principio rector

| Capa | Responsabilidad |
|---|---|
| **SvelteKit (Frontend)** | Controla la UX del catálogo: selects encadenados Marca → Modelo → Variante, buscador de texto, orden, paginación y sincronización con la URL. **No calcula reglas de compatibilidad ni hace joins complejos.** |
| **Django (Marketplace + Products + Vehicles)** | Expone APIs especializadas para: (a) obtener marcas, modelos y variantes disponibles en el marketplace; (b) listar productos del marketplace filtrando por vehículo, texto libre, categoría y orden. Centraliza la lógica de compatibilidad. |
| **PostgreSQL** | Ejecuta los joins pesados `Product ↔ CompatibilidadProducto ↔ VariantVehiculo ↔ ModeloVehiculo ↔ Marca` apoyado en índices. |

> ⚠️ El criterio de compatibilidad **siempre** se resuelve en el backend usando `CompatibilidadProducto`. El frontend solo envía IDs (marca, modelo, variante) como filtros.

---

## 2️⃣ Modelo de datos relevante (ya implementado)

### 2.1. Productos y compatibilidad

Modelos en [services/backend/apps/products/models.py](services/backend/apps/products/models.py):

- `Product`
  - Pertenece a un `Provider` (vendor) y a una `Category` (universal).
  - Es la entidad que se muestra en el catálogo público (vía `MarketplaceProductViewSet`).
- `CompatibilidadProducto`
  - `producto: ForeignKey(Product, related_name='compatibilidades')`
  - `variante: ForeignKey('vehicles.VariantVehiculo')`
  - `notas_instalacion: CharField` opcional.
  - `unique_together = ('producto', 'variante')` + índices sobre `(variante, producto)`.

Este modelo es el **puente** entre el catálogo de productos y el universo de vehículos.

### 2.2. Vehículos

Modelos en [services/backend/apps/vehicles/models.py](services/backend/apps/vehicles/models.py):

- `Marca`
  - `nombre`, `slug`, `activo`.
- `ModeloVehiculo`
  - `nombre`, `marca`, `slug`, `activo`.
- `Motor`
  - `combustible`, `cilindrada_cc`, `codigo_motor`, `tecnologia`.
  - `__str__` ya devuelve un resumen amigable (ej: `2.0L (4G63) Turbo`).
- `Transmision`
  - `tipo` (`MT`, `AT`, `CVT`, etc.), `velocidades`.
  - `__str__` devuelve algo como `Manual 5`.
- `Traccion`
  - `tipo` (`4x2`, `4x4`, `AWD`).
- `VariantVehiculo`
  - `modelo`, `motor`, `transmision`, `traccion`, `anio_desde`, `anio_hasta`.
  - `__str__` devuelve `"Marca Modelo | Motor | Transmisión | Tracción (anio_desde-anio_hasta)"`.

> 🔑 La **variante de vehículo** es la unidad mínima de compatibilidad. Los filtros de `marca` y `modelo` se traducen a subconjuntos de variantes.

---

## 3️⃣ Objetivo funcional del filtro en `/productos`

### 3.1. Caso de uso principal

El usuario final quiere responder: **"Muéstrame solo las piezas compatibles con mi vehículo"**.

- Paso 1 — Selecciona **Marca** (ej: `Toyota`).
- Paso 2 — Selecciona **Modelo** (ej: `Yaris`).
- Paso 3 — Selecciona **Variante** (ej: `Yaris 1.3L (1NR-FE) MT 4x2 (2012-2018)`).
- El listado de productos se filtra a aquellos que tienen al menos una `CompatibilidadProducto` ligada a esa variante.

### 3.2. Requerimientos específicos

- Tres campos de filtro: `marca`, `modelo`, `variante`:
  - Encadenados: al cambiar la marca se limpian modelos y variantes; al cambiar modelo se limpian variantes.
  - Los modelos mostrados para una marca deben ser **solo** aquellos que tienen al menos un producto compatible en el marketplace (no todo el catálogo teórico de vehículos).
  - Las variantes mostradas para un modelo deben estar formateadas como un **texto concatenado único** (ver §4.3).
- Comportamiento combinado con otros filtros ya existentes o futuros:
  - Búsqueda de texto libre (por nombre, referencia, descripción).
  - Filtro por categoría del producto.
  - Orden (precio asc/desc, relevancia, más recientes).
  - Paginación controlada desde la querystring (ej: `page=2`).
- Persistencia en la URL: todos los filtros deben reflejarse en la querystring de `/productos`.
- Soporte multiproveedor: el filtro por vehículo no se limita a un proveedor; debe considerar el universo completo de `Product.for_marketplace()`.

---

## 4️⃣ API de vehículos para filtros encadenados (pública)

Actualmente `apps/vehicles/views.py` expone `ViewSet`s con `IsAuthenticated` (orientados a panel interno). Para el marketplace público se define una **capa de lectura read-only y pública** que reutiliza los serializers pero con permisos abiertos.

### 4.1. Endpoints propuestos

Nuevo namespace (ejemplo): `/api/public/vehicles/` con 3 endpoints clave:

1. `GET /api/public/vehicles/marcas/`
   - Lista de marcas **activas** que tienen al menos un producto compatible en el marketplace.
2. `GET /api/public/vehicles/modelos/`
   - Requiere `marca_id` o `marca_slug`.
   - Lista de modelos activos para esa marca **con productos compatibles**.
3. `GET /api/public/vehicles/variantes/`
   - Requiere `modelo_id`.
   - Lista de variantes activas para ese modelo **con productos compatibles**, con un campo `display_name` ya concatenado.

> Nota: a nivel de implementación, estos endpoints pueden vivir en `apps/products` o en un nuevo módulo `apps/public`, pero **no** deben permitir creación/edición (solo lectura).

### 4.2. Filtro "solo con productos compatibles"

Todos los endpoints de vehículos orientados al marketplace deben considerar únicamente marcas/modelos/variantes que aparezcan en `CompatibilidadProducto` asociadas a productos visibles en el marketplace.

Pseudocódigo conceptual:

```python
# Conjunto base de productos en marketplace
productos = Product.objects.for_marketplace().filter(is_active=True)

# Marcas con productos compatibles
marcas = Marca.objects.filter(
    modelo__variantvehiculo__compatibilidadproducto__producto__in=productos
).distinct()

# Modelos para una marca con productos compatibles
modelos = ModeloVehiculo.objects.filter(
    marca_id=marca_id,
    activo=True,
    variantvehiculo__compatibilidadproducto__producto__in=productos,
).distinct()

# Variantes para un modelo con productos compatibles
variantes = VariantVehiculo.objects.filter(
    modelo_id=modelo_id,
    compatibilidadproducto__producto__in=productos,
).select_related('modelo', 'motor', 'transmision', 'traccion').distinct()
```

### 4.3. Formato del campo "Variante" (concatenado)

Requisito: la variante debe mostrarse como **un solo texto** que ya incluya todos los campos relevantes:

- Motor (cilindrada, código, tecnología).
- Transmisión (tipo + velocidades si aplica).
- Tracción.
- Rango de años.

Se propone un serializer específico para filtros:

```python
# apps/vehicles/serializers.py
class VariantVehiculoFilterSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = VariantVehiculo
        fields = ['id', 'display_name', 'modelo', 'anio_desde', 'anio_hasta']

    def get_display_name(self, obj):
        # Basado en __str__ de los modelos relacionados
        hasta = obj.anio_hasta or 'Actual'
        return (
            f"{obj.motor} | {obj.transmision} | {obj.traccion} "
            f"({obj.anio_desde}-{hasta})"
        )
```

Respuesta ejemplo:

```json
GET /api/public/vehicles/variantes/?modelo_id=123
[
  {
    "id": 45,
    "display_name": "1.3L (1NR-FE) VVT-i | Manual 5 | 4x2 (2012-2018)",
    "modelo": 123,
    "anio_desde": 2012,
    "anio_hasta": 2018
  }
]
```

---

## 5️⃣ API de productos de marketplace con filtros por vehículo

### 5.1. Base actual

En [services/backend/apps/products/views.py](services/backend/apps/products/views.py):

- `MarketplaceProductViewSet` (ReadOnlyModelViewSet)
  - `permission_classes = []` (público)
  - `authentication_classes = []`
  - `filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]`
  - `filterset_fields = ['category', 'product_type']`
  - `search_fields = ['name', 'reference', 'description']`
  - `ordering_fields = ['name', 'price', 'created_at']`
  - `get_queryset` usa `Product.objects.for_marketplace()`.

### 5.2. Nuevos parámetros de filtro

Se agregan parámetros GET opcionales a la lista pública de productos:

- `marca_id`: filtra productos compatibles con variantes cuyo modelo pertenece a esa marca.
- `modelo_id`: filtra productos compatibles con variantes de ese modelo.
- `variante_id`: filtra productos compatibles con esa variante específica.
- `q`: texto de búsqueda (alias amable de `search`).
- `provider_id`: filtra productos de un proveedor específico (campo `Product.provider_id`).
- `es_universal`: controla el filtro por productos universales (`Product.es_universal`):
  - `es_universal=true` → solo productos universales.
  - `es_universal=false` → solo productos NO universales (requieren compatibilidad o al menos no están marcados como universales).
  - (omitido) → incluye ambos tipos.
- `category_id`: ID de la categoría seleccionada (modelo `Category`). El filtro debe incluir la categoría y **todas sus descendientes** en el árbol MPTT.
- `category_slug`: alternativa textual a `category_id` (útil para URLs amigables); si se envían ambos, prevalece `category_id`.
- `ordering`: `-created_at` (default), `price`, `-price`, `name`, `-name`.

Ejemplo de URL combinada:

```text
GET /api/products/marketplace/?marca_id=10&modelo_id=120&variante_id=45&q=disco+freno&ordering=price&page=2
```

### 5.3. Lógica de filtrado por vehículo

Pseudocódigo propuesto dentro de `get_queryset` o de un `FilterSet` dedicado:

```python
from django.db.models import Q

class MarketplaceProductViewSet(ReadOnlyModelViewSet):
    ...
    def get_queryset(self):
        qs = Product.objects.for_marketplace().filter(is_active=True)

        request = self.request
        marca_id = request.query_params.get('marca_id')
        modelo_id = request.query_params.get('modelo_id')
        variante_id = request.query_params.get('variante_id')
        q = request.query_params.get('q')

        if marca_id:
            qs = qs.filter(
                compatibilidades__variante__modelo__marca_id=marca_id
            )

        if modelo_id:
            qs = qs.filter(
                compatibilidades__variante__modelo_id=modelo_id
            )

        if variante_id:
            qs = qs.filter(
                compatibilidades__variante_id=variante_id
            )

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(reference__icontains=q) |
                Q(description__icontains=q) |
                Q(manufacturer_code__icontains=q)
            )

        return qs.distinct()
```

> 🔍 Para una implementación más limpia, se puede definir un `MarketplaceProductFilter` usando `django-filter` y declararlo en `filterset_class`.

### 5.4. Serializador de lista

Se reutiliza `ProductListSerializer`, que ya expone:

- `id`, `name`, `reference`, `slug`.
- `provider_name`, `product_type`.
- `price`, `price_with_tax`, `tax_percent`.
- `category_name`, `image`.
- `is_active`, `total_stock`, `is_synced`, `created_at`.

No es necesario exponer la lista de variantes compatibles en el listado; eso quedará para la vista de detalle de producto.

---

## 6️⃣ UX en SvelteKit — página `/productos`

### 6.1. Estado y querystring

Se define un estado de filtros en el frontend sincronizado con los parámetros de la URL:

```ts
// Ejemplo conceptual en +page.svelte / store compartido
let filtros = {
  marca_id: $page.url.searchParams.get('marca_id') ?? '',
  modelo_id: $page.url.searchParams.get('modelo_id') ?? '',
  variante_id: $page.url.searchParams.get('variante_id') ?? '',
  q: $page.url.searchParams.get('q') ?? '',
  ordering: $page.url.searchParams.get('ordering') ?? '-created_at',
  page: Number($page.url.searchParams.get('page') ?? '1')
};
```

Reglas:

- Al cambiar `marca_id` → limpiar `modelo_id` y `variante_id` y resetear `page = 1`.
- Al cambiar `modelo_id` → limpiar `variante_id` y resetear `page = 1`.
- Al cambiar `variante_id`, `q` o `ordering` → `page = 1`.
- Toda actualización de filtros debe llamar a una función `actualizarURL()` que haga `goto` o `pushState` con la nueva querystring.

### 6.2. Carga inicial en `+page.ts`

`+page.ts` debe leer los parámetros de la URL y llamar a la API de marketplace con esos filtros:

```ts
export const load: PageLoad = async ({ url, fetch }) => {
  const params = new URLSearchParams(url.search);

  const response = await api.marketplace.list({
    marca_id: params.get('marca_id') || undefined,
    modelo_id: params.get('modelo_id') || undefined,
    variante_id: params.get('variante_id') || undefined,
    q: params.get('q') || undefined,
    ordering: params.get('ordering') || '-created_at',
    page: Number(params.get('page') || '1'),
    page_size: 24
  });

  // En paralelo, se puede precargar lista de marcas públicas
  const marcas = await api.publicVehicles.marcas();

  return {
    products: response.results ?? [],
    totalCount: response.count ?? 0,
    marcas,
    filtrosIniciales: {
      marca_id: params.get('marca_id'),
      modelo_id: params.get('modelo_id'),
      variante_id: params.get('variante_id'),
      q: params.get('q') || '',
      ordering: params.get('ordering') || '-created_at',
      page: Number(params.get('page') || '1')
    }
  };
};
```

### 6.3. Carga dinámica de modelos y variantes (encadenado)

En el componente Svelte:

- `onMount` o en un reactive statement, si llega `marca_id` inicial, llamar a `api.publicVehicles.modelos(marca_id)`.
- Si llega `modelo_id` inicial, llamar a `api.publicVehicles.variantes(modelo_id)`.
- Al cambiar el valor de un select:
  - Actualizar el estado local de filtros.
  - Disparar la recarga de productos (ya sea navegando a la URL con nuevos parámetros o usando `enhance`).

Ejemplo conceptual:

```svelte
<select bind:value={filtros.marca_id} on:change={onMarcaChange}>...</select>
<select bind:value={filtros.modelo_id} disabled={!modelos.length} on:change={onModeloChange}>...</select>
<select bind:value={filtros.variante_id} disabled={!variantes.length} on:change={onVarianteChange}>...</select>
```

Donde `onMarcaChange`:

```ts
function onMarcaChange() {
  filtros.modelo_id = '';
  filtros.variante_id = '';
  filtros.page = 1;
  cargarModelos(filtros.marca_id);
  actualizarURL();
}
```

### 6.4. Comportamiento en ausencia de resultados

- Si después de aplicar filtros de vehículo y texto no hay productos:
  - Mostrar mensaje claro de "No se encontraron productos compatibles con este vehículo".
  - Ofrecer botón para limpiar filtros de vehículo (`marca_id`, `modelo_id`, `variante_id`).

---

## 7️⃣ Consideraciones de rendimiento e índices

- `CompatibilidadProducto` ya tiene índice `Index(fields=['variante', 'producto'])`, lo que ayuda a filtrar productos por variante.
- Para filtrar por marca y modelo conviene apoyarse en índices definidos en `vehicles`:
  - `ModeloVehiculo` tiene índices sobre `['marca', 'activo']`.
  - `VariantVehiculo` tiene índices sobre `['modelo', 'anio_desde', 'anio_hasta']`.
- En las consultas de productos:
  - Usar `select_related('category', 'provider')` en el queryset base del marketplace.
  - Usar `prefetch_related('compatibilidades__variante__modelo__marca')` en vistas donde se necesite mostrar información de compatibilidad.
- Siempre terminar el queryset de marketplace con `.distinct()` para evitar duplicados por joins de compatibilidad.

---

## 8️⃣ Casos borde y reglas de negocio

- **Cambio de filtros inconsistentes:**
  - Si el usuario manipula manualmente la URL con un `modelo_id` que no pertenece a la `marca_id` seleccionada, el backend seguirá devolviendo resultados vacíos. El frontend debe manejar esto mostrando "sin resultados" sin romper.
- **Variante sin productos activos:**
  - El endpoint público de variantes debe filtrar **solo** variantes con productos activos en el marketplace. Así se evita ofrecer variantes "muertas" en el selector.
- **Productos universales sin compatibilidad específica:**
  - Si existen productos marcados como universales (ej: aditivos), la regla puede ser:
    - No se muestran cuando se aplica un filtro de vehículo **estricto** (solo compatibles explícitamente), o
    - Se muestran siempre. Este es un punto de decisión de negocio que se debe dejar parametrizable más adelante.
    
 OBSERVACION: ESTO SE RESUELVE CON FILTROS ACTIVOS O APLICADOS, "UNIVERSALES" DEBE SER UN FILTRO APLICADO POR DEFECTO, EL USUARIO TIENE LA LIBERTAD DE BORRAR O APLICAR LOS OTROS FILTROS, ENTIENDO QUE INCLUSO FILTRAR POR CATEGORIAS PUEDE MOSTRARSE COMO UN FILTRO APLICADO, FILTRO POR PROVEEDOR, ETC, PUEDEN APLICARSE MUCHOS FILTROS A LA VES. 

### 8.1. Filtros activos (universales, proveedor, categorías)

La observación anterior se traduce en un sistema de **filtros activos/aplicados** que se muestran como _chips_ debajo del buscador y se reflejan en la querystring.

- **Fuente de verdad:**
  - Los filtros activos se derivan **solo** de los parámetros de la URL (`marca_id`, `modelo_id`, `variante_id`, `q`, `provider_id`, `category_id`/`category_slug`, `es_universal`, etc.).
  - El frontend no mantiene lógica duplicada; simplemente interpreta lo que viene en la URL y lo representa como chips.

- **Filtro "Universales":**
  - A nivel de modelo ya existe `Product.es_universal` (booleano, con índice).
  - El backend expone el parámetro `es_universal` descrito en §5.2.
  - **Estado por defecto (sin `es_universal` en la URL):** se incluyen productos universales y no universales. En la UI se muestra un chip "Universales" como **activo por defecto** para comunicar que los productos universales están incluidos en los resultados.
  - Si el usuario desea **excluir** productos universales, el frontend envía `es_universal=false` en la URL y actualiza el chip correspondiente (por ejemplo, cambiando su estilo o texto a "Sin universales").
  - Opcionalmente se puede ofrecer un modo "Solo universales" (`es_universal=true`) como tercer estado, útil cuando el usuario busca aditivos, herramientas u otros productos genéricos no ligados a un vehículo específico.

- **Filtro por proveedor:**
  - Se apoya en `Product.provider` y el parámetro `provider_id` de §5.2.
  - El frontend puede exponer este filtro como un desplegable de proveedores (o un listado de chips), y cada selección genera un chip activo con el nombre del proveedor.
  - Al limpiar el chip de proveedor, se elimina `provider_id` de la URL y se recargan los productos.

- **Filtro por categorías (árbol MPTT):**
  - Se usa el modelo `Category(MPTTModel)` del app `products`. Una categoría puede tener hijas; el filtro debe considerar la categoría seleccionada **y todas sus descendientes** (`Category.get_descendants(include_self=True)`).
  - El filtro se expresa vía `category_id` (o `category_slug`) en la URL. Esto permite construir URLs estables del tipo:
    - `/productos?category_slug=frenos` o `/productos?category_id=10`.
  - En la UI, al elegir una categoría (por ejemplo, desde un panel lateral o un menú desplegable), se añade un chip con el nombre de la categoría seleccionada. Al cerrar el chip, se eliminan `category_id`/`category_slug` de la URL.

- **Combinación de múltiples filtros:**
  - El usuario puede aplicar **varios filtros simultáneamente**: vehículo (marca/modelo/variante), texto (`q`), proveedor, categoría, universales y orden.
  - Cada filtro activo se representa como un chip individual con botón de cierre (`✕`). Quitar un chip equivale a eliminar el parámetro asociado de la URL y resetear `page` a `1`.
  - Se puede incluir un chip o botón de "Limpiar todos" que elimine **todos** los parámetros de filtro (excepto, si se desea, algún valor por defecto de negocio) y recargue el listado base.

- **Multiproveedor:**
  - El mismo producto (misma referencia) puede existir en catálogos de varios proveedores. El filtro por vehículo se aplica de forma uniforme; cada fila corresponde a un `Product` concreto de un proveedor.

---

## 9️⃣ Checklist de implementación

1. **Backend — Vehicles públicos**
   - [ ] Crear endpoints GET públicos para `marcas`, `modelos` y `variantes` basados en los modelos de `vehicles`.
   - [ ] Aplicar filtros "solo con productos marketplace" usando `CompatibilidadProducto`.
   - [ ] Implementar `VariantVehiculoFilterSerializer` con campo `display_name` concatenado.

2. **Backend — MarketplaceProductViewSet**
   - [ ] Extender `get_queryset` (o crear `FilterSet`) para soportar `marca_id`, `modelo_id`, `variante_id`, `q`.
   - [ ] Asegurar `distinct()` y uso de índices adecuados.

3. **Frontend — API client**
   - [ ] Agregar métodos en `$lib/api/client` para `publicVehicles.marcas`, `publicVehicles.modelos`, `publicVehicles.variantes`.
   - [ ] Ajustar `api.products.list` o crear `api.marketplace.list` específico para el endpoint público.

4. **Frontend — `/productos`**
   - [ ] Actualizar `+page.ts` para leer filtros desde `url.searchParams` y llamarlos en la API.
   - [ ] Reemplazar el filtrado local por nombre/categoría por consumo de API con paginación.
   - [ ] Implementar selects encadenados Marca/Modelo/Variante con carga asíncrona.
   - [ ] Sincronizar todos los filtros con la querystring (incluyendo texto y orden).

5. **Validación**
   - [ ] Probar escenarios con y sin filtros de vehículo.
   - [ ] Validar rendimiento con catálogos medianos/grandes.
   - [ ] Ajustar mensajes de UX en "sin resultados" y estados de carga.

---

Este documento define la arquitectura y los contratos de APIs necesarios para implementar el filtro de productos por marca, modelo y variante de vehículo en el marketplace. El siguiente paso será aplicar estos lineamientos en el código (backend y frontend) de forma incremental, validando contra los modelos existentes en `products` y `vehicles`. 
