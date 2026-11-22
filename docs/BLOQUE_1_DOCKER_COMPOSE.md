# Bloque 1 Validar Odoo en Docker Compose

Responsable de infraestructura: Frank. Este laboratorio prepara un arranque limpio de Odoo 18 con los addons del repositorio y valida su funcionamiento multiempresa antes de pasar a Minikube.

## Arranque en Windows

Desde la raiz del repositorio, con Docker Desktop en modo de contenedores Linux:

```powershell
.\scripts\lab.ps1 -Action Up
.\scripts\lab.ps1 -Action Check -Seed
```

La primera orden crea `.env.lab` si no existe, genera credenciales locales aleatorias, construye la imagen y levanta PostgreSQL, Redis, el inicializador y Odoo. El archivo de credenciales queda excluido de Git.

La segunda orden prepara un conjunto minimo de tres companias, tres usuarios restringidos, productos, stock y pedidos de prueba. Comprueba por HTTP y JSON-RPC el login, los addons y la separacion de datos. Este conjunto verifica infraestructura y funciones basicas; Jesus prepara el dataset del benchmark.

Acceso de Odoo: <http://localhost:8070>. El login de administracion esta en `ODOO_ADMIN_LOGIN` y su contrasena en `ODOO_ADMIN_PASS`, dentro de `.env.lab`. La cuenta `ODOO_SERVICE_LOGIN` es la utilizada para la integracion. `ODOO_ADMIN_PASSWORD` es la clave maestra de bases, no la contrasena del login.

Los puertos de laboratorio son 8070 y 8072 para Odoo, 8001 para Django y 5556 para Flower. Solo se publican en la interfaz local. El frontend se inicia por separado.

## Comandos de seguimiento

```powershell
# Estado, incluyendo el inicializador que debe haber terminado con codigo 0.
.\scripts\lab.ps1 -Action Status

# Repetir las comprobaciones sin crear ni modificar los datos de prueba.
.\scripts\lab.ps1 -Action Check

# Detener el entorno conservando sus volumenes.
.\scripts\lab.ps1 -Action Stop
```

La opcion `-Marketplace` de `Up` incluye Django, Celery y Flower. Su integracion completa con Odoo se valida en el bloque 5; la validacion de este bloque utiliza directamente el Service HTTP de Odoo en Compose.

## Repetir con volumenes nuevos

Cada nombre de proyecto de Compose crea una red y volumenes propios. Para repetir desde cero conservando los datos de la primera corrida:

```powershell
.\scripts\lab.ps1 -Action Stop
.\scripts\lab.ps1 -Action Up -ProjectName ecomparts-lab-repeticion
.\scripts\lab.ps1 -Action Check -Seed -ProjectName ecomparts-lab-repeticion
```

Usa un sufijo nuevo en cada arranque que deba partir de volumenes vacios. Solo un laboratorio puede utilizar los mismos puertos a la vez. Las credenciales de `.env.lab` se conservan entre corridas.

Los resultados de las comprobaciones se guardan en `.lab/<proyecto>-checks.json`. Los registros de construccion y ejecucion pueden conservarse en `.lab/`; esa carpeta queda excluida de Git.

## Secuencia de inicializacion

1. PostgreSQL crea la base indicada por `ODOO_DB` y la indicada por `DJANGO_DB_NAME`.
2. Su healthcheck espera al servidor TCP definitivo, despues de ejecutar los scripts de inicializacion.
3. `odoo_init` instala los addons mediante `--init`, sin datos demo, y finaliza el servidor con `--stop-after-init`.
4. El mismo inicializador crea o actualiza las cuentas de administracion y servicio usando el script existente del repositorio.
5. Odoo arranca cuando el inicializador termina correctamente. Django conserva su dependencia del healthcheck de Odoo.

Los addons comprobados son `base`, `web`, `sale_management`, `stock`, `ecomp`, `orders_odoo`, `multi_company_products` y `odoo_django_webhook`. Sus dependencias se instalan mediante Odoo.

La inicializacion se puede repetir sobre los mismos volumenes. La orden `--init` no sustituye una migracion ni una actualizacion de addons; un cambio de version del codigo requiere un procedimiento de actualizacion aparte.

## Cambios de infraestructura

- Se unificaron los nombres de bases entre Compose y el script de PostgreSQL.
- Se incorporo el servicio `odoo_init`, que impide aceptar trafico antes de preparar la base, los addons y las cuentas.
- Se anadio el override `compose.lab.yml` para utilizar contenedores, volumenes y puertos de laboratorio.
- Se cambio la base de las imagenes Python de Bullseye a Bookworm tras comprobar errores 404 al descargar paquetes de Bullseye.
- Se especificaron finales de linea LF para los scripts de shell y se normalizan los entrypoints de Odoo durante la construccion.
- La descarga del codigo de Odoo usa HTTP/1.1, muestra progreso y detecta una transferencia detenida.
- Los permisos de escritura se preparan sobre los directorios de datos y configuracion. Los entrypoints conservan el codigo de la imagen sin cambios de permisos recursivos en cada arranque.
- Los contextos Docker excluyen caches de Python, credenciales y archivos generados durante la ejecucion.
- Django dispone de healthcheck y Celery espera a que la API este disponible.
- El configurador de Odoo resuelve reglas y grupos mediante XML IDs, de forma que funciona en bases nuevas. Un error al aplicar las reglas detiene la configuracion y el arranque de Django.

El override utiliza la etiqueta YAML `!override`; requiere Docker Compose 2.24.4 o posterior. La version instalada durante esta tarea es 2.40.3.

## Evidencia de ejecucion

Estado de la tarea de Frank: implementada y validada el 22 de noviembre de 2026. El trabajo se incorpora a la rama `Kubernetes` para la revision cruzada del equipo.

| Comprobacion | Resultado |
|---|---|
| Configuracion de Compose | Valida; nombres y credenciales alineados. |
| PostgreSQL y Redis | Arranque correcto con volumenes nuevos. |
| Inicializacion de Odoo | Servicio `odoo_init` terminado con codigo 0; 64 modulos instalados contando dependencias. |
| Addons requeridos | Los ocho addons comprobados figuran instalados. |
| Django | Comprobacion de configuracion sin problemas y migraciones aplicadas correctamente. |
| Companias A, B y C | Login, catalogo, stock, pedido y aislamiento correctos en las tres. |
| Restricciones de usuario | Cada cuenta tiene una sola compania y no es administradora del sistema; se rechaza la lectura de un producto ajeno y la seleccion de otra compania. |
| Regresion del configurador | Tres pruebas aprobadas: IDs de la base actual, identificador inexistente y error de escritura de una regla. |
| Repeticion limpia | `ecomparts-lab-repeticion` inicializado sobre otros volumenes vacios; comprobaciones aprobadas de nuevo. |

Los pedidos de esta comprobacion se crean directamente en Odoo. El recorrido completo marketplace, Django, Celery y Odoo corresponde a la validacion de integracion del bloque 5.

Los informes de cada ejecucion estan en `.lab/ecomparts-lab-checks.json` y `.lab/ecomparts-lab-repeticion-checks.json`. La evidencia resumida y sin credenciales se conserva en [evidence/bloque1.json](evidence/bloque1.json).

## Referencias

- [Compose principal](../docker-compose.yml).
- [Override del laboratorio](../compose.lab.yml).
- [Lanzador PowerShell](../scripts/lab.ps1).
- [Comprobacion JSON-RPC](../scripts/verify_odoo_lab.py).
- [Inicializador de Odoo](../services/odoo/bootstrap.sh).
- [CLI de Odoo 18](https://www.odoo.com/documentation/18.0/developer/reference/cli.html).
- [Combinacion de archivos Compose](https://docs.docker.com/reference/compose-file/merge/).
