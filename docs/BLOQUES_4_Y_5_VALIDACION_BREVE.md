# Bloques 4 y 5: infraestructura y validación breve

Fecha: 23 de noviembre de 2026. Rama: `frank/kubernetes-continuacion`.

El alcance elegido fue comprobar las herramientas, el HPA y la integración, dejando la matriz completa para Jesús. La infraestructura tiene evidencia funcional. La comparación de capacidad y el cierre del experimento siguen pendientes.

## Qué cambió sobre el trabajo de Jesús

Se conservaron sus datos BENCH, operaciones de lectura y pedidos separados, verificadores y resultados históricos. El ejecutor ahora exige completar la preparación de sesiones antes de iniciar la rampa de trabajo. Después espera un calentamiento explícito y reinicia las estadísticas para medir una ventana completa. El tiempo de preparación no se presenta como rendimiento medido.

El protocolo 3 fija la semilla y asigna usuarios A:B:C mediante proporciones enteras reproducibles. Con 20 usuarios se obtienen A=3, B=7 y C=10. Con 100 se obtienen A=17, B=33 y C=50. Las consultas de catálogo y stock conservan pesos 3:2. Cada solicitud abre una conexión nueva conservando la cookie, para permitir que el Service envíe tráfico a Pods nuevos. Esta política añade trabajo de conexión y debe mantenerse igual en todas las comparaciones.

Los errores JSON-RPC cuentan como fallos incluso con HTTP 200. Los fallos de preparación invalidan una corrida si no se alcanzan todos los usuarios. La preparación permite hasta tres intentos por usuario y conserva sus errores de intento. Los fallos de las solicitudes medidas permanecen en los resultados, sin reintentos que los oculten.

`metadata.json` conserva imagen e identificador efectivo, recursos, workers, configuración de PostgreSQL, capacidad declarada por Kubernetes, límites del contenedor del nodo, hashes de scripts, commit y cambios locales. Las comparaciones se agrupan por una firma de configuración. El generador también tiene imagen y recursos fijados. Las ejecuciones formales requieren un árbol de archivos versionados limpio, 30 s de calentamiento y al menos 300 s medidos.

La preparación, la rampa, el calentamiento y la medición están registrados en `timing.json`. `final.json` es la fuente de totales finales. Los CSV de Locust se escriben periódicamente y pueden quedar unas solicitudes detrás del JSON al cerrar. `measured_summary.csv` se calcula desde el JSON final y la duración efectiva.

## Entorno real

Un nodo Minikube con driver Docker, limitado por Docker a 4 CPU y 4 GiB. Kubernetes informa 16 CPU y unos 7,44 GiB de capacidad de su VM subyacente. Ese valor declarado no sustituye el límite efectivo del contenedor. El ejecutor registra ambos valores para las próximas corridas. Locust comparte el presupuesto del nodo con Odoo y PostgreSQL.

Por Pod Odoo: dos workers, cron desactivado, `db_maxconn=8`, solicitud 500m CPU y 768 MiB, límite 1500m CPU y 1536 MiB. PostgreSQL usa `max_connections=100`. Imagen Odoo: `ecomparts-odoo:block2-43f43e9752ef`. Los manifiestos y la configuración efectiva están en las evidencias.

Los Pods comparten sesiones y filestore en un PVC RWO en el mismo nodo. PostgreSQL tiene otro PVC. El despliegue se fija al nodo que conserva el almacenamiento. Esto permite probar réplicas en este laboratorio y conserva un punto único de fallo en el equipo, el almacenamiento y PostgreSQL.

## Resultados breves con réplicas fijas

20 usuarios, rampa de trabajo de 5 usuarios/s, calentamiento de 5 s y ventana medida de 30 s. Una ejecución por configuración. HPA desactivado.

| Pods | Solicitudes finales | Fallos | p95 | Operaciones exitosas/s | ID |
|---:|---:|---:|---:|---:|---|
| 1 | 1938 | 0 | 23 ms | 64,598 | 202611231848375800 |
| 2 | 1926 | 0 | 34 ms | 64,198 | 202611231849378000 |
| 3 | 1947 | 0 | 18 ms | 64,900 | 202611231850377000 |

Las tres configuraciones aceptan la carga breve. No se concluye una mejora de capacidad ni un número máximo de usuarios con estas ventanas. Son ejecuciones de desarrollo sobre `a5873ab`, con cambios locales y hashes registrados. `comparison_eligible=false` en las cuatro pruebas de esta entrega.

## HPA comprobado

Manifiesto: `k8s/autoscaling/odoo-hpa.yaml`. Rango 1 a 3 Pods. Objetivo: 70 % de la CPU solicitada de 500m, equivalente a 350m por Pod. El porcentaje corresponde al request, no a toda la CPU del equipo. Subida máxima de un Pod por 30 s, bajada de un Pod por 30 s con estabilización de 60 s, elegida para la demostración de laboratorio.

```powershell
.\scripts\kubernetes.ps1 -Action HpaOn
.\scripts\run_benchmark.ps1 -Hpa -Purpose hpa -Users 100 -SpawnRate 5 -WarmupSeconds 5 -DurationSeconds 120 -ExperimentId mi-pico-hpa
.\scripts\kubernetes.ps1 -Action HpaOff -Replicas 2
```

En la corrida `202611231840403600`, 100 usuarios permanecieron activos durante 120 s. Totales finales: 15048 solicitudes, 18 fallos, 0,120 % de error, p95 de 2100 ms y 125,250 operaciones exitosas/s. Hubo fallos de transporte durante la subida de carga, registrados como respuestas no JSON con estado HTTP 0. Requieren análisis antes de declarar un nivel de servicio.

La serie temporal observó un Pod al comienzo, dos listos a las 23:42:18 UTC y tres a las 23:42:49 UTC. Los logs de ambos Pods nuevos contienen POST a `call_kw` con HTTP 200. Eso demuestra recepción de tráfico a nivel HTTP. Los errores funcionales se contabilizan en Locust y HTTP 200 por sí solo no garantiza éxito JSON-RPC. Una captura posterior sin carga confirmó un Pod listo y deseado.

Tres intentos previos con 200 usuarios fallaron la preparación y se excluyeron de las métricas válidas. Motivaron separar la preparación de sesiones de la rampa de consultas. La validación corregida del HPA se ejecutó con 100 usuarios. El protocolo corregido aún debe probarse con 200 en la matriz de Jesús.

## Integración real por la API

Se añadió un proyecto Compose independiente, `ecomparts-lab-integration`, con base y volúmenes propios. Django y un worker Celery real acceden al Service NodePort `odoo-marketplace` a través de la red privada Docker del nodo. El Service ClusterIP original `odoo` se conserva para las pruebas internas.

```powershell
python scripts/integration_lab.py --setup --verify
```

El script genera credenciales locales en `.lab/marketplace-kubernetes.env`, prepara usuarios y productos LAB y obtiene un token por el endpoint de autenticación. Crea los pedidos y sube una imagen de comprobante por HTTP. El verificador lee la SubOrder y compara en Odoo su compañía, referencia, producto y cantidad. No crea el pedido por ORM ni ejecuta las tareas Celery en modo directo.

| Compañía de la tienda | SubOrder | sale.order Odoo | company_id | Resultado |
|---|---|---:|---:|---|
| A | ORD-2026-00004-A | 6 | 2 | Correcto |
| B | ORD-2026-00005-A | 7 | 3 | Correcto |
| C | ORD-2026-00006-A | 8 | 4 | Correcto |

Los seis POST de pedidos y comprobantes devolvieron HTTP 201. Se conservaron logs del contenedor del worker asociados a cada SubOrder. La letra final `-A` de estos números identifica la primera suborden del pedido, no la compañía A. La compañía se valida por `company_id`.

La prueba detectó un error existente con clientes nuevos: `create` devolvía `[id]` para `res.partner` y `utm.source`, pero el conector pasaba la lista a una relación que exige un número. Se normalizó y validó el identificador en esos dos casos y en `sale.order`. Tres pruebas de regresión cubren el cliente nuevo, la fuente nueva y las respuestas inválidas. Pasan seis pruebas de `apps.sync.tests` y siete de las herramientas de benchmark. Después del arreglo se repitió el recorrido con otro cliente nuevo y las tres compañías pasaron.

El alcance probado llega a una venta borrador después de subir el comprobante. La aceptación real del pago, la reserva/entrega de stock, los webhooks de retorno y el navegador SvelteKit requieren sus propias pruebas. El comprobante usado es una imagen sintética de laboratorio.

```powershell
# Detener solo esta integración, conservando sus datos:
python scripts/integration_lab.py --stop
```

## Evidencia y cierre pendiente

Después de guardar la implementación en el commit `f455b20`, se comprobó otra vez el ejecutor con dos Pods, 20 usuarios y 30 s medidos: 1930 solicitudes y cero fallos. El árbol versionado estaba limpio y las copias de fuentes coincidieron con sus hashes. Esta comprobación adicional se conserva en [committed-runner-check.json](evidence/frank-validacion-breve/committed-runner-check.json), separada del piloto y de la matriz formal. Las simulaciones de reanudación también comprobaron que una celda medida no se duplica y que los borradores de una ejecución fallida se limpian antes del reintento.

Ver [informe](INFORME_VALIDACION_BREVE.md), [entrega a Jesús](ENTREGA_JESUS_PRUEBAS_FINALES.md) y [datos seleccionados](evidence/frank-validacion-breve/summary.json). La prueba histórica de recuperación de un Pod se conserva separada en [bloque 3](BLOQUE_3_REPLICAS.md): 5522 solicitudes, tres fallos y 6,008 s hasta observar dos Pods listos. Tiene un protocolo y un objetivo diferentes.

Jesús debe ejecutar la matriz formal y revisar las conclusiones. Después corresponde actualizar el informe y la presentación con las comparaciones completas y acordar la integración de las ramas. Esta entrega no aprueba ni fusiona su PR automáticamente.

Referencias técnicas: [HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/), [volúmenes y modos de acceso](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes), [API externa de Odoo 18](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html), [estadísticas de Locust](https://docs.locust.io/en/stable/retrieving-stats.html).
