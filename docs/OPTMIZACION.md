# Roadmap de Optimizacion

Fecha: 7 de abril de 2026
Proyecto: ECOMPARTS Marketplace
Estado: Documento base para ejecucion por fases

## 1. Objetivo

Este documento define el roadmap de optimizacion tecnica del marketplace con foco en:

- robustez de modelos y relaciones,
- flexibilidad para evolucionar reglas de negocio sin romper APIs,
- escalabilidad operativa para multiproveedor,
- rapidez de carga en backend y frontend,
- consistencia entre catalogo, compatibilidades, stock, orders y Odoo,
- preparacion para SEO tecnico y crecimiento organico.

La idea no es hacer microajustes aislados. La idea correcta es trabajar app por app, medir, corregir cuellos de botella estructurales y dejar una base durable.

## 2. Criterio Rector

La optimizacion no debe perseguir complejidad. Debe perseguir estas propiedades:

1. Modelos claros, con responsabilidades bien definidas.
2. Queries predecibles, indexadas y faciles de perfilar.
3. Serializers y views con bajo riesgo de N+1 queries.
4. Integraciones desacopladas para que Odoo no contamine el dominio principal.
5. Capacidad de crecer sin rehacer el esquema cada pocas semanas.
6. Buen tiempo de respuesta para catalogo, detalle de producto, filtros y checkout.

## 3. Alcance de la Optimzacion

Por ahora el trabajo debe priorizar backend y contratos de datos. El frontend y SEO deben aprovechar esa base, no compensar debilidades del modelo.

Orden recomendado:

1. Modelos y constraints.
2. Índices y estrategia de consultas.
3. Managers, services y serializers.
4. Cache, tareas asincronas y sincronizacion.
5. Observabilidad.
6. SEO tecnico y performance de storefront.

## 4. Herramientas Disponibles Hoy

Segun el stack actual, ya tenemos una base razonable para optimizar:

### Backend y datos

- Django 4.2.16
- Django REST Framework
- PostgreSQL con `psycopg2-binary`
- `django-filter`
- `django-mptt`

### Cache y background jobs

- Redis
- `django-redis`
- Celery
- `django-celery-beat`
- Flower

### Infraestructura de serving

- Gunicorn
- WhiteNoise
- Docker / Docker Compose

### Utilidades funcionales

- Cloudinary y `django-cloudinary-storage`
- Pillow
- JWT con `djangorestframework-simplejwt`

### Documentacion API

- `drf-spectacular`

## 5. Herramientas que Faltan o Conviene Evaluar

Estas no son obligatorias hoy, pero sí muy recomendables para una etapa de optimizacion seria:

### Observabilidad y profiling

- Sentry para errores y trazabilidad en backend/frontend.
- `django-silk` o equivalente para profiling de requests y queries en entorno de desarrollo.
- `django-querycount` para detectar N+1 rapido.
- Prometheus + Grafana para métricas de app, worker y base de datos.
- `pg_stat_statements` en PostgreSQL para detectar queries lentas reales.

### Performance y cache avanzada

- Cache versionada por claves para catalogo, categorias, marcas, modelos y detalle de proveedor.
- CDN mas estricta para assets publicos e imagenes si Cloudinary no cubre todos los caminos.

### Busqueda y relevancia

- PostgreSQL full text search como primera fase realista.
- Meilisearch o Elasticsearch solo cuando el catalogo y la demanda lo justifiquen.

### SEO y contenido

- Sitemap dinamico.
- Metadata canónica por categoria, producto, proveedor y landing de filtros.
- Structured data tipo Product, Organization, BreadcrumbList y Review.

## 6. Redis

Redis no es un accesorio. En este proyecto debe verse como parte del núcleo operativo para:

- cache de lecturas frecuentes,
- sesiones o estado temporal si se decide ampliar ese uso,
- rate limiting futuro,
- colas Celery,
- desacoplar procesos pesados de sincronizacion,
- evitar recalculos repetitivos en páginas de alto tráfico.

Pero Redis no sustituye un modelo bien diseñado ni una query bien indexada. Primero se arregla la estructura; después se acelera con cache.

## 7. SEO: ahora o despues

SEO debe entrar en dos tiempos.

### Lo que sí conviene hacer desde ahora

- definir slugs estables y canónicos,
- evitar URLs ambiguas o duplicadas,
- asegurar que productos, categorias y proveedores tengan campos publicables consistentes,
- preparar metadatos y breadcrumbs,
- evitar dependencias del lado cliente para contenido crítico indexable,
- modelar reviews, rating y stock de forma estructurada.

### Lo que puede venir después de estabilizar backend

- estrategia editorial por categoria y proveedor,
- páginas SEO por combinaciones válidas de vehículo/categoría,
- schema markup completo,
- optimización de Core Web Vitals,
- sitemap segmentado,
- automatización de metadata y linking interno.

Conclusión: SEO técnico base empieza ahora. SEO de crecimiento y escala viene inmediatamente después de estabilizar modelos, consultas y storefronts públicos.

## 8. Riesgos Reales del Negocio

En un marketplace de autopartes para Perú, los puntos críticos no son genéricos:

- compatibilidades por vehículo pueden disparar queries caras,
- catálogo multiproveedor exige aislar claramente stock, pricing y visibilidad,
- Odoo puede introducir latencia, acoplamiento y fallos de sincronización,
- búsquedas por marca, modelo, motor, año y categoría tienden a crecer rápido en complejidad,
- el checkout multiproveedor requiere consistencia fuerte,
- reviews, reputación y reglas tributarias visibles afectan conversión y confianza,
- IGV, comprobantes y datos comerciales deben ser correctos y rápidos de leer.

## 9. Roadmap por Fases

## Fase 0. Baseline y medicion

Objetivo: dejar de optimizar a ciegas.

Entregables:

- inventario de modelos por app,
- mapa de relaciones y ownership de datos,
- top 20 endpoints y páginas críticas,
- medición de queries por endpoint,
- medición de tiempos de respuesta backend,
- detección de N+1 en catálogo, producto, proveedor, customer y órdenes,
- identificación de tablas calientes en PostgreSQL.

Resultado esperado:

- saber qué optimizar primero con evidencia.

## Fase 1. Dominio y calidad de modelos

Objetivo: endurecer el dominio antes de cachear o escalar.

Checklist:

- revisar `null`, `blank`, `unique`, `db_index`, `constraints` y `on_delete`,
- mover lógica repetida a managers o servicios de dominio,
- separar campos de integración externa de campos de dominio interno,
- garantizar nombres claros y consistentes entre modelos y API,
- revisar campos calculados que hoy podrían convertirse en cuellos de botella,
- definir dónde usar snapshots y dónde usar referencias vivas.

Resultado esperado:

- modelos más robustos, menos ambigüedad, menos deuda para fases posteriores.

## Fase 2. Queries, índices y serializers

Objetivo: bajar carga de base de datos sin romper claridad.

Checklist:

- agregar índices compuestos según filtros reales,
- revisar `select_related`, `prefetch_related`, `only`, `defer`,
- optimizar serializers de listados versus detalle,
- reducir joins innecesarios en endpoints públicos,
- revisar paginación y ordenamiento por defecto,
- cachear catálogos de referencia relativamente estables.

Resultado esperado:

- respuestas más rápidas y predecibles en lecturas frecuentes.

## Fase 3. Integracion Odoo y procesos asincronos

Objetivo: aislar mejor sincronización, evitar bloqueos y errores en cascada.

Checklist:

- separar comandos de bootstrap, sync y repair,
- versionar reglas de sync cuando sea necesario,
- aplicar idempotencia en tareas críticas,
- registrar estados y errores de sync por entidad,
- evitar que una falla de Odoo degrade el marketplace completo,
- mover recálculos pesados a Celery cuando no necesiten ser inline.

Resultado esperado:

- integración más segura y menos impacto operativo sobre tráfico real.

## Fase 4. Cache y storefront performance

Objetivo: aprovechar Redis de forma controlada.

Checklist:

- cache de categorías, marcas, modelos y variantes públicas,
- cache de detalle de proveedor público,
- cache selectivo del catálogo cuando no comprometa frescura comercial,
- invalidación explícita por cambios relevantes,
- uso prudente de cache por vehículo seleccionado y navegación de catálogo.

Resultado esperado:

- latencia menor en navegación pública.

## Fase 5. SEO técnico y crecimiento orgánico

Objetivo: convertir la estructura técnica en visibilidad y páginas indexables de calidad.

Checklist:

- títulos y metadescriptions por entidad,
- canonical URLs,
- structured data,
- sitemap y robots coherentes,
- páginas públicas de proveedor y producto limpias,
- estrategia de landings por taxonomía útil, no combinatoria infinita.

Resultado esperado:

- base lista para escalar posicionamiento sin inflar deuda técnica.

## 10. Orden de Trabajo por App

Este es el orden recomendado para la optimización meticulosa.

### 1. `products`

Es el centro del tráfico y de la indexación futura.

Prioridades:

- revisar índices sobre categoría, provider, active, universal y compatibilidades,
- separar claramente serializer de listado y serializer de detalle,
- endurecer consistencia de stock agregado y stock por almacén,
- revisar si `total_stock` conviene seguir calculándolo on demand o materializarlo parcialmente,
- revisar compatibilidades y joins con vehículos,
- preparar campos públicos para SEO y storefront.

Riesgos:

- N+1 en cards y detalle,
- queries explosivas por compatibilidad,
- costos de agregación en stock.

### 2. `vehicles`

Es la base de búsqueda especializada de autopartes.

Prioridades:

- validar constraints de marca, modelo y variante,
- revisar índices compuestos para filtros reales,
- simplificar payloads públicos para catálogo,
- definir estrategia de cache para listas públicas,
- revisar slugs y nombres mostrables.

Riesgos:

- crecimiento combinatorio de variantes,
- filtros lentos por modelo/año/motor,
- duplicidad semántica entre variantes similares.

### 3. `marketplace`

Gobierna providers, reputación, membresías y storefront público.

Prioridades:

- consolidar modelo público de proveedor,
- revisar rating y reviews para evitar recalculo innecesario,
- validar publicación y visibilidad,
- revisar endpoints públicos y permisos,
- preparar caché del storefront del proveedor.

Riesgos:

- sobrecarga por recalcular reputación inline,
- datos comerciales inconsistentes,
- APIs públicas demasiado pesadas.

### 4. `orders`

Debe ser correcto antes de ser rápido.

Prioridades:

- revisar estados, snapshots y consistencia transaccional,
- verificar índices sobre customer, provider, status y fechas,
- aislar lógica de cálculo y transición de estados,
- revisar subórdenes y pagos para evitar inconsistencias.

Riesgos:

- condiciones de carrera,
- sobreventa si stock y orden no están bien coordinados,
- carga excesiva en historial de órdenes.

### 5. `customer`

Debe quedar simple, extensible y con cargas rápidas.

Prioridades:

- separar preferencias, perfil y actividad si empieza a crecer demasiado,
- revisar uso de `select_related` y profile hydration,
- definir qué datos del customer deben ser snapshot en otras apps.

Riesgos:

- convertir el perfil en un contenedor de datos heterogéneos,
- cargar demasiado el endpoint `me`.

### 6. `cart`

Aunque aún no esté completamente maduro, debe diseñarse con criterio.

Prioridades:

- separar estado temporal de persistencia real,
- definir expiración, stock check y merge entre sesión y login,
- evitar que el carrito dependa de queries pesadas.

### 7. `sync`

Es el app con mayor riesgo de complejidad accidental.

Prioridades:

- dividir responsabilidades de sync,
- reforzar idempotencia,
- mejorar trazabilidad y retries,
- aislar reglas específicas de Odoo.

Riesgos:

- acoplamiento fuerte,
- tareas no reentrantes,
- errores difíciles de reproducir.

### 8. `discounts`

Prioridades:

- formalizar reglas de prioridad y stacking,
- aislar evaluación en servicios,
- evitar cálculos repetidos por request.

### 9. `services`

Prioridades:

- revisar modelo de catálogo de servicios y ubicación,
- preparar filtros y SEO local futuro,
- validar coherencia con customer workshop y reputación.

### 10. `core`

Prioridades:

- centralizar utilidades comunes reales,
- no convertir `core` en repositorio ambiguo.

## 11. Cuellos de Botella Probables

Los cuellos de botella más probables, antes de medir, son estos:

- catálogo de productos con joins a provider, stock y compatibilidades,
- filtros por vehículo en páginas públicas,
- detalle de producto con stock por almacén,
- storefront público de proveedor con reviews, rating y productos,
- checkout multiproveedor,
- endpoints `me` y perfiles enriquecidos,
- sincronización con Odoo ejecutada de forma demasiado inline,
- invalidación de cache no diseñada.

## 12. Principios de Refactorizacion

Cuando empecemos a optimizar app por app, cada cambio debe cumplir esto:

1. No mezclar refactorización, features nuevas y cambios cosméticos en el mismo lote.
2. Medir antes y después.
3. Mantener compatibilidad de API cuando no haya motivo fuerte para romperla.
4. Favorecer services/managers sobre lógica dispersa en views y serializers.
5. Evitar señales complejas cuando una tarea explícita o servicio sea más claro.
6. Documentar decisiones de modelado y tradeoffs.

## 13. KPI Tecnicos que Conviene Medir

### Backend

- tiempo promedio y p95 por endpoint,
- cantidad de queries por endpoint,
- tiempos de queries lentas,
- jobs Celery fallidos y reintentados,
- tiempo de sincronización con Odoo.

### Catálogo y negocio

- tiempo de carga de `/productos`,
- tiempo de carga de detalle de producto,
- tiempo de carga de perfil público de proveedor,
- éxito en búsqueda por vehículo,
- conversión desde páginas públicas a carrito o checkout.

### SEO técnico

- indexabilidad de producto, categoría y proveedor,
- cobertura de metadatos,
- tiempo de render de páginas públicas,
- contenido duplicado por rutas o filtros.

## 14. Resultado Esperado al Terminar este Roadmap

Si se ejecuta bien, el proyecto debe quedar con estas características:

- dominio de negocio más limpio,
- queries más rápidas y menos costosas,
- endpoints públicos preparados para tráfico y SEO,
- menor acoplamiento con Odoo,
- mejor base para escalar catálogo, providers y servicios,
- roadmap técnico claro para siguientes releases.

## 15. Recomendacion Operativa

La ejecución correcta no es intentar optimizar todo a la vez.

La ejecución correcta es:

1. tomar una app,
2. mapear sus modelos y consultas críticas,
3. detectar debilidades estructurales,
4. documentar el diseño objetivo,
5. implementar en lotes pequeños,
6. validar impacto real,
7. continuar con la siguiente app.

## 16. Siguiente Paso Inmediato

Fase siguiente recomendada:

- empezar por `products` y `vehicles` juntos,
- porque ahí viven el catálogo, el filtro principal de negocio y buena parte del rendimiento público,
- y porque además son la base para SEO, conversión y precisión comercial.

Cuando empecemos la implementación, conviene abrir un documento de trabajo por app con este formato:

- mapa de modelos,
- relaciones críticas,
- queries frecuentes,
- índices actuales,
- debilidades,
- cambios propuestos,
- impacto esperado,
- riesgos de migración.

Ese será el método correcto para optimizar con criterio de producto, no solo con criterio académico.