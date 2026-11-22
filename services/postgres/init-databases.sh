#!/bin/bash
set -euo pipefail

# ============================================
# Script de Inicialización de Bases de Datos
# Crea las BDs necesarias para el marketplace
# ============================================

create_db_if_missing() {
    local dbname="$1"
    echo "Verificando base de datos: $dbname"
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d postgres \
        --set=db_name="$dbname" --set=db_owner="$POSTGRES_USER" <<'SQL'
SELECT format('CREATE DATABASE %I OWNER %I', :'db_name', :'db_owner')
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = :'db_name')
\gexec
SQL
}

# Crear las bases esperadas por la configuración/.env
create_db_if_missing "${ODOO_DB:-ecomparts_odoo_shared}"
create_db_if_missing "${DJANGO_DB_NAME:-ecomparts_marketplace}"

echo '✅ Bases de datos verificadas/creadas correctamente'
