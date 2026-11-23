# ECOMPARTS PERÚ 

Marketplace Multi-Tenant de Autopartes

## Stack Tecnológico

- **Backend**: Django 4.2 + Django REST Framework
- **ERP**: Odoo 18 Community (Multi-Compañía)
- **Frontend**: SvelteKit (Fase 2)
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Tasks**: Celery + Celery Beat
- **Containerización**: Docker + Docker Compose

## Arquitectura

Multi-tenant con aislamiento de datos por proveedor. Cada proveedor gestiona su catálogo independiente, sincronizado con Odoo.

## Documentación

- [Bloque 1: laboratorio de Odoo en Docker Compose](docs/BLOQUE_1_DOCKER_COMPOSE.md)
- [Bloque 2: una replica de Odoo en Minikube](docs/BLOQUE_2_MINIKUBE.md)
- [Bloque 3: dos replicas, almacenamiento y recuperacion](docs/BLOQUE_3_REPLICAS.md)
- [Revision de Jesus y continuacion de Frank](docs/REVISION_JESUS_Y_CONTINUACION.md)
- [Trabajo de Jesus: datos, Locust y resultados (bloques 1 a 5)](docs/TRABAJO_JESUS_BLOQUES_1_A_5.md)
- [Setup Completo](docs/SETUP_COMPLETO.md)
- [Fase 1: Backend](docs/FASE_1_BACKEND.md)
- [Fase 2: Frontend](docs/FASE_2_FRONTEND.md)
- [Estrategia SaaS 2026-2031](docs/ESTRATEGIA_SAAS_2026_2031.md)

## Quick Start
```bash
# Clonar el proyecto
cd ~/Escritorio/ECOMPARTS

# Levantar servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Acceder a servicios
# Odoo: http://localhost:8070
# Django API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs/
```

## Contacto

- **Proyecto**: ECOMPARTS PERÚ
- **País**: Perú
- **Año**: 2026
