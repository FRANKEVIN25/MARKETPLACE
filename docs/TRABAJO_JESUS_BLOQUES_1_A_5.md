# Trabajo de Jesus: datos, validacion y resultados

Estos pasos preparan las pruebas de los cinco bloques del plan. Los bloques 1 y 2
tienen validacion local, y el bloque 3 tiene una prueba de dos replicas en un
solo nodo. La comparacion formal y el HPA de los bloques 4 y 5 siguen pendientes.

## Antes de comenzar

- Ejecutar desde la raiz del repositorio, en PowerShell.
- Docker Desktop con contenedores Linux. El perfil Minikube pide 4 CPU y 4096 MB;
  Docker debe disponer de mas de 4096 MB para dejar margen al propio motor.
- `.env.k8s` existe solo localmente y esta excluido de Git. No copiarlo a reportes.
- `scripts/run_benchmark.ps1` usa la imagen oficial de Locust dentro de
  Minikube; no exige instalar Locust en Windows. El generador comparte el nodo
  de laboratorio con Odoo, por lo que se registra su consumo en cada corrida.
- La proporcion A:B:C es 1:2:3 y la mezcla de lecturas es catalogo:stock = 3:2.
  Son parametros de este experimento, no equivalen a 120 usuarios reales.
- Las imagenes de los bloques 1 a 3 resumen registros reales. En Windows se
  regeneran con `.\scripts\render_jesus_evidence.ps1`; los JSON y CSV son la
  evidencia numerica primaria.

## Bloque 1: conjunto de datos reproducible en Compose

```powershell
.\scripts\lab.ps1 -Action Up
.\scripts\lab.ps1 -Action Check -Seed
python scripts/benchmark_dataset.py seed --env-file .env.lab --base-url http://127.0.0.1:8070
python scripts/benchmark_dataset.py verify --env-file .env.lab --base-url http://127.0.0.1:8070
```

El conjunto agrega 12 productos con stock y un cliente por compania. Los nombres
`BENCH-A-001`, `BENCH-B-001` y `BENCH-C-001` permiten repetir el seed sin duplicar
registros. `verify` no modifica datos. Guardar la salida como evidencia junto con
el resultado de `Check -Seed`. El script de Frank ya comprueba login, permisos
y pedido minimo en las tres companias.

La prueba local del 22 de noviembre de 2026 paso. Ver
[evidencia del bloque 1](evidence/jesus-bloque1.json). La carga de humo no
representa el benchmark final.

## Bloque 2: un Pod y prueba basica

```powershell
.\scripts\kubernetes.ps1 -Action Up
.\scripts\kubernetes.ps1 -Action Check -Seed
python scripts/benchmark_dataset.py seed
python scripts/benchmark_dataset.py verify
.\scripts\run_benchmark.ps1 -Pods 1 -Users 5 -Repeat 1 -DurationSeconds 60 -SpawnRate 1
```

La prueba usa `http://odoo:8069` desde un Job en el namespace `ecomparts`.
El puerto local `18070` sirve para preparar y comprobar los datos. Un
`port-forward` al Service termina en un solo Pod, por lo que no sirve para
medir distribucion entre replicas. CSV y metricas quedan en `.lab/runs/<id>/`.

En este equipo se valido con `-MemoryMb 3072`: pasaron las comprobaciones
funcionales, la persistencia y las corridas de humo de lectura y escritura.
Ver [evidencia del bloque 2](evidence/jesus-bloque2.json). Para comparar
1, 2 y 3 Pods, fijar una capacidad de cluster suficiente e identica en
todas las corridas. Los CSV y estadisticas finales de las corridas cortas estan
en [evidence/runs](evidence/runs/).

## Bloque 3: dos replicas, sesion y adjunto

En Minikube de un solo nodo se pudieron ejecutar dos Pods con el PVC
`ReadWriteOnce`. Esto no demuestra que el volumen funcione en nodos distintos.
Frank debe revisar el almacenamiento compartido, la estrategia `Recreate`,
el control de cron y el escalado antes de llevar esta configuracion a un cluster
de varios nodos.

Obtener los dos nombres con `kubectl get pods -n ecomparts -l
app.kubernetes.io/name=odoo`. En dos terminales, abrir un tunel **a cada Pod**:

```powershell
.\.tools\kubectl.exe --kubeconfig .lab/kubeconfig --context ecomparts-k8s -n ecomparts port-forward pod/<POD_A> 18071:8069
.\.tools\kubectl.exe --kubeconfig .lab/kubeconfig --context ecomparts-k8s -n ecomparts port-forward pod/<POD_B> 18072:8069
```

En un tercer terminal, o directamente con el envoltorio que abre y cierra
los dos tuneles:

```powershell
python scripts/verify_odoo_replicas.py --pod-a <POD_A> --pod-b <POD_B>
.\scripts\check_replicas.ps1
```

El script autentica en A y reutiliza la cookie en B, comprueba el adjunto
compartido y repite el aislamiento de las tres companias. Registrar sus
identificadores de Pod y la salida. Para la perdida de un Pod, iniciar una
corrida ligera de 180 s y eliminar un Pod mientras sigue:

```powershell
.\scripts\run_benchmark.ps1 -Pods 2 -Users 20 -DurationSeconds 180
.\.tools\kubectl.exe --kubeconfig .lab/kubeconfig --context ecomparts-k8s -n ecomparts delete pod <POD_A>
```

Usar terminales distintos y anotar la hora del borrado. Comparar
`run_stats_history.csv` con `infrastructure.csv`; registrar errores y tiempo
hasta que vuelva a haber dos Pods listos. Esta corrida es de disponibilidad,
separada del benchmark de capacidad.

La prueba local del 22 de noviembre de 2026 paso las comprobaciones de sesion,
adjunto y aislamiento entre dos Pods. Con 20 usuarios durante 120 s, el borrado
de un Pod produjo 3 fallos en 6978 solicitudes (0,043 %); volvieron a estar
listos dos Pods en 13,25 s. Ver [evidencia del bloque 3](evidence/jesus-bloque3.json).
Los CSV originales de esa corrida estan en [evidence/runs/202611222150154038](evidence/runs/202611222150154038/).
La prueba no valida almacenamiento en varios nodos ni garantiza cero errores
durante el fallo.

## Bloque 4: comparacion controlada

Frank prepara 1, 2 y 3 Pods fijos, sin HPA, conservando imagen, workers,
requests/limits, PostgreSQL y cron. El ejecutor comprueba que el numero de
replicas listas coincide y rechaza cualquier HPA activo.

Para cada configuracion de Pods, ejecutar:

```powershell
foreach ($users in 20,50,100,200) {
    foreach ($repeat in 1..3) {
        .\scripts\run_benchmark.ps1 -Pods <1_O_2_O_3> -Users $users -Repeat $repeat -DurationSeconds 300 -SpawnRate 5
    }
}
python scripts/summarize_benchmark.py
```

Revisar `.lab/runs/summary.md` y los CSV originales. Cada corrida conserva
`final.json` y `timing.json`; el resumen usa esas estadisticas de cierre
para evitar que un CSV periodico omita las ultimas solicitudes. Usa la mediana
de las repeticiones para p95 aproximado, operaciones exitosas/s y porcentaje de errores.
El script marca como fallo un error JSON-RPC aunque HTTP sea 200.

Los pedidos son una prueba **separada**. Ejecutar `-Mode write` con la misma
configuracion deseada y limpiar solo los pedidos de esa corrida antes de la
siguiente comparacion:

```powershell
.\scripts\run_benchmark.ps1 -Mode write -Pods 1 -Users 20 -DurationSeconds 60
python scripts/benchmark_dataset.py reset-orders --run-id <ID_DE_LA_CORRIDA>
python scripts/benchmark_dataset.py verify
```

No usar los datos ni el resumen para afirmar mejora de rendimiento hasta
completar las comparaciones y revisar CPU, RAM y conexiones de PostgreSQL.

## Bloque 5: pico HPA e integracion

Con el HPA de 1 a 3 Pods preparado por Frank, ejecutar un pico reproducible:

```powershell
.\scripts\run_benchmark.ps1 -Hpa -Users 200 -DurationSeconds 300 -SpawnRate 20
python scripts/summarize_benchmark.py
```

`infrastructure.csv` registra cada cinco segundos replicas deseadas, listas y
consumo observado; `run_stats_history.csv` permite situar p95 y errores en
el tiempo. Registrar tambien el objetivo de CPU, requests y evento de escalado
del HPA. El generador de carga consume recursos del mismo nodo: incluirlo al
interpretar los resultados.

Para la integracion, levantar Django y Celery, crear un pedido real desde el
marketplace y subir un comprobante por la API o la interfaz. La subida del
comprobante es la accion que encola `create_odoo_sale_order` en Celery.
Confirmar que `ODOO_URL` de Django apunta al Odoo de Kubernetes antes de
la prueba. Con el numero de SubOrder:

```powershell
docker compose --env-file .env.lab -p ecomparts-lab -f docker-compose.yml -f compose.lab.yml exec backend python manage.py verify_marketplace_order <NUMERO_SUBORDER>
```

El comando espera el resultado asincrono y compara en Odoo la compania, el
identificador de la SubOrder y las lineas. No crea el pedido ni sustituye el
recorrido por la API.

## Estado

Los bloques 1 y 2 de Jesus fueron validados y tienen evidencia. El bloque 3
tiene evidencia funcional y de fallo de Pod en Minikube de un nodo; queda
pendiente la arquitectura duradera de varias replicas. Los scripts de los
bloques 4 y 5 estan preparados, pero faltan corridas comparables, HPA y la
prueba del pedido completo de Django a Odoo en Kubernetes. No marcar un bloque
como cerrado sin esas evidencias.

## Continuacion de Frank, 23 de noviembre de 2026

La revision y la configuracion reproducible de dos replicas en el nodo del
laboratorio se documentan en [Bloque 3](BLOQUE_3_REPLICAS.md). La estrategia,
la afinidad del almacenamiento y el verificador se actualizaron en la rama
`frank/kubernetes-continuacion`. El [registro de revision](REVISION_JESUS_Y_CONTINUACION.md)
separa lo validado de las condiciones que faltan antes del benchmark formal.
