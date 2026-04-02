# 🌍 Arquitectura de Localización y Geolocalización

**Marketplace de Talleres + Autopartes (MVP → Escalable LATAM)**

---

## 🧠 Objetivo

Diseñar un sistema de localización **simple para el MVP**, pero **escalable a nivel marketplace tipo VTEX/Shopify**, que permita:

* Buscar **talleres cercanos**
* Encontrar **productos con stock más cercano**
* Gestionar **direcciones y envíos**
* Escalar a múltiples países sin reestructurar la base

---

## ⚠️ Principio clave

> No existe una librería mágica que resuelva esto.
> Es un problema de **arquitectura + datos + geolocalización**.

---

# 🧩 1. Separación de responsabilidades (CRÍTICO)

El sistema se divide en 3 capas independientes:

---

## 1️⃣ Ubicación administrativa (UBIGEO simplificado)

Se usa para:

* Formularios
* Facturación
* Envíos
* Filtros básicos

### Modelos:

```python
class Department(models.Model):
    name = models.CharField(max_length=100)

class Province(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

class District(models.Model):
    name = models.CharField(max_length=100)
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
```

---

## 2️⃣ Geolocalización (lat/lon)

Se usa para:

* Búsqueda por cercanía
* Ranking por distancia
* Matching inteligente

### Implementación:

```python
from django.contrib.gis.db import models

class GeoLocationMixin(models.Model):
    location = models.PointField()

    class Meta:
        abstract = True
```

---

## 3️⃣ Zonas de cobertura (logística)

Se usa para:

* Envíos
* Cobertura operativa
* Reglas comerciales

```python
class DeliveryZone(models.Model):
    name = models.CharField(max_length=100)
    districts = models.ManyToManyField(District)
```

---

# 🧱 2. Aplicación en el sistema actual

---

## 🔧 A. Talleres (`Workshop`)

Agregar:

```python
location = models.PointField(null=True, blank=True)
district = models.ForeignKey(District, null=True, on_delete=models.SET_NULL)
```

---

## 🏪 B. Almacenes (`Warehouse`)

🔥 Este es el punto clave para productos

```python
from django.contrib.gis.db import models

class Warehouse(models.Model):
    provider = models.ForeignKey('marketplace.Provider', on_delete=models.CASCADE)

    name = models.CharField(max_length=100)

    # NUEVO
    location = models.PointField(null=True, blank=True)
    district = models.ForeignKey(District, null=True, on_delete=models.SET_NULL)

    address = models.CharField(max_length=255, blank=True)
```

---

## 🚀 Resultado

Ahora puedes hacer:

👉 “producto más cercano con stock disponible”

---

# 🔥 3. Querys clave (core del negocio)

---

## 🔎 A. Talleres más cercanos

```python
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point

user_location = Point(lon, lat)

Workshop.objects.annotate(
    distance=Distance('location', user_location)
).order_by('distance')
```

---

## 🛒 B. Productos con stock más cercano

```python
StockItem.objects.filter(
    quantity__gt=0
).select_related('warehouse').annotate(
    distance=Distance('warehouse__location', user_location)
).order_by('distance')
```

---

## 🧠 Esto permite:

* Mostrar **“Disponible cerca de ti”**
* Priorizar **entregas rápidas**
* Ranking tipo Amazon / MercadoLibre

---

# 🗺️ 4. Estrategia MVP (Perú)

---

## 🇵🇪 Lima (ALTA PRECISIÓN)

✔️ Cargar TODOS los distritos
(~43 distritos)

👉 Necesario porque:

* Alta densidad
* Logística compleja
* Diferencias reales de distancia

---

## 🌎 Regiones (SIMPLIFICADO)

✔️ Solo ciudades principales (≈5 por región)

Ejemplo:

* Arequipa (Arequipa, Camaná, Mollendo…)
* La Libertad (Trujillo, Chepén…)
* Piura (Piura, Sullana…)

---

## 🎯 Regla MVP

| Zona     | Nivel                |
| -------- | -------------------- |
| Lima     | Distritos completos  |
| Regiones | Ciudades principales |
| Rural    | Ignorar (por ahora)  |

---

# ⚙️ 5. Stack técnico recomendado

---

## Backend (Django)

* PostgreSQL
* PostGIS
* GeoDjango

---

## Frontend (Svelte)

* Geolocation API (browser)
* Mapbox o Google Places (opcional)

---

# 🔥 6. Casos de uso habilitados

---

## 🔧 Talleres

* “Talleres cerca de mí”
* Matching por:

  * problema
  * categoría
  * distancia

---

## 🛒 Productos

* “Repuesto disponible más cercano”
* “Entrega más rápida”
* “Stock distribuido por almacén”

---

## 🚚 Logística

* Zonas de envío
* Restricciones por distrito
* Costos dinámicos (futuro)

---

# 🧠 7. Decisiones importantes

---

## ❌ NO hacer

* Usar solo strings ("Lima", "Miraflores")
* Mezclar ubicación con geolocalización
* Depender 100% de APIs externas

---

## ✅ SÍ hacer

* Base propia (UBIGEO simplificado)
* Lat/Lon en entidades clave
* PostGIS desde el inicio

---

# 🚀 8. Escalabilidad futura

Este diseño permite:

* Multi-país (solo cambias seed)
* Rutas inteligentes (OSRM / Google)
* Pricing dinámico por distancia
* Matching IA (taller + producto + ubicación)

---

# 🏁 TL;DR

* Separar: **ubicación, geolocalización, logística**
* Usar **PostGIS + GeoDjango**
* Aplicar a:

  * talleres ✅
  * almacenes ✅
* MVP:

  * Lima detallado
  * Regiones simplificadas

---

## 🔥 Insight final

> La ubicación no es un campo…
> es un **motor de decisión del negocio**.

---
