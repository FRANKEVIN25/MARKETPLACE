# Evidencia seleccionada de la validación breve

Los tres escenarios `smoke` y el pico `hpa` son ejecuciones de desarrollo sobre el commit base `a5873ab`. Sus cambios locales y hashes permanecen en `metadata.json`. Ninguna fila completa la matriz formal.

`final.json` y `timing.json` son la fuente para calcular los totales finales. `run_stats.csv` es la última escritura periódica de Locust y puede quedar unas solicitudes detrás del JSON al cerrar. `measured_summary.csv` y `summary.json` consolidan el JSON final y su duración efectiva.

Cada carpeta conserva configuración efectiva, reparto y concurrencia de usuarios, estadísticas finales, fallos y serie de infraestructura. El HPA tiene además nombres y tiempos de tráfico observado de los Pods nuevos en sus metadatos. `hpa-after-load.json` registra la reducción posterior a un Pod. `excluded-attempts.json` conserva tres intentos que no completaron la preparación.

`integration.json` registra pedidos LAB creados por HTTP, verificación de compañías y líneas en Odoo y logs correlacionados del worker Celery real. La primera ejecución encontró un error de ID de cliente; después de corregirlo se repitió con un cliente nuevo. Los secretos y tokens no forman parte de esta carpeta.

Las pruebas de recuperación del bloque 3 y las corridas originales de Jesús se mantienen en sus ubicaciones históricas y no se agrupan con estas ventanas.
