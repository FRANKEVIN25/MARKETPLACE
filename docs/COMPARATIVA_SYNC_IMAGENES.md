# Comparativa: Flujo actual vs Flujo async inteligente — Sync de imágenes

## Referencia de código base

| Elemento | Archivo |
|---|---|
| Orquestación sync actual | `services/backend/apps/sync/services/products.py` |
| Tareas Celery activas | `services/backend/apps/sync/tasks.py` |
| Conector Odoo (lectura) | `services/backend/apps/sync/connector/products.py` |
| Modelo addon Odoo | `services/odoo/addons/ecomp/models/products.py` |

---

## Flujo actual — Sync pull periódico con diferencial por `x_image_version` ✅ implementado

### Arquitectura

```
Odoo filestore
    ↓  JSON-RPC (image_1920 base64)
Django Celery worker
    ↓  base64.b64decode + cloudinary.uploader.upload (síncrono)
Cloudinary CDN
    ↓  secure_url
Django Product.image_url / image_cloudinary_id
    ↓  API REST
Svelte frontend
```

### Paso a paso

1. **Celery Beat** dispara `sync_all_active_providers()` o `sync_provider_products(provider_id)`.
2. `sync_provider_catalog_snapshot()` llama a `odoo.get_products()` con `include_inactive=True`. En modo `include_images=False` (default actual de la sync nocturna), el campo `image_1920` **no viaja** en este payload.
3. Se corre `sync_provider_product_images()` como fase separada:
   - Primer round-trip liviano: pide solo `['id', 'default_code', 'x_image_version']` para todos los productos.
   - Compara `x_image_version` remoto contra `odoo_image_version` local para identificar *candidatos*. `x_image_version` solo cambia cuando `image_1920` cambia — no cuando cambia precio, descripción u otros campos.
   - Segundo round-trip pesado: llama a `get_products_by_ids(candidate_ids, fields=['id', 'default_code', 'x_image_version', 'image_1920'])` solo para los candidatos.
4. Para cada candidato: `_upload_image()` decodifica `image_b64` y llama a `cloudinary.uploader.upload()` **de forma síncrona** dentro del worker.
5. Persiste `image_url`, `image_cloudinary_id`, `odoo_image_version` con `bulk_update`.

### Puntos clave del código actual

```python
# addon Odoo — ecomp/models/products.py
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_image_version = fields.Char(
        string='Image Version',
        copy=False,
        index=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('image_1920'):
                vals['x_image_version'] = fields.Datetime.now().strftime('%Y%m%d%H%M%S%f')
        return super().create(vals_list)

    def write(self, vals):
        if 'image_1920' in vals:
            vals['x_image_version'] = fields.Datetime.now().strftime('%Y%m%d%H%M%S%f')
        return super().write(vals)

# Django — sync_provider_product_images() — decisión de candidatos
remote_version = remote_product.get('x_image_version') or None
if force or _product_needs_image_refresh(local_product, remote_version):
    candidate_ids.append(remote_odoo_id)

# _product_needs_image_refresh()
def _product_needs_image_refresh(product, remote_version):
    if not product.image_url or not product.image_cloudinary_id:
        return True          # sin imagen local → siempre candidato
    if not remote_version:
        return False
    return product.odoo_image_version != remote_version  # señal exacta de imagen
```

> **Nota de primera ejecución**: productos existentes en Odoo antes del despliegue
> tienen `x_image_version = NULL`. Django los trata como candidatos en la primera
> sync, estableciendo la línea base. A partir de ahí solo se activan si la imagen
> real cambia.

---

## Flujo propuesto — Async push desde Odoo + sync inteligente

### Arquitectura

```
Odoo filestore
    ↓  write() override detecta cambio de imagen
Odoo queue_job (worker async interno)
    ↓  lee image_1920, calcula hash, verifica cambio real
Cloudinary CDN  (upload directo desde Odoo worker)
    ↓  secure_url
Odoo x_cloudinary_url + x_image_hash + x_needs_sync=True
    ↓  JSON-RPC liviano (solo URL, sin binario)
Django Celery worker  (filtra por x_needs_sync=True)
    ↓  product.image_url = x_cloudinary_url
Django Product.image_url
    ↓  API REST
Svelte frontend
```

### Paso a paso

1. Vendor sube imagen en Odoo (campo `image_1920` en `product.template`).
2. Override de `write()` (o `create()`) en el addon detecta cambio en `image_1920`.
3. Odoo encola un job async (OCA `queue_job`): `upload_image_to_cloudinary(product_id)`.
4. Worker Odoo ejecuta el job:
   - Lee `image_1920` (base64).
   - Calcula hash SHA-256 de los bytes decodificados.
   - Compara contra `x_image_hash` almacenado localmente.
   - Si no cambió: descarta sin hacer nada.
   - Si cambió: sube a Cloudinary, guarda `x_cloudinary_url`, `x_image_hash`, `x_image_status = 'done'`.
5. Odoo setea `x_needs_sync = True` en el registro del producto.
6. Django Celery worker ejecuta sync liviana filtrando por `x_needs_sync = True`:
   - Round-trip único: `search_read` con dominio `[('x_needs_sync', '=', True)]`.
   - Payload: `['id', 'default_code', 'x_cloudinary_url']`. Sin `image_1920`.
7. Django actualiza `product.image_url = x_cloudinary_url`.
8. Odoo resetea `x_needs_sync = False` tras confirmar (o Django lo resetea por RPC).
9. Frontend consume directamente la URL CDN.

---

## Comparativa técnica

### Transferencia de datos

| Dimensión | Flujo actual | Flujo propuesto |
|---|---|---|
| Payload principal catálogo | liviano (sin `image_1920`) | liviano (sin `image_1920`) |
| Payload sync de imágenes | `image_1920` base64 (~500 KB–2 MB por producto) para todos los candidatos | Solo URL string (~80 bytes por producto) |
| Round-trips JSON-RPC por ciclo de imagen | 2 (metadata + binario) | 1 (solo productos con `x_needs_sync=True`) |
| Upload a Cloudinary | Django worker (síncrono, bloquea el worker) | Odoo worker async (no bloquea Django) |

### Deduplicación

| Criterio | Flujo actual | Flujo propuesto |
|---|---|---|
| Señal de cambio | `x_image_version` en `product.template` — solo cambia cuando `image_1920` cambia, sin importar otros campos | Hash SHA-256 del binario real — solo cambia si la imagen realmente cambió |
| Falsos positivos de subida | Eliminados: price, description u otros campos no actualizan `x_image_version` | Casi nulos: el hash garantiza que solo sube si el contenido cambió |
| Subida redundante a Cloudinary | Minimizada: solo candidatos con `x_image_version` diferente | Prevenida por comparación de hash en Odoo antes del upload |

### Resiliencia y aislamiento de fallos

| Escenario | Flujo actual | Flujo propuesto |
|---|---|---|
| Cloudinary lento / timeout | Bloquea el Celery worker de Django; puede afectar la sync del catálogo completo si se corre acoplado | Falla aislada en el worker async de Odoo; el catálogo Django no se bloquea |
| Cloudinary rechaza la imagen | `_resolve_image_fields_for_sync` devuelve `refreshed=False`; se conserva imagen previa (correcto) | hash/status persisten en Odoo sin `x_cloudinary_url`; Django detecta ausencia y conserva la previa |
| Odoo async worker caído | No aplica | `x_needs_sync` queda en cola; cuando el worker se recupera, reintenta automáticamente |
| Django worker caído | Toda la sync para; imágenes tampoco se actualizan | Imágenes ya están en Cloudinary con URL en Odoo; solo falla el write en Django, que se reintenta |
| Odoo sin Cloudinary route | No aplica en Odoo | Upload falla en Odoo worker; `x_image_status = 'failed'`; Django nunca recibe URL rota |

### Escalabilidad

| Dimensión | Flujo actual | Flujo propuesto |
|---|---|---|
| Costo por 1.000 productos con 1 imagen cambiada | Hasta 1.000 download base64 (~1 GB) + 1.000 uploads a Cloudinary desde Django | 1 hash mismatch → 1 upload desde Odoo worker; Django recibe 1 URL |
| Escalar a 10 providers con 5.000 productos c/u | 50.000 evaluaciones de candidatos + potencial de miles de transfers binarios por sync | Solo los productos con `x_needs_sync=True` en la ventana; el volumen real de cambios suele ser <1% |
| Worker Django desacoplado de I/O pesado | No: el worker hace I/O binario a Cloudinary | Sí: el worker Django solo escribe strings en la DB |

### Complejidad operativa

| Dimensión | Flujo actual | Flujo propuesto |
|---|---|---|
| Partes adicionales a mantener | Ninguna nueva | OCA `queue_job` en Odoo, worker async Odoo, campos custom `x_cloudinary_url / x_image_hash / x_image_status / x_needs_sync` en `product.template` |
| Credenciales Cloudinary en | Django únicamente | Odoo worker **y** posiblemente Django (si hay fallback) |
| Puntos de observabilidad | `SyncLog` Django por fase | `SyncLog` Django + estado de queue_job Odoo + `x_image_status` por producto |
| Rollback / migraciones | Solo Django migrations | Django migrations + `__manifest__.py` addon Odoo + field migration en Odoo |
| Testing | Unit tests en Django aislados de Odoo | Unit tests en Django + tests del worker Odoo (requiere mock de `cloudinary` en Odoo) |

---

## Análisis de riesgos específicos del flujo propuesto

### 1. `queue_job` es una dependencia OCA externa

El flujo propuesto requiere la OCA `queue_job` (o `base_setup` equivalente) instalada en el Odoo del provider. Si el provider no tiene ese módulo o la versión es incompatible, todo el flujo async no existe. El flujo actual no tiene esa dependencia.

**Mitigación**: implementar un fallback con `threading.Thread` simple en Odoo si `queue_job` no está disponible, o bien con un cron de Odoo que procese un modelo propio de cola (`ecomparts.image.queue`).

### 2. Gestión del flag `x_needs_sync`

El reseteo de `x_needs_sync = False` debe ser atómico con la confirmación del write en Django. Si Django falla después de leer pero antes de confirmar el reseteo, el producto se re-sincroniza en el siguiente ciclo (safe, idempotente). Pero si el reseteo ocurre antes del write en Django y Django falla, se pierde el cambio hasta el próximo ciclo forzado.

**Mitigación**: Django resetea el flag **después** de confirmar el write local, nunca antes.

### 3. Credenciales Cloudinary en Odoo

Poner credenciales Cloudinary dentro del addon Odoo introduce una nueva superficie de configuración por provider. Si un provider tiene su propio Odoo (multiproveedor), los credentials no son globales.

**Mitigación**: las credenciales Cloudinary se configuran en `ir.config_parameter` del addon y se leen desde `odoo.conf` como variable de entorno, no hardcodeadas.

### 4. Observabilidad fragmentada

El estado del pipeline de imagen queda repartido entre Odoo (`x_image_status`) y Django (`SyncLog`). Un fallo en el worker Odoo puede quedar invisible para el operador de Django.

**Mitigación**: Django persiste en `SyncLog` no solo si el write fue exitoso sino también si el `x_image_status` que leyó era `'failed'` o `'pending'`, para poder alertar desde el panel de administración.

---

## Tabla resumen de decisión

| Criterio | Flujo actual | Flujo propuesto | Ventaja |
|---|---|---|---|
| Transferencia binaria entre sistemas | Sí (image_1920 base64) | No | Propuesto |
| Deduplicación real de subidas | Heurística (write_date) | Exacta (SHA-256) | Propuesto |
| Aislamiento de fallos Cloudinary | Bajo (bloquea worker Django) | Alto (falla en Odoo worker) | Propuesto |
| Partes del sistema a operar | 2 (Django + Odoo) | 3+ (Django + Odoo + queue worker) | Actual |
| Complejidad de implementación | Baja (ya existe) | Alta (addon, campos, worker, tests) | Actual |
| Escalabilidad con muchos productos | Limitada por transfer binario | Alta (solo URLs en steady state) | Propuesto |
| Dependencias externas nuevas | Ninguna | `queue_job` OCA (o equivalente) | Actual |
| Observabilidad unificada | Centralizada en Django | Distribuida Odoo + Django | Actual |
| Falsos positivos de sync | Eliminados (x_image_version exacto) | Mínimos (hash) | Empate |
| Resiliencia si Django worker cae | Imagen no actualizada | Imagen ya en CDN, solo falta el write | Propuesto |

---

## Veredicto y recomendación

El flujo propuesto es arquitectónicamente superior para escala. La eliminación del transfer binario entre sistemas es el cambio más significativo: `image_1920` en base64 puede pesar entre 500 KB y 3 MB por producto y hoy viaja en JSON-RPC para cada candidato, lo que convierte una sync de imágenes de 500 productos en varios cientos de MB de payload.

Sin embargo, tiene un costo de implementación real y nuevas dependencias operativas que no deben subestimarse.

### Estado de implementación

#### ✅ Fase 1 — Completada

Las dos mejoras críticas del flujo actual están implementadas:

1. **`x_image_version` en el addon Odoo** (`ecomp/models/products.py`): campo `Char` con `index=True` y `copy=False` en `product.template`. Los overrides de `create()` y `write()` lo actualizan únicamente cuando `image_1920` cambia, con precisión de microsegundos (`%Y%m%d%H%M%S%f`). Esto elimina completamente los falsos positivos que generaba `write_date`.

2. **`sync_provider_product_images()` usa `x_image_version`** (`services/products.py`): los dos round-trips JSON-RPC ahora piden `x_image_version` en lugar de `write_date`. La lógica de `_product_needs_image_refresh()` no cambió; el beneficio viene de que la señal es ahora exacta.

#### Fase 2 — Opcional / mediano plazo: flujo async desde Odoo

Aplicar solo si el volumen de imágenes o la carga de los workers Django se convierte en un cuello de botella real en producción. Requiere:

1. Agregar `x_cloudinary_url`, `x_image_hash`, `x_image_status`, `x_needs_sync` en el addon.
2. Implementar override de `write()` con encolado async (OCA `queue_job` o cron propio de Odoo).
3. Worker Odoo que suba a Cloudinary y actualice los campos custom.
4. Modificar `sync_provider_product_images()` para filtrar por `x_needs_sync=True` y leer `x_cloudinary_url` en lugar de `image_1920`.
5. Reseteo atómico del flag tras write confirmado en Django.
6. Extender `SyncLog` para registrar `x_image_status` leído desde Odoo.

Esta fase solo tiene sentido cuando la Fase 1 ya opera estable en producción y el transfer de `image_1920` para candidatos reales sigue siendo alto.
