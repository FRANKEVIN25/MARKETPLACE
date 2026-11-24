# Entrega a Jesús: pruebas y cierre del experimento

## Punto de partida

Usar la rama `frank/kubernetes-continuacion`, basada en tu commit `f480b1d`. Incluye tus scripts, el almacenamiento y los verificadores del bloque 3, protocolo de medición corregido, HPA e integración HTTP comprobados. Ver [revisión original](REVISION_JESUS_Y_CONTINUACION.md) y [validación breve](BLOQUES_4_Y_5_VALIDACION_BREVE.md).

Frank terminó la implementación de infraestructura de este alcance y una validación breve. Quedan la matriz formal, el análisis de errores del pico, la revisión cruzada y la conclusión comparativa. Las pruebas cortas no completan esas tareas.

## Preparación en tu equipo

Actualizar tu copia sin descartar cambios locales. Puedes revisar esta rama desde otra copia de trabajo. No fusionar automáticamente el PR #3 ni sobrescribir `Kubernetes`.

```powershell
git fetch origin
git switch --track origin/frank/kubernetes-continuacion
```

Si la rama ya existe localmente, usar `git switch frank/kubernetes-continuacion` y revisar `git status` antes de actualizar. Los secretos `.env.lab` y `.env.k8s` y las herramientas `.tools` no viajan por Git. Seguir los bloques [1](BLOQUE_1_DOCKER_COMPOSE.md) y [2](BLOQUE_2_MINIKUBE.md) para preparar credenciales, Docker, kubectl y Minikube. Necesitas Python y Docker Compose con soporte `!override`. El script usa el contexto `ecomparts-k8s`, namespace `ecomparts` y kubeconfig local `.lab/kubeconfig`.

```powershell
.\scripts\kubernetes.ps1 -Action Up
.\scripts\kubernetes.ps1 -Action Check -Seed
python scripts/benchmark_dataset.py seed
python scripts/benchmark_dataset.py verify
.\scripts\kubernetes.ps1 -Action Scale -Replicas 2
.\scripts\check_replicas.ps1
python -m unittest discover -s scripts -p test_benchmark_tools.py -v
```

`Check -Seed` corresponde al escenario inicial de un Pod. Si retomas un laboratorio de dos o tres Pods, preparar antes `Scale -Replicas 1`. No cambiar ni sembrar datos durante una carga activa. Los verificadores crean solo sus marcadores LAB/BENCH.

## Matriz de lectura

Mantener constantes el presupuesto del nodo, imagen, datos, workers, recursos por Pod, configuración PostgreSQL, generador y política de conexiones. Registrar los límites Docker además de la capacidad que declara Kubernetes. En el equipo de Frank el nodo estaba limitado a 4 CPU y 4 GiB, aunque kubelet declaraba 16 CPU. Locust comparte recursos con el servidor.

Cerrar programas y cargas ajenas, y detener la integración aislada si fue levantada. `--stop` conserva los volúmenes y solo apunta al proyecto de integración. Si no existe su archivo local de entorno, omitir ese comando.

```powershell
python scripts/integration_lab.py --stop
.\scripts\kubernetes.ps1 -Action HpaOff -Replicas 1
git status --short
# Vista previa: no cambia réplicas ni inicia carga.
python scripts/run_benchmark_matrix.py --mode read
# Ejecutar cuando puedas dedicar el equipo al experimento.
python scripts/run_benchmark_matrix.py --mode read --execute
```

Son **36 corridas por modo**: 1/2/3 Pods por 20/50/100/200 usuarios, con tres repeticiones. Cada una usa rampa de 5 usuarios/s, 30 s de calentamiento y 300 s medidos, además de preparación de sesiones. Solo la medición suma tres horas por modo. La ejecución total tarda más. El orden alterna las configuraciones de Pods dentro de cada carga y repetición.

El árbol versionado debe estar limpio. No cambiar el código durante la matriz. El ejecutor registra el commit y la firma de configuración. Si falla la preparación o cambia la configuración, se detiene y no declara la matriz completa. Conservar la evidencia fallida para diagnosticarla. La corrección actual del arranque tiene evidencia hasta 100 usuarios; 200 sigue pendiente de esta ejecución.

El archivo `.lab/matrices/matrix-<fecha>.json` es el punto de continuación. Para retomar el mismo experimento y commit:

```powershell
python scripts/run_benchmark_matrix.py --mode read --execute --resume .lab/matrices/matrix-<fecha>.json
```

Una corrida válida queda registrada antes de limpiar sus pedidos. Si la limpieza falla, al retomar se repite la limpieza y se conserva la medición, sin duplicarla. No editar el checkpoint para ocultar errores. Si cambias parámetros o código, iniciar otra familia de experimento y no mezclarla con la anterior.

## Pedidos por separado

```powershell
python scripts/run_benchmark_matrix.py --mode write
python scripts/run_benchmark_matrix.py --mode write --execute
```

La matriz de escritura agrega otras 36 corridas y al menos tres horas medidas. Crea ventas borrador BENCH, no confirma stock ni pagos. La limpieza posterior se restringe al `run_id` de la corrida. Verificar el dataset al terminar cada limpieza. Ejecutar esta matriz después de lectura y analizarla por separado.

## Pico HPA e integración

Repetir el pico con una identificación propia. No mezclarlo con réplicas fijas:

```powershell
.\scripts\kubernetes.ps1 -Action HpaOn
.\scripts\run_benchmark.ps1 -Hpa -Purpose hpa -Users 100 -SpawnRate 5 -WarmupSeconds 30 -DurationSeconds 300 -ExperimentId jesus-hpa-01
.\scripts\kubernetes.ps1 -Action Status
# Esperar y registrar también la reducción al terminar la carga.
.\scripts\kubernetes.ps1 -Action HpaOff -Replicas 2
python scripts/integration_lab.py --setup --verify
```

En la primera prueba breve válida hubo 18 errores de transporte durante el pico. Revisar su instante contra CPU, memoria, conexiones PG, creación y readiness de Pods. El HPA es reactivo y no elimina por sí solo los fallos durante un incremento rápido. Si cambias recursos, target o rampa, registrar la nueva configuración y repetir los escenarios comparables.

La integración crea un cliente nuevo y pedidos de A/B/C por la API, sube comprobantes y espera al worker real. La evidencia está en `.lab/integration-result.json`. Revisar además la tienda en navegador con las mismas compañías, el estado de pago y los casos de error que exija el plan. Esta entrega verifica la API y la venta borrador.

## Qué entregar para cerrar

- Checkpoint con las 36 celdas completas de cada modo ejecutado y el mismo commit/configuración por familia.
- Por corrida: `metadata.json`, `timing.json`, `final.json`, CSV de solicitudes y fallos, serie de infraestructura y estados de Pods. No subir `.env`, tokens, kubeconfig ni secretos.
- Tabla con repeticiones, mediana p95, operaciones exitosas/s y errores, usando `final.json`. El CSV periódico puede contener menos solicitudes por su último instante de escritura.
- Serie CPU/RAM, conexiones PG y réplicas, con las marcas de escalado/recuperación. Distinguir muestreo de métricas y medición de latencia.
- Conclusión apoyada por esos datos. Comparar misma carga y familia. Si tres Pods no mejoran, explicarlo con los recursos y las métricas observadas.
- Revisión cruzada de los cambios y acuerdo de fusión. Actualizar informe y presentación, manteniendo visible el alcance de un nodo y PostgreSQL único.

```powershell
python scripts/summarize_benchmark.py --purpose benchmark
```

El resumen separa familias y rechaza repeticiones formales duplicadas. No infiere que exista una matriz completa a partir de unas filas. El checkpoint y la cobertura de las 36 celdas son necesarios para ese cierre.
