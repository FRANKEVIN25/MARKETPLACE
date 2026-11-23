# Bloque 3: dos réplicas de Odoo en un nodo

Este paso completa la configuración de Frank y reproduce las comprobaciones de Jesús. El laboratorio conserva sus bases y volúmenes; no se modifica el marketplace ni se configura todavía el HPA.

## Preparar y comprobar

Con Docker Desktop abierto y el perfil `ecomparts-k8s` iniciado:

```powershell
.\scripts\kubernetes.ps1 -Action Scale -Replicas 2
.\scripts\check_replicas.ps1
```

Si es la primera instalación, usar primero `kubernetes.ps1 -Action Up` y `-Action Check -Seed`, como explica el bloque 2. `Check` es la comprobación del bloque 2 y requiere una sola réplica; no debe ejecutarse durante una corrida de carga.

`Scale` conserva la imagen que ya está desplegada y aplica el Deployment versionado. Espera los Pods listos, comprueba que usan el mismo PVC en el único nodo y que el Service tiene dos destinos preparados. Abre de nuevo el acceso local en `http://127.0.0.1:18070`.

Los dos procesos de Odoo de cada contenedor son workers, no réplicas adicionales. Cada Pod sigue siendo una instancia de Odoo. Las compañías A/B/C comparten la base y se separan por permisos; no existe un Pod reservado para cada empresa.

La prueba entre réplicas abre un túnel **a cada Pod**, con puertos 18071 y 18072. Autentica en A y reutiliza la cookie en B, compara un adjunto del filestore y comprueba acceso al producto propio y rechazo de los dos productos ajenos para las tres compañías, en ambos Pods. Los nombres de los Pods quedan en la salida.

## Probar la pérdida de un Pod durante lectura

Primero preparar y verificar los datos. La carga escribe registros de prueba BENCH únicamente durante la preparación; la corrida siguiente es de lectura:

```powershell
python scripts/benchmark_dataset.py seed
python scripts/benchmark_dataset.py verify
```

Confirmar que ambos comandos terminan correctamente antes de continuar. En una terminal:

```powershell
.\scripts\run_benchmark.ps1 -Pods 2 -Users 20 -DurationSeconds 120 -SpawnRate 5
```

El ejecutor muestra `job.batch/bench-<ID> created`. En otra terminal, mientras la corrida sigue activa:

```powershell
.\scripts\observe_odoo_recovery.ps1 -RunId <ID> -Users 20
```

El observador exige el perfil y namespace del laboratorio, una corrida de lectura con dos réplicas, veinte usuarios efectivos y al menos cien solicitudes antes de borrar un solo Pod. Comprueba que vuelve a haber dos Pods listos con una identidad de reemplazo y que el Service conserva su UID. Guarda `.lab/runs/<ID>/recovery.json`.

El tiempo se mide desde la solicitud de borrado hasta observar dos Pods listos no terminantes, mediante consultas cada 500 ms más la latencia de la API. No significa que las solicitudes hayan permanecido sin fallos ni que todas hayan usado ambos Pods. Los fallos y tiempos se leen de los CSV y de `final.json` cuando termina Locust.

Un túnel local al Service queda conectado a un Pod concreto y puede terminar si se retira ese Pod. El generador de carga usa el Service interno desde Minikube, no el túnel. Al acabar puede reabrirse el acceso local:

```powershell
.\scripts\kubernetes.ps1 -Action Forward
.\scripts\check_replicas.ps1
```

## Qué revisar antes de dar conformidad

- Dos Pods listos con la misma imagen, recursos por Pod y claim `odoo-data`.
- Sesión A→B, adjunto idéntico y aislamiento A/B/C en los dos Pods.
- `max_cron_threads = 0`, dos workers por Pod y `db_maxconn = 8`.
- Mismo UID del Service antes y después del borrado.
- CSV completo con fallos, solicitudes, tiempo medido y recuperación registrada.
- Alcance de un nodo y PostgreSQL único explícitos en el resultado.

Las evidencias nuevas se enlazan en [frank-bloque3.json](evidence/frank-bloque3.json). Jesús debe reproducir o revisar esta configuración antes del cierre cruzado. La matriz de capacidad y HPA siguen pendientes; esta prueba no es el benchmark formal.

La corrida de disponibilidad `202611231758445348`, realizada el 23 de noviembre,
registró 5522 solicitudes y 3 fallos (0,054 %), con dos Pods listos observados de
nuevo a los 6,008 s. El Service conservó su UID. Después del reemplazo pasaron
de nuevo sesión, adjunto y permisos A/B/C en ambos Pods. El nodo de esta prueba
tiene 4 CPU y 4096 MB; no debe compararse su tiempo de recuperación con el de
Jesús como si la diferencia demostrara una mejora de capacidad.

La corrida se ejecutó antes del commit final de infraestructura, sobre el árbol
de trabajo registrado en su metadata. Conservamos sus CSV y JSON originales.
No es una corrida formal sobre un commit limpio ni reemplaza la matriz del
bloque 4.

## Volver a una réplica

Fuera de una corrida activa y sin HPA:

```powershell
.\scripts\kubernetes.ps1 -Action Scale -Replicas 1
```

La misma acción admite tres réplicas, pero no constituye por sí sola una validación del bloque 4. Los escenarios se medirán después de fijar metodología, recursos y captura de configuración por corrida.
