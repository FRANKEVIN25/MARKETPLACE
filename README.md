# ECOMPARTS PERÚ 

Marketplace Multi-Tenant de Autopartes

## Stack Tecnológico

- **Backend**: Django 4.2 + Django REST Framework
- **ERP**: Odoo 19 Community (Multi-Compañía)
- **Frontend**: SvelteKit (Fase 2)
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Tasks**: Celery + Celery Beat
- **Containerización**: Docker + Docker Compose

## Arquitectura

Multi-tenant con aislamiento de datos por proveedor. Cada proveedor gestiona su catálogo independiente, sincronizado con Odoo.

## Documentación

- [Setup Completo](docs/SETUP_COMPLETO.md)
- [Fase 1: Backend](docs/FASE_1_BACKEND.md)
- [Fase 2: Frontend](docs/FASE_2_FRONTEND.md)

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
