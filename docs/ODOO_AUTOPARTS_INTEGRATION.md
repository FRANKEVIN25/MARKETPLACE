# Módulo Odoo: AutoParts Integration - MyAutoCore

## Objetivo del módulo

Este módulo Odoo (Odoo 18) tiene como objetivo modelar de forma nativa en Odoo la información específica de un negocio de autopartes y sus compatibilidades vehículo–producto, alineada con la estructura del backend Django REST del marketplace.

Puntos clave:
- Gestionar marcas, modelos, motorizaciones y variantes de vehículos de forma normalizada.
- Permitir definir compatibilidades entre autopartes y variantes de vehículo.
- Extender los productos de Odoo con campos propios de repuestos (lado, calidad, códigos OEM, etc.).
- Mantener una sincronización consistente entre los modelos de Odoo y los modelos expuestos por la API Django REST (IDs externos, slugs, restricciones de unicidad).

El módulo está definido en el directorio `services/odoo/addons_disabled/ecomparts_integration` y debe trasladarse a `services/odoo/addons` para estar disponible como addon instalable en la instancia Odoo.

---

## Estructura del módulo

Archivos principales relevantes para el dominio de vehículos y compatibilidades:

- `__manifest__.py`: metadatos del módulo, dependencias y carga de vistas/datos.
- `models/vehicle_models.py`: modelos de datos de vehículos (marcas, modelos, transmisiones, tracciones, motores y variantes).
- `models/products.py` (a crear/completar): extensión de productos Odoo con campos específicos de autopartes y enlace a compatibilidades.
- `models/compatibility.py` (a crear/completar): modelos que representan la relación de compatibilidad entre productos y variantes de vehículo.
- `data/vehicle_variants_seed.xml`: datos iniciales de referencia de marcas, modelos y variantes de vehículos.
- `views/vehicle_views.xml`: vistas árbol/formulario para gestionar el catálogo de vehículos.
- `views/product_views.xml`: vistas de producto extendidas con campos de autopartes y compatibilidades.
- `views/actions.xml` y `views/menus.xml`: acciones y menús para exponer los modelos en la interfaz.

---

## 1. `vehicle_models.py`

Archivo: `services/odoo/addons_disabled/ecomparts_integration/models/vehicle_models.py`

Este archivo define el modelo jerárquico de vehículos y sus atributos técnicos. Es la base para cualquier lógica de compatibilidad.

### 1.1. MarcaVehiculo (`vehiculo.marca`)

Representa la marca de vehículo (Toyota, Honda, etc.).

Campos principales:
- `nombre` (Char, requerido, indexado): nombre visible de la marca.
- `slug` (Char, requerido, único, indexado): identificador URL-friendly alineado con Django.
- `activo` (Boolean, por defecto `True`): permite activar/desactivar la marca.
- `django_external_id` (Char, solo lectura): almacena el identificador externo de la entidad en Django REST (para sincronización).
- `modelo_ids` (One2many → `vehiculo.modelo`): modelos asociados a la marca.

Restricciones:
- `_sql_constraints`: `marca_slug_unique` garantiza que el `slug` sea único.

### 1.2. ModeloVehiculo (`vehiculo.modelo`)

Representa un modelo concreto dentro de una marca (Corolla, Civic, etc.).

Campos principales:
- `nombre` (Char, requerido, indexado): nombre base del modelo.
- `slug` (Char, requerido, único, indexado): slug alineado con el modelo equivalente en Django.
- `activo` (Boolean): modelo activo/inactivo.
- `marca_id` (Many2one → `vehiculo.marca`, requerido, indexado): relación con la marca.
- `django_external_id` (Char, solo lectura): ID externo Django REST.
- `nombre_mostrar` (Char, compute, store, indexado): nombre completo calculado, por ejemplo "Toyota Corolla".
- `variante_ids` (One2many → `vehiculo.variante`): variantes asociadas al modelo.

Restricciones:
- `marca_modelo_unique`: evita duplicar `nombre` dentro de una misma `marca_id`.
- `modelo_slug_unique`: slug único por modelo.

### 1.3. TransmisionVehiculo (`vehiculo.transmision`)

Modela los tipos de transmisión.

Campos principales:
- `tipo` (Selection): valores como `MT`, `AT`, `CVT`, `DCT`, `RED`, `NA`.
- `velocidades` (Integer): número de velocidades (opcional).
- `django_external_id` (Char, solo lectura): ID externo Django.
- `display_name` (Char, compute, store): etiqueta calculada, por ejemplo "AT 6V".

Restricciones:
- `transmision_unique`: combinación única de `tipo` + `velocidades`.

### 1.4. TraccionVehiculo (`vehiculo.traccion`)

Modela los tipos de tracción.

Campos principales:
- `tipo` (Selection): `4x2`, `4x4`, `AWD`.
- `django_external_id` (Char, solo lectura).
- `display_name` (Char, compute, store).

Restricciones:
- `traccion_unique`: `tipo` único.

### 1.5. MotorVehiculo (`vehiculo.motor`)

Modela las características del motor.

Campos principales:
- `combustible` (Selection): `GSL`, `Hib`, `Ele`, `Dis`.
- `cilindrada_cc` (Integer): cilindrada en cc.
- `codigo_motor` (Char): código de motor (G4FG, 1GD-FTV, etc.).
- `tecnologia` (Char): descripción de la tecnología (VVT-i, Turbo, etc.).
- `django_external_id` (Char, solo lectura).
- `nombre` (Char, compute, store, indexado): descripción legible combinando los campos anteriores (ejemplo: `1.6L (G4FG) D-CVVT`).

Restricciones:
- `motor_unique`: combinación única de `combustible`, `cilindrada_cc`, `codigo_motor`, `tecnologia`.

### 1.6. VarianteVehiculo (`vehiculo.variante`)

Representa una variante específica dentro de un modelo (año, motor, transmisión, tracción).

Campos principales:
- `modelo_id` (Many2one → `vehiculo.modelo`, requerido, indexado): modelo base.
- `motor_id` (Many2one → `vehiculo.motor`): motor asociado.
- `transmision_id` (Many2one → `vehiculo.transmision`): transmisión asociada.
- `traccion_id` (Many2one → `vehiculo.traccion`): tracción asociada.
- `anio_desde` (Integer, requerido, indexado): año inicial de la variante.
- `anio_hasta` (Integer, opcional, indexado): año final; si está vacío, la variante sigue vigente.
- `django_external_id` (Char, solo lectura): ID externo Django.
- `nombre` (Char, compute, store, indexado): descripción completa de la variante, incluyendo modelo, motor, transmisión, tracción y rango de años.

Restricciones y validaciones:
- `_sql_constraints` `variante_unique`: combinación única de `modelo_id`, `motor_id`, `transmision_id`, `traccion_id`, `anio_desde`, `anio_hasta`.
- `@api.constrains('anio_desde', 'anio_hasta')`: asegura que `anio_hasta` no sea menor que `anio_desde`.

### 1.7. Datos semilla de vehículos

Archivo: `services/odoo/addons_disabled/ecomparts_integration/data/vehicle_variants_seed.xml`

Este archivo carga datos iniciales de ejemplo para:
- Marcas: Toyota, Honda, Ford, Hyundai, Tesla.
- Modelos por marca (Corolla, RAV4, Hilux, Civic, CR-V, etc.).
- Transmisiones, tracciones y motores de referencia.
- Variantes de vehículo (combinaciones modelo + motor + transmisión + tracción + rango de años).

Sirve como catálogo base para pruebas de UX y para validar las reglas de compatibilidad.

---

## 2. `products.py` (diseño propuesto)

Archivo previsto: `services/odoo/addons_disabled/ecomparts_integration/models/products.py`

Objetivo: extender los modelos estándar de productos (`product.template` y/o `product.product`) para incluir campos específicos de autopartes y el enlace con las compatibilidades vehículo–producto.

### 2.1. Extensión de `product.template`

Campos recomendados:
- `autopart_oem_code` (Char): código OEM de fabricante.
- `autopart_side` (Selection): lado del vehículo (`left`, `right`, `front`, `rear`, `both`).
- `autopart_quality` (Selection): calidad del repuesto (`original`, `oem`, `aftermarket_premium`, `aftermarket_standard`).
- `autopart_notes` (Text): notas técnicas específicas de montaje/instalación.
- un atributo booleando para definir si un productos es universal o no.

Relaciones con compatibilidades:
- `compatibility_ids` (One2many → modelo en `compatibility.py`): lista de compatibilidades vehículo–producto.

Aspectos de sincronización con Django REST:
- Mantener campos alineados con el modelo de producto del backend Django (por ejemplo, slugs, códigos de producto, IDs externos si aplica).
- Definir, si se requiere, un `django_external_id` en el modelo de producto para vincular cada plantilla con su representación en Django.

### 2.2. Vistas de producto (`product_views.xml`)

Vistas esperadas (ya previstas en el manifest):
- Extender la vista formulario de `product.template` para:
  - Mostrar un apartado "Compatibilidad de vehículos" con un one2many a compatibilidades.
  - Mostrar los campos de lado/calidad del repuesto, código OEM y notas.
- Añadir filtros de búsqueda predefinidos (filtros rápidos) en la vista árbol para productos de autopartes.

---

## 3. `compatibility.py` (diseño propuesto)

Archivo previsto: `services/odoo/addons_disabled/ecomparts_integration/models/compatibility.py`

Objetivo: representar de forma explícita la relación de compatibilidad entre una autoparte (producto) y una o varias variantes de vehículo.

### 3.1. Modelo principal de compatibilidad

Modelo sugerido: `autopart.compatibility`.

Campos clave:
- `product_tmpl_id` (Many2one → `product.template`, requerido, indexado): plantilla de producto (autoparte) a la que aplica la compatibilidad.
- `variant_id` (Many2one → `vehiculo.variante`, requerido, indexado): variante de vehículo compatible.
- `fitment_notes` (Text): notas de instalación (ej: "solo versión 4x4", "requiere kit adicional").
- `active` (Boolean): activar/desactivar una compatibilidad puntual sin perder histórico.

Restricciones e índices sugeridos:
- `_sql_constraints` con combinación única `product_tmpl_id` + `variant_id` para evitar duplicados.
- Índices sobre `variant_id` para acelerar búsquedas masivas.

### 3.2. Relación con Django REST (pendiente)

La compatibilidad se debe reflejar en el backend Django REST de forma que:
- Django pueda preguntar a Odoo (o recibir sincronización) sobre qué vehículos son compatibles con un producto concreto.

Sin embargo, **la implementación concreta de la sincronización de compatibilidades con Django REST queda pendiente**, porque todavía no se han definido los archivos y flujos exactos de sincronización de productos en el backend.

Por ahora:
- Las compatibilidades se crean y mantienen en Odoo.
- Django seguirá consumiendo los productos y catálogos de Odoo a través de los mecanismos ya existentes.
- Cuando se definan los archivos/procesos de sincronización específicos, se actualizará este documento con el detalle técnico (endpoints, modelos Django involucrados y mapeos de campos).

---

## 4. Vistas y navegación en Odoo

### 4.1. Vistas de vehículos (`vehicle_views.xml`)

Acciones y vistas previstas (según `__manifest__.py`):
- Vistas árbol y formulario para cada modelo definido en `vehicle_models.py`:
  - `vehiculo.marca`: mantenimiento de marcas.
  - `vehiculo.modelo`: mantenimiento de modelos por marca.
  - `vehiculo.motor`, `vehiculo.transmision`, `vehiculo.traccion`: catálogos técnicos.
  - `vehiculo.variante`: combinación final de modelo + motor + transmisión + tracción + años.
- Búsqueda avanzada por marca, modelo, rango de años, motorización, transmisión y tracción.

### 4.2. Vistas de productos (`product_views.xml`)

- Extensiones sobre `product.template` para mostrar los campos de autopartes y la pestaña de compatibilidades.
- Listados filtrados para localizar rápidamente repuestos por marca/modelo/variante de vehículo.

### 4.3. Menús y acciones (`actions.xml`, `menus.xml`)

- Menús bajo una sección tipo "Autoparts / Vehículos" para la administración del catálogo de vehículos.
- Menús bajo "Autoparts / Compatibilidades" para revisar y mantener las compatibilidades.
- Acciones de ventana configuradas para abrir las vistas árbol/formulario de cada modelo.

---

## 5. Notas sobre sincronización con Django REST

- **Odoo 18**: el módulo está pensado para funcionar sobre Odoo 18 y Python 3.10+, según `__manifest__.py`.
- **IDs externos**: los campos `django_external_id` presentes en varios modelos (`vehiculo.marca`, `vehiculo.modelo`, `vehiculo.transmision`, `vehiculo.traccion`, `vehiculo.motor`, `vehiculo.variante`) son la clave para relacionar cada registro Odoo con su homólogo en Django.
- **Slugs**: los campos `slug` en marcas y modelos deben mantenerse alineados con los slugs usados por la API pública del marketplace (`/api/v1/vehicles/public/marcas/`, etc.) para evitar duplicidad de identificadores.
- **Flujos de sincronización**: pendientes de definición detallada. Actualmente solo se están consumiendo productos desde Odoo hacia Django; los ajustes específicos para compatibilidades se documentarán más adelante.

---

## 6. Pasos para activar el módulo en Odoo

1. Mover el módulo desde `services/odoo/addons_disabled/ecomparts_integration` a `services/odoo/addons/ecomparts_integration`.
2. Reiniciar el contenedor/servicio de Odoo para que detecte el nuevo addon.
3. Desde la interfaz de Odoo (Apps):
   - Actualizar la lista de aplicaciones.
   - Instalar **"AutoParts Integration - MyAutoCore"**.
4. Verificar:
   - Que los menús de vehículos y compatibilidades aparecen.
   - Que los datos semilla de vehículos han sido cargados.
   - Que las vistas de producto muestran los campos personalizados una vez implementados `products.py` y `compatibility.py`.

---

## 7. Roadmap de implementación

Este es el roadmap propuesto para implementar el módulo de autopartes y compatibilidades en Odoo 18, coordinado con el backend Django REST.

1. **Preparación del módulo Odoo**
  - Mover `ecomparts_integration` desde `services/odoo/addons_disabled` a `services/odoo/addons`.
  - Verificar que `__manifest__.py` es válido para Odoo 18 y que las dependencias (`base`, `product`, `stock`) están disponibles.

2. **Modelado de vehículos (ya implementado)**
  - Revisar y, si es necesario, ajustar `vehicle_models.py`.
  - Validar que los datos semilla de `vehicle_variants_seed.xml` cargan correctamente.

3. **Implementar `products.py`**
  - Extender `product.template` con los campos definidos en la sección 2.1 (código OEM, lado, calidad, notas, flag universal/no universal).
  - Añadir el `One2many` hacia el modelo de compatibilidades.
  - Actualizar `models/__init__.py` del módulo para incluir la nueva clase.

4. **Implementar `compatibility.py`**
  - Crear el modelo `autopart.compatibility` según la sección 3 (relación producto–variante, notas, activo, constraints de unicidad).
  - Añadir índices y restricciones SQL recomendadas.
  - Actualizar `models/__init__.py` para cargar el nuevo modelo.

5. **Vistas y menús en Odoo**
  - Implementar `vehicle_views.xml` con vistas árbol/formulario para marcas, modelos, motores, transmisiones, tracciones y variantes.
  - Implementar `product_views.xml` extendiendo el formulario de `product.template` con los campos de autopartes y la pestaña de compatibilidades.
  - Implementar `actions.xml` y `menus.xml` para exponer los modelos en la interfaz (menús de Vehículos y Compatibilidades).

6. **Seguridad y acceso**
  - Crear/actualizar `security/ir.model.access.csv` para los modelos nuevos (`autopart.compatibility`) y, si aplica, para los modelos de vehículos.
  - Definir qué grupos de usuario pueden crear/editar compatibilidades, y quién solo puede consultarlas.

7. **Pruebas funcionales en Odoo**
  - Instalar el módulo en un entorno de pruebas.
  - Crear productos de ejemplo con distintos valores de lado/calidad/universal.
  - Definir compatibilidades contra variantes de vehículos y verificar la UX en las vistas.

8. **Integración con Django REST (fase posterior)**
  - Identificar los modelos y endpoints de Django que participan en la sincronización de productos y compatibilidades.
  - Diseñar y documentar el flujo de sincronización (dirección, frecuencia, manejo de conflictos).
  - Implementar los ajustes necesarios en el backend Django y en Odoo.

9. **Documentación y handoff**
  - Actualizar este documento con los detalles finales de sincronización.
  - Dejar ejemplos de uso (escenarios típicos de alta de autopartes y definición de compatibilidades).
