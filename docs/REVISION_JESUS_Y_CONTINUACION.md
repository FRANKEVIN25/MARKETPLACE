# Revisión de Jesús y continuación de Frank

Fecha: 23 de noviembre de 2026. Esta es la revisión y entrega del siguiente paso, no el informe final del experimento.

**Actualización posterior:** los hallazgos de esta revisión se atendieron en los [bloques 4 y 5](BLOQUES_4_Y_5_VALIDACION_BREVE.md). HPA e integración API tienen evidencia breve. La matriz formal y la revisión cruzada quedan en la [entrega a Jesús](ENTREGA_JESUS_PRUEBAS_FINALES.md). El texto siguiente conserva la revisión inicial como registro histórico.

## Trabajo revisado

- Plan: [Odoo multiempresa en Kubernetes](https://docs.google.com/document/d/1bhAJbVwwfICd8ajIzh4CxHmDQNWdyLeU_AU3XM7Y6FE/edit).
- [PR #3](https://github.com/FRANKEVIN25/MARKETPLACE/pull/3), abierto como borrador hacia `Kubernetes`. Al consultar GitHub no tenía revisiones ni verificaciones automáticas publicadas.
- Rama de Jesús: `jesus/bloques-1-5-evidencias`.
- Commit de Jesús: `f480b1da4c4d094cf7c92dea934bd8efdb57720a`, del 22 de noviembre, hora de Lima. Incluye 39 archivos y 2524 líneas añadidas.
- Continuación local: `frank/kubernetes-continuacion`, basada directamente en ese commit. El PR original no se fusionó ni se aprobó automáticamente.

Jesús separó datos BENCH, carga de lectura, creación de pedidos, validación entre réplicas y consolidación de resultados. Versionó CSV y JSON además de sus imágenes; las imágenes son resúmenes, no sustituyen los registros numéricos. Documentó qué probó y qué sigue pendiente. Sus corridas preceden al commit final y registran el árbol de trabajo y el hash del script: se debe conservar esa información al interpretarlas.

## Qué se pudo verificar

Las tres pruebas de `test_benchmark_tools.py` pasan. Comprobaron errores JSON-RPC con HTTP 200, respuestas vacías y el cálculo de operaciones exitosas sin contar fallos. En este entorno hubo que ejecutarlas fuera del sandbox porque este impedía escribir en los directorios temporales; no fue un fallo de sus aserciones.

El resumen reconstruido desde los `final.json` y `timing.json` versionados coincide con:

| Corrida de Jesús | Solicitudes | Fallos | p95 aproximado | Tipo |
|---|---:|---:|---:|---|
| 202611222145155138 | 409 | 0 | 14 ms | Lectura, un Pod, cinco usuarios |
| 202611222146357743 | 80 | 0 | 65 ms | Pedidos, un Pod, un usuario |
| 202611222150154038 | 6978 | 3 | 46 ms | Disponibilidad, dos Pods, veinte usuarios |

Son pruebas cortas con objetivos distintos. No permiten comparar rendimiento entre una y dos réplicas. La recuperación de 13,246 s documentada por Jesús corresponde a su corrida y equipo, no a una medición nueva de Frank.

## Ajustes realizados en este paso

1. El Deployment usa `RollingUpdate`, con `maxSurge: 0` y `maxUnavailable: 1`. Con dos réplicas, una actualización puede conservar una preparada; con una sola puede haber interrupción. No garantiza cero errores durante un fallo.
2. El nodo que conserva los archivos se etiqueta y Odoo se fija a él. El lanzador rechaza esta configuración si hay más de un nodo.
3. Se añadió `Scale -Replicas 1|2|3`. Conserva la imagen desplegada, comprueba el PVC, dos workers y cron desactivado, y rechaza cambios mientras hay HPA o una corrida BENCH activa.
4. La preparación registra Pods, UID, imagen, recursos, volumen, destinos listos del Service y hashes de configuración en `.lab/<perfil>-fixed-<n>.json`.
5. El verificador de Jesús ahora comprueba los permisos de A/B/C en **ambos** Pods y rechaza productos de las otras dos compañías en cada uno. Antes comprobaba la continuación de la sesión A→B y realizaba las consultas de aislamiento en B.
6. `observe_odoo_recovery.ps1` espera carga efectiva antes de eliminar un solo Pod y registra la recuperación y la identidad del Service.

### Alcance del almacenamiento y cron

El plan pide compartir almacenamiento en el nodo de laboratorio. `ReadWriteOnce` permite que varios Pods monten el mismo volumen en **un mismo nodo**, según la [documentación de Kubernetes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes). No hace falta introducir NFS para este alcance.

Ambos Pods montan `odoo-data` en `/var/lib/odoo`, que contiene sesiones y filestore. Los datos de PostgreSQL están en su propio PVC. Esto no valida almacenamiento compartido entre varios nodos ni resistencia a perder el equipo completo.

Se mantiene `max_cron_threads = 0` en los Pods web para que las réplicas no ejecuten esas tareas durante las pruebas. No se ha desplegado un ejecutor de cron de producción. La configuración por Pod sigue en dos workers, `db_maxconn = 8`, CPU solicitada de 500m y RAM solicitada de 768 MiB.

## Pendientes antes del benchmark formal

| Hallazgo | Por qué importa | Paso siguiente |
|---|---|---|
| Falta un calentamiento explícito después de completar la rampa | `--reset-stats` al terminar de crear usuarios no equivale a calentar durante un período fijado; `-t` incluye la rampa | Separar rampa, calentamiento y ventana medida; repetir con parámetros idénticos |
| El resumen agrupa solo por modo, Pods, usuarios y HPA | Puede mezclar duración, rampa, imagen o recursos distintos bajo una misma fila | Capturar configuración completa por corrida y exigir una firma de comparación equivalente |
| La preparación de usuarios ocurre fuera de las estadísticas de Locust | Un fallo de login o de datos puede reducir la carga efectiva | Exigir los usuarios previstos, solicitudes medidas y un estado de preparación válido |
| A:B:C se asigna con probabilidades 1:2:3 | No garantiza esa proporción exacta en cada corrida | Registrar la distribución efectiva o controlar la asignación reproducible |
| HPA todavía no está configurado | El ejecutor de Jesús acepta el modo HPA, pero eso no demuestra escalado | Frank prepara el HPA y Jesús ejecuta el pico con su serie temporal |

Estos puntos se resolverán al preparar el bloque 4. Las corridas cortas conservan su valor como comprobaciones funcionales y de disponibilidad.

## Secuencia para continuar

1. Revisar la evidencia nueva del bloque 3 y reproducir la sesión y los permisos con los manifiestos de esta rama.
2. Completar las condiciones de comparación del bloque 4 y preparar los escenarios fijos con la misma capacidad del nodo.
3. Jesús ejecuta la matriz 1/2/3 Pods × 20/50/100/200 usuarios, con repeticiones y pedidos por separado. Frank recoge y vincula las métricas de infraestructura.
4. Preparar el HPA y probar el recorrido completo del pedido marketplace → Django → Celery → Odoo, en la compañía correcta.
5. Con los datos finales, redactar el informe, los gráficos y la presentación. Todavía no corresponde afirmar una mejora de rendimiento ni cerrar los bloques 4 y 5.

Ver [procedimiento del bloque 3](BLOQUE_3_REPLICAS.md) y [trabajo original de Jesús](TRABAJO_JESUS_BLOQUES_1_A_5.md).
