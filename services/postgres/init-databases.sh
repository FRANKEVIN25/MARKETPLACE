#!/bin/bash
set -e

# ============================================
# Script de Inicialización de Bases de Datos
# Crea las BDs necesarias para el marketplace
# ============================================

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Crear BD para Odoo Shared (Multi-Company)
    CREATE DATABASE ecomparts_odoo_shared;
    GRANT ALL PRIVILEGES ON DATABASE ecomparts_odoo_shared TO ecomparts_user;

    -- Crear BD para Django Marketplace
    CREATE DATABASE ecomparts_marketplace;
    GRANT ALL PRIVILEGES ON DATABASE ecomparts_marketplace TO ecomparts_user;

    -- Log de éxito
    \echo '✅ Bases de datos creadas correctamente:'
    \echo '   - ecomparts_odoo_shared (Odoo Multi-Company)'
    \echo '   - ecomparts_marketplace (Django)'
EOSQL