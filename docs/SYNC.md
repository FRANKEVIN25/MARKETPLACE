# App `sync` + `ecomparts` - Guia resumida

## 1. Que resuelve esta parte del sistema

La app `sync` concentra la integracion entre Django y Odoo.

Su trabajo se divide en cuatro bloques:

- transporte hacia Odoo por JSON-RPC
- servicios de sincronizacion y aprovisionamiento
- tareas Celery para ejecucion asincrona
- observabilidad basica por provider y por fase

El paquete `ecomparts` no contiene logica de negocio de sync, pero si gobierna la
operacion automatica:

- carga settings de Django
- inicializa Celery
- define el horario de Beat
- expone la configuracion efectiva que usan worker y beat

## 2. Estructura actual

```text
apps/sync/
├── connector/
│   ├── base.py
│   ├── companies.py
│   ├── users.py
│   ├── products.py
│   ├── vehicles.py
│   └── compatibility.py
├── services/
│   ├── provisioning.py
│   ├── categories.py
│   ├── products.py
│   ├── compatibility.py
│   ├── orders.py
│   └── observability.py
├── management/commands/
│   ├── setup_odoo.py
│   ├── push_categories.py
│   ├── sync_products.py
│   ├── sync_images.py
│   ├── sync_stock.py
│   ├── sync_compatibility.py
│   ├── sync_delivery_status.py
│   ├── sync_celery_beat.py
│   └── upgrade_odoo_module.py
├── models.py
├── tasks.py
├── odoo_connector.py
└── __init__.py

ecomparts/
├── settings.py
├── beat_schedule.py
├── celery.py
├── urls.py
└── ...
```

## 3. Como se reparte la responsabilidad

### `connector/`

Es la capa de transporte pura contra Odoo. No decide negocio ni persiste modelos Django.

- `base.py`: autenticacion, `requests.Session`, `execute_kw`, reautenticacion
- `products.py`: lectura de productos, stock y categorias Odoo
- `vehicles.py`: push de jerarquia vehicular Django -> Odoo
- `compatibility.py`: lectura de `autopart.compatibility` y `vehiculo.variante`
- `companies.py` y `users.py`: alta tecnica de company y users en Odoo

La clase final `OdooConnector` compone estos mixins y `odoo_connector.py` se mantiene
como shim de compatibilidad para imports viejos.

### `services/`

Aqui vive la logica real.

- `provisioning.py`: crea provider en Django y su company/user en Odoo
- `categories.py`: empuja y resuelve categorias globales
- `products.py`: snapshot de catalogo, sync diferencial de imagenes, sync completa y stock rapido
- `compatibility.py`: sincroniza compatibilidades producto <-> vehiculo en lote
- `orders.py`: integra ordenes y estados con Odoo
- `observability.py`: actualiza estado de sync por provider y por fase

### `tasks.py`

Las tareas Celery son delgadas: reciben argumentos y delegan al servicio correcto.

Tareas mas importantes hoy:

- `sync_all_active_providers`: dispara snapshot de catalogo para todos los providers, sin compatibilidades
- `sync_all_compatibility`: dispara la sync separada de compatibilidades
- `sync_all_stock`: dispara la sync rapida de stock
- `sync_provider_products`: sync por provider con bandera `include_compatibility`
- `sync_provider_compatibility`: sync puntual de compatibilidades por provider
- `create_provider_with_odoo_setup`: onboarding tecnico del provider

### `models.py`

La app `sync` ya no es solo servicios y tareas. Ahora tambien tiene persistencia propia:

- `ProviderSyncState`: guarda ultimo estado de sync por provider y tipo (`catalog`, `images`, `stock`, `compatibility`)

Esto permite dejar trazabilidad simple de:

- ultima ejecucion
- duracion
- error mas reciente
- metricas resumidas

## 4. Flujos principales actuales

### Catalogo base

```text
Beat/CLI -> tasks.sync_all_active_providers
         -> tasks.sync_provider_products(provider_id, include_compatibility=False)
         -> services.products.sync_provider_products()
         -> snapshot catalogo + fase diferencial de imagenes
```

### Compatibilidades

```text
Beat/CLI -> tasks.sync_all_compatibility
         -> tasks.sync_provider_compatibility(provider_id)
         -> services.compatibility.sync_provider_compatibility()
         -> Odoo autopart.compatibility -> Django CompatibilidadProducto
```

### Stock rapido

```text
Beat/CLI -> tasks.sync_all_stock
         -> tasks.sync_provider_stock(provider_id)
         -> services.products.sync_provider_stock()
```

### Onboarding de provider

```text
Admin/API -> tasks.create_provider_with_odoo_setup
          -> services.provisioning.create_provider_with_odoo_setup()
          -> Provider Django + Company Odoo + User Odoo
```

## 5. Relacion con `ecomparts`

La parte importante para operacion automatica no esta solo en `apps/sync`. Tambien depende de
los archivos del paquete `ecomparts`.

### `ecomparts/settings.py`

Define la configuracion base:

- broker y backend de Celery
- timezone
- variables de horario para sync
- `CELERY_BEAT_SCHEDULE` base del proyecto

Variables de sync relevantes:

```python
SYNC_STOCK_INTERVAL_MINUTES
SYNC_CATALOG_SCHEDULE_HOUR
SYNC_CATALOG_SCHEDULE_MINUTE
SYNC_COMPATIBILITY_SCHEDULE_HOUR
SYNC_COMPATIBILITY_SCHEDULE_MINUTE
```

Estas constantes se resuelven desde variables de entorno con fallback local en `settings.py`.

### `ecomparts/beat_schedule.py`

Es la fuente central del horario operativo de sync.

`get_periodic_schedule(base_schedule=None)` toma el schedule base del proyecto y le agrega:

- `sync-odoo-products-nightly`
- `sync-odoo-compatibility-nightly`
- `sync-odoo-stock-interval`
- `recalculate-workshop-scores`

La ventaja es que el horario de sync queda concentrado en un solo lugar y reutilizable.

### `ecomparts/celery.py`

Inicializa Celery y carga el schedule efectivo:

```python
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(beat_schedule=get_periodic_schedule(getattr(app.conf, 'beat_schedule', {})))
```

Eso significa que Celery arranca con:

- la configuracion base de `settings.py`
- mas el schedule enriquecido por `beat_schedule.py`

## 6. Como se conecta esto con `django_celery_beat`

En este proyecto Beat no corre solo con el diccionario en memoria. Corre con `DatabaseScheduler`.

En `docker-compose.yml`, `celery_beat` arranca asi:

```sh
python manage.py sync_celery_beat && \
celery -A ecomparts beat --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Eso tiene una consecuencia importante:

- el horario se define en codigo
- luego `sync_celery_beat` lo sincroniza a la tabla de `django_celery_beat`
- despues Beat agenda usando la base de datos

Si cambias horarios en `settings.py` o `beat_schedule.py`, el contenedor `celery_beat`
debe volver a ejecutar `sync_celery_beat` para reflejar esos cambios en la base.

## 7. Que hace `sync_celery_beat`

El comando `apps/sync/management/commands/sync_celery_beat.py` traduce el schedule en codigo
 a registros de `django_celery_beat`.

Hace tres cosas:

- lee `get_periodic_schedule(...)`
- crea o actualiza `PeriodicTask`, `CrontabSchedule` e `IntervalSchedule`
- limpia tareas legacy que ya no deben seguir vivas

Esto evita el problema clasico de tener:

- horarios editados en Python
- pero `PeriodicTask` viejas todavia activas en base de datos

## 8. Comandos utiles

```bash
# Sync completa de catalogo: snapshot + imagenes + compatibilidades
docker exec -it ecomparts-backend python manage.py sync_products

# Sync de catalogo sin compatibilidades: snapshot + imagenes
docker exec -it ecomparts-backend python manage.py sync_products --skip-compat

# Solo imagenes
docker exec -it ecomparts-backend python manage.py sync_images
docker exec -it ecomparts-backend python manage.py sync_images --provider-id=3
docker exec -it ecomparts-backend python manage.py sync_images --force

# Solo compatibilidades
docker exec -it ecomparts-backend python manage.py sync_compatibility

# Solo stock
docker exec -it ecomparts-backend python manage.py sync_stock

# Sincronizar tareas periodicas hacia django_celery_beat
docker exec -it ecomparts-backend python manage.py sync_celery_beat
```

## 9. Donde tocar segun el cambio

| Necesidad | Archivo principal |
|---|---|
| Cambiar horario de catalogo, compatibilidades o stock | `ecomparts/settings.py` y `ecomparts/beat_schedule.py` |
| Hacer efectiva la programacion en DB | `apps/sync/management/commands/sync_celery_beat.py` |
| Agregar una tarea nueva de sync | `apps/sync/tasks.py` + `ecomparts/beat_schedule.py` |
| Cambiar logica de productos o imagenes | `apps/sync/services/products.py` |
| Cambiar logica de compatibilidades | `apps/sync/services/compatibility.py` |
| Cambiar trazabilidad del estado | `apps/sync/models.py` y `apps/sync/services/observability.py` |
| Cambiar transporte hacia Odoo | `apps/sync/connector/` |

## 10. Resumen operativo

La foto actual del sistema es esta:

- `apps/sync` contiene la logica de integracion y observabilidad
- `ecomparts/settings.py` define parametros base y defaults
- `ecomparts/beat_schedule.py` arma el horario real de sync
- `ecomparts/celery.py` carga ese horario en Celery
- `sync_celery_beat` baja ese horario a `django_celery_beat`
- `celery_beat` agenda desde base de datos y `celery_worker` ejecuta las tareas

Si algo no corre automatico, normalmente hay que revisar esta cadena en ese orden:

1. `settings.py`
2. `beat_schedule.py`
3. `sync_celery_beat`
4. `PeriodicTask` en DB
5. logs de `celery_beat`
6. logs de `celery_worker`
