# Sincronizacion de Atributos de Product

## Objetivo

Este documento describe, atributo por atributo, como se sincroniza `apps.products.models.Product` entre Odoo y Django.

La meta es separar con precision cuatro conceptos que hoy se suelen mezclar:

1. Fuente de verdad
2. Direccion de sincronizacion
3. Frecuencia esperada
4. Particularidades operativas

## Glosario operativo

### Fuente de verdad

Sistema canonico para un dato. Si hay conflicto entre Odoo y Django, gana la fuente de verdad.

### Snapshot catalogo

Lectura periodica de atributos relativamente estables del producto: nombre, referencia, precio, categoria, calidad, lado, imagen, flags de publicacion tecnica.

En una arquitectura optimizada, este snapshot no deberia traer siempre binarios pesados como `image_1920`. Lo correcto es que el catalogo estable viaje liviano y que las imagenes se sincronicen de forma diferencial.

### Sync completa

Proceso Odoo → Django que refresca catalogo, stock agregado y compatibilidades. Hoy lo hace `sync_provider_products()`.

### Sync rapida de stock

Proceso Odoo → Django que solo refresca `total_stock_cached`. Hoy lo hace `sync_provider_stock()`.

### Atributo derivado

Campo que no viene directamente de Odoo sino que se calcula o se construye en Django a partir de otros datos.

### Atributo de integracion

Campo tecnico usado para enlazar entidades entre sistemas. No es parte del catalogo comercial, pero es critico para idempotencia y reconciliacion.

### Denormalizado

Valor guardado en Django para lectura rapida, aunque su origen real este en otro lugar.

### Bridge

Estrategia para vincular dos sistemas que ya tienen datos previos. En categorias, por ejemplo, Django puede tener seeds y luego enlazarlos con el ID real de Odoo.

## Resumen ejecutivo

Para `Product`, la regla dominante es esta:

- Odoo es la fuente de verdad para casi todo el catalogo tecnico del producto.
- Django es la fuente de verdad para atributos puramente web o de experiencia marketplace.
- Algunas relaciones son mixtas: categoria y compatibilidad se leen desde Odoo, pero su persistencia local se optimiza en Django para consulta rapida.

## Matriz atributo por atributo

| Atributo Django | Tipo | Fuente de verdad | Direccion | Frecuencia | Observaciones |
|---|---|---|---|---|---|
| `provider` | integracion | Django | Django → sync scope | al crear/enlazar | Define de que proveedor es el producto y en que `company_id` de Odoo se consulta. |
| `odoo_product_id` | integracion | Odoo | Odoo → Django | sync completa | Ancla primaria para idempotencia de variantes `product.product`. |
| `odoo_template_id` | integracion | Odoo | Odoo → Django | sync completa | Ancla para compatibilidades y campos de plantilla. |
| `name` | catalogo | Odoo | Odoo → Django | sync completa diaria o bajo demanda | Campo comercial principal. No deberia editarse localmente. |
| `reference` | catalogo con regla defensiva | Odoo | Odoo → Django | sync completa diaria o bajo demanda | Viene de `default_code`. Si Odoo duplica referencias dentro del mismo provider, Django usa fallback `ODOO-{id}` para no romper la constraint local. |
| `slug` | derivado web | Django | solo Django | al crear | No se sincroniza con Odoo. Se genera una vez para URLs estables. |
| `product_type` | catalogo tecnico | Odoo | Odoo → Django | sync completa | Viene de `type`. Impacta semantica operativa, no solo visual. |
| `manufacturer_code` | catalogo tecnico | Odoo | Odoo → Django | sync completa | En Odoo el nombre real es `autopart_oem_code`. Django lo renombra a `manufacturer_code`. |
| `description` | catalogo tecnico-comercial | Odoo | Odoo → Django | sync completa | Viene de `description_sale`. |
| `price` | catalogo comercial | Odoo | Odoo → Django | sync completa y tambien cuando cambien listas de precio | Django no deberia ser maestro de precio base si Odoo es canonico. |
| `tax_percent` | politica local | Django | solo Django | muy esporadico | Hoy no se sincroniza desde Odoo. Se comporta como configuracion local del marketplace. |
| `category` | relacion catalogo | Odoo | Odoo → Django | sync completa y verificacion periodica | El producto solo referencia una categoria ya reconciliada en Django. |
| `is_active` | catalogo operativo | Odoo | Odoo → Django | sync completa | Si Odoo desactiva el producto, Django debe reflejarlo. |
| `is_published` | publicacion web | Django | solo Django | segun negocio | No debe sobreescribirse desde Odoo. Es decision editorial/comercial del marketplace. |
| `es_universal` | catalogo tecnico | Odoo | Odoo → Django | sync completa | Viene de `autopart_universal`. Afecta la interpretacion de compatibilidades. |
| `autopart_side` | catalogo tecnico | Odoo | Odoo → Django | sync completa | Viene directo de `autopart_side`. |
| `autopart_quality` | catalogo tecnico | Odoo | Odoo → Django | sync completa | Viene directo de `autopart_quality`. |
| `vehiculos_compatibles` | relacion tecnica | Odoo | Odoo → Django | sync completa o job especifico | No se guarda como lista cruda; se materializa via `CompatibilidadProducto`. |
| `image_url` | derivado CDN | mixto | Odoo → Cloudinary → Django | sync completa, menos frecuente que stock | Odoo guarda la imagen fuente; Django guarda la URL transformada en Cloudinary. |
| `image_cloudinary_id` | integracion CDN | Cloudinary derivado de Odoo | Odoo/Cloudinary → Django | sync completa diferencial | No existe en Odoo; es metadata tecnica local para servir la imagen. |
| `odoo_state` | estado integracion | Django | solo Django | cada sync | No describe negocio del producto sino estado del pipeline local. |
| `total_stock_cached` | denormalizado operativo | Odoo | Odoo → Django | cada 10 a 15 min | Cache agregado para lectura rapida del marketplace. |
| `last_sync_at` | metadata integracion | Django | solo Django | cada sync exitosa | Marca cuando Django refresco el registro, no cuando Odoo lo modifico. |
| `created_at` | metadata local | Django | solo Django | una vez | Sin valor de sincronizacion. |
| `updated_at` | metadata local | Django | solo Django | cada save local | No debe interpretarse como cambio real en Odoo. |


## Grupos de comportamiento

### 1. Atributos de catalogo estable

Campos:

- `name`
- `reference`
- `product_type`
- `manufacturer_code`
- `description`
- `price`
- `autopart_side`
- `autopart_quality`
- `es_universal`
- `is_active`

Comportamiento:

- Deben refrescarse en la sync completa.
- No justifican una frecuencia de 10 minutos salvo que el negocio cambie precios en tiempo casi real.
- En la practica, una frecuencia diaria o varias veces al dia suele bastar.

### 2. Atributos relacionales de catalogo

Campos:

- `category`
- `vehiculos_compatibles`
- `odoo_template_id`

Comportamiento:

- Requieren reconciliacion, no solo copia de valores.
- `category` depende primero de que exista el arbol local de categorias.
- `vehiculos_compatibles` depende de que los vehiculos y variantes ya esten empujados o reconciliados.

### 3. Atributos de stock

Campo:

- `total_stock_cached`

Comportamiento:

- Es el atributo mas sensible a frecuencia.
- Debe refrescarse mas seguido que el resto del catalogo.
- Tiene sentido operativo correrlo cada 10 minutos.
- Es cache local: la verdad sigue siendo Odoo.

### 4. Atributos de imagen

Campos:

- `image_url`
- `image_cloudinary_id`

Comportamiento:

- Odoo guarda la imagen fuente.
- Django no guarda binario; guarda el resultado publicado en CDN.
- No necesitan la misma frecuencia que stock.
- Si falla la subida a Cloudinary, conviene conservar la imagen local previa y no dejar el producto sin imagen por un error transitorio.

### 5. Atributos puramente web o locales

Campos:

- `slug`
- `is_published`
- `tax_percent`
- `odoo_state`
- `last_sync_at`

Comportamiento:

- No deben venir de Odoo.
- Su ciclo de vida responde a necesidades del marketplace o de observabilidad.

## Particularidades importantes

### Categoria

La categoria no es solo un atributo plano del producto.

Tiene tres niveles de comportamiento:

1. Existe como arbol global en Django.
2. Se reconcilia con Odoo mediante `odoo_category_id`.
3. Luego cada producto solo apunta a una categoria ya reconciliada.

Conclusion operativa:

- La sync de categorias debe ejecutarse antes que la de productos.
- La frecuencia puede ser baja frente a stock.
- Una corrida diaria de consistencia tiene sentido.

### Compatibilidad

`vehiculos_compatibles` no se trata como un campo simple porque realmente vive en la tabla intermedia `CompatibilidadProducto`.

Eso implica:

- La verdad esta en Odoo, en `autopart.compatibility`.
- Django materializa la relacion para filtros y detalle de producto.
- Si `es_universal=True`, el frontend o la logica de dominio puede decidir no exigir compatibilidad explicita.

Conclusion operativa:

- Puede sincronizarse junto con catalogo completo.
- No necesita la frecuencia del stock.
- Si el catalogo vehicular cambia mucho, puede ameritar job separado.

### Imagen

La imagen tiene una cadena de sincronizacion distinta:

1. Odoo almacena binario fuente.
2. El sync la lee como `image_1920`.
3. Se sube a Cloudinary.
4. Django guarda `image_url` e `image_cloudinary_id`.

Conclusion operativa:

- La verdad visual sigue naciendo en Odoo.
- Pero el valor almacenado en Django ya es una proyeccion derivada para entrega web.
- No conviene refrescarla con la misma frecuencia que stock.
- El mayor costo no es guardar la URL en Django sino transportar `image_1920` en JSON-RPC y volver a subirla a Cloudinary aunque no haya cambiado.
- La mejora sustancial es volver diferencial la sync de imagen: solo pedir binario cuando el producto es nuevo, no tiene imagen local o existe evidencia de cambio en Odoo.

### Stock

`total_stock_cached` es un cache deliberado.

No representa un inventario independiente del marketplace. Su funcion es:

- responder rapido en listados,
- evitar queries costosas en tiempo real a Odoo,
- reducir N+1 en lectura web.

Conclusion operativa:

- El nombre correcto de este atributo es cache o snapshot de stock, no stock maestro.
- La fuente de verdad real sigue siendo `qty_available` de Odoo.

## Propuesta de frecuencias por grupo

| Grupo | Campos | Frecuencia sugerida |
|---|---|---|
| Stock | `total_stock_cached` | cada 10 minutos |
| Catalogo estable | nombre, referencia, precio, tipo, calidad, lado, fabricante, activo | 1 vez por dia o por ventana nocturna |
| Categorias | arbol global + asignacion a producto | 1 vez por dia |
| Compatibilidades | relacion producto-vehiculo | 1 vez por dia o bajo demanda |
| Imagenes | `image_url`, `image_cloudinary_id` | job separado o fase diferencial dentro de la sync completa nocturna |

## Arquitectura recomendada por ventanas

La estrategia mas sana para este proyecto no es sincronizar todo con la misma frecuencia.

La recomendacion es esta:

### 1. Ventana nocturna por company o por provider

Ejecutar una sync de catalogo estable en lotes, idealmente por `company_id` o por grupos de providers, durante horas de baja carga.

Esa corrida deberia incluir:

- `name`
- `reference`
- `product_type`
- `manufacturer_code`
- `description`
- `price`
- `category`
- `is_active`
- `es_universal`
- `autopart_side`
- `autopart_quality`
- `odoo_product_id`
- `odoo_template_id`
- reconciliacion de productos faltantes en el snapshot

Esa corrida no deberia mezclar siempre el blob de imagen si no hay señal de cambio.

### 2. Ventana diurna de stock

Durante el dia, el unico atributo que realmente justifica una frecuencia corta es `total_stock_cached`.

Eso significa:

- stock cada 10 a 15 minutos,
- sin categorias,
- sin compatibilidades,
- sin imagenes,
- sin recarga completa de catalogo.

### 3. Categorias y compatibilidades como jobs de menor frecuencia

Categorias y compatibilidades no deberian vivir en el mismo ritmo que stock.

- categorias: baja frecuencia y antes de productos,
- compatibilidades: baja frecuencia, nocturna o bajo demanda,
- ambas pueden correr en jobs separados para aislar fallos.

### 4. Imagenes como pipeline diferencial

La sync de imagen no deberia ser "traer `image_1920` para todos los productos en cada corrida".

La arquitectura correcta es:

1. snapshot liviano de catalogo sin binario pesado,
2. deteccion de productos nuevos o con imagen cambiada,
3. solo para esos casos traer `image_1920`,
4. subir a Cloudinary y persistir `image_url` / `image_cloudinary_id`.

## Cuello de botella real de imagen

El cuello de botella principal no esta en el `save()` de Django.

Esta en dos puntos:

1. traer `image_1920` desde Odoo para cada producto, porque viaja como base64 grande dentro del payload JSON-RPC,
2. volver a subir esa misma imagen a Cloudinary aunque no haya cambiado.

Si la imagen no cambio, pedirla otra vez ya es costo inutil aunque luego Cloudinary sobrescriba el mismo `public_id`.

## Mejora arquitectonica sustancial para imagenes

La mejora mas importante es introducir una señal barata de cambio de imagen.

Opciones de mayor a menor solidez:

1. Extender Odoo para exponer un `image_sync_hash`, checksum o `image_write_date` especifico.
2. Usar `write_date` o `__last_update` de `product.product` o `product.template` como heuristica para decidir si vale la pena pedir `image_1920`.
3. Mantener en Django una metadata local de la ultima sync de imagen y solo refrescar imagen para productos nuevos, sin imagen local o modificados recientemente.

Si existe esa señal, la sync completa nocturna puede seguir siendo diaria sin volverse pesada.

## Implementacion recomendada de las reglas de imagen

La regla de decision debe vivir en Django, dentro de `apps/sync/services/products.py`, porque ahi esta la orquestacion del pipeline completo.

La implementacion mas pragmatica es:

1. el snapshot de catalogo no trae `image_1920`,
2. Django pide una metadata liviana remota,
3. Django compara esa metadata contra una version persistida localmente,
4. solo si hay diferencia pide el binario y lo sube a Cloudinary.

Hoy la heuristica implementable sin tocar Odoo es usar `write_date` como version remota barata.

Eso no requiere addon nuevo para funcionar.

Pero la version mas precisa si conviene implementarla en el addon de Odoo, idealmente en `services/odoo/addons/ecomparts_integration/models/products.py`, agregando una señal dedicada de cambio de imagen en `product.template` o `product.product`.

En otras palabras:

- corto plazo: reglas en Django + `write_date` como heuristica,
- mediano plazo: addon Odoo con `image_sync_hash` o `image_write_date` especifico.

## Decision arquitectonica recomendada hoy

Con el contexto actual del proyecto, tu intuicion es correcta: la arquitectura del app `sync` influye mucho en la robustez total del marketplace, especialmente en una vertical de autopartes con multiproveedor, compatibilidades y Odoo como sistema canonico.

La forma correcta de pensarla es esta:

- sync completa de catalogo: baja frecuencia, nocturna y por ventanas,
- stock: alta frecuencia y aislado,
- imagenes: diferenciales, no masivas,
- categorias y compatibilidades: jobs separados y de menor frecuencia,
- reconciliacion: explicita para detectar productos que ya no vienen desde Odoo.

Eso no implica cambiar de raiz todo el modelo actual. Implica endurecer la separacion entre tipos de sync para que cada una sea mas liviana, mas observable y mas segura.

## Observabilidad operativa

Ademas de los logs, conviene persistir el ultimo estado por provider y por fase de sync.

Fases utiles:

- catalogo
- imagenes
- stock
- compatibilidades

Con eso el operador puede distinguir rapido:

- ultima corrida exitosa,
- ultima corrida parcial,
- ultima corrida fallida,
- duracion aproximada,
- metricas basicas de cada fase.

Esa observabilidad no cambia la logica de negocio, pero si mejora mucho la operacion real del pipeline.

## Reglas de decision recomendadas

### Si un atributo cambia mucho

Separarlo en un job propio o incluirlo en una sync frecuente.

### Si un atributo cuesta mucho traerlo

No meterlo en la sync de stock. Imagenes son el mejor ejemplo.

### Si un atributo existe por SEO, UX o control editorial

Mantenerlo local en Django y no traerlo desde Odoo.

### Si un atributo sirve para idempotencia entre sistemas

Tratarlo como atributo de integracion y protegerlo especialmente. `odoo_product_id` y `odoo_template_id` son los casos criticos.

## Estado actual del codigo

Hoy el codigo ya refleja esta separacion en gran parte:

- `sync_provider_catalog_snapshot()` materializa el snapshot de catalogo estable y la reconciliacion base.
- `sync_provider_products()` hace sync completa.
- `sync_provider_stock()` hace sync rapida.
- `category` se resuelve contra un mapa local previamente reconciliado.
- `vehiculos_compatibles` se materializa via `CompatibilidadProducto`.
- `image_url` e `image_cloudinary_id` son derivados de la imagen fuente de Odoo.

Los campos tecnicos de autoparte que deben venir de Odoo en la sync completa son:

- `autopart_oem_code` → `manufacturer_code`
- `autopart_side` → `autopart_side`
- `autopart_quality` → `autopart_quality`
- `autopart_universal` → `es_universal`

## Decision marco

La forma mas sana de pensar `Product` es esta:

- Un solo modelo Django agrupa campos de tres naturalezas distintas: catalogo Odoo, control web local e integracion tecnica.
- La optimizacion correcta no es tratar todos los atributos igual.
- La optimizacion correcta es dividirlos por comportamiento de sincronizacion.

Si se mantiene esa regla, las decisiones de frecuencia, ownership y tolerancia a fallos se vuelven mucho mas claras.