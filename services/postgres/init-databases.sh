#!/bin/bash
set -e

# ============================================
# Script de Inicialización de Bases de Datos
# Crea las BDs necesarias para el marketplace
# ============================================

create_db_if_missing() {
    local dbname="$1"
    local exists
    exists=$(psql -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$dbname'" )
    if [ "$exists" = '1' ]; then
        echo "Database $dbname already exists, skipping create"
    else
        echo "Creating database $dbname"
        psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE \"$dbname\";"
        psql -U "$POSTGRES_USER" -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE \"$dbname\" TO \"$POSTGRES_USER\";"
    fi
}

# Crear las bases esperadas por la configuración/.env
create_db_if_missing "ecomparts_odoo"
create_db_if_missing "ecomparts_marketplace"

echo '✅ Bases de datos verificadas/creadas correctamente'