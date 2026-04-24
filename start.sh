#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "❌ No se encontró Docker Compose"
  exit 1
fi

# Defaults locales para entorno de desarrollo.
export POSTGRES_USER="${POSTGRES_USER:-ecomparts_user}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-EcomParts!Secure2025}"
export POSTGRES_DB="${POSTGRES_DB:-postgres}"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-django-insecure-ecomparts-2025-change-in-production}"
export DJANGO_DEBUG="${DJANGO_DEBUG:-True}"
export DJANGO_ALLOWED_HOSTS="${DJANGO_ALLOWED_HOSTS:-localhost,127.0.0.1,ecomparts-backend,backend}"
export DJANGO_DB_NAME="${DJANGO_DB_NAME:-ecomparts_marketplace}"
export DJANGO_DB_USER="${DJANGO_DB_USER:-ecomparts_user}"
export DJANGO_DB_PASSWORD="${DJANGO_DB_PASSWORD:-$POSTGRES_PASSWORD}"
export DJANGO_DB_HOST="${DJANGO_DB_HOST:-postgres}"
export DJANGO_DB_PORT="${DJANGO_DB_PORT:-5432}"
export ODOO_PORT="${ODOO_PORT:-8070}"
export ODOO_URL="${ODOO_URL:-http://odoo:8069}"
export ODOO_DB="${ODOO_DB:-ecomparts_odoo_shared}"
export ODOO_USERNAME="${ODOO_USERNAME:-service@ecomparts.local}"
export ODOO_PASSWORD="${ODOO_PASSWORD:-Service!2025}"
export ODOO_SERVICE_LOGIN="${ODOO_SERVICE_LOGIN:-$ODOO_USERNAME}"
export ODOO_SERVICE_PASS="${ODOO_SERVICE_PASS:-$ODOO_PASSWORD}"
export ODOO_ADMIN_LOGIN="${ODOO_ADMIN_LOGIN:-admin2@ecomparts.local}"
export ODOO_ADMIN_PASS="${ODOO_ADMIN_PASS:-Admin!2025}"
export ODOO_ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"
export REDIS_HOST="${REDIS_HOST:-redis}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://redis:6379/0}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://redis:6379/0}"
export CORS_ALLOWED_ORIGINS="${CORS_ALLOWED_ORIGINS:-http://localhost:5173,http://localhost:3000}"
export TIMEZONE="${TIMEZONE:-America/Lima}"
export LANGUAGE_CODE="${LANGUAGE_CODE:-es-pe}"
export COUNTRY_CODE="${COUNTRY_CODE:-PE}"
export CLOUDINARY_CLOUD_NAME="${CLOUDINARY_CLOUD_NAME:-}"
export CLOUDINARY_API_KEY="${CLOUDINARY_API_KEY:-}"
export CLOUDINARY_API_SECRET="${CLOUDINARY_API_SECRET:-}"

if [[ -z "$CLOUDINARY_CLOUD_NAME" || -z "$CLOUDINARY_API_KEY" || -z "$CLOUDINARY_API_SECRET" ]]; then
  echo "⚠️  Variables CLOUDINARY_* no configuradas. Los servicios levantarán, pero la subida de imágenes desde Odoo fallará hasta definirlas."
fi

echo "🔨 Reconstruyendo imágenes afectadas por requirements.txt y settings.py..."
"${COMPOSE_CMD[@]}" build backend celery_worker celery_beat flower

echo "🚀 Levantando stack principal..."
"${COMPOSE_CMD[@]}" up -d postgres redis odoo backend celery_worker celery_beat flower

echo ""
echo "✅ ECOMPARTS corriendo:"
echo "   Backend:  http://localhost:8000"
echo "   Odoo:     http://localhost:${ODOO_PORT}"
echo "   Admin:    http://localhost:8000/admin"
echo "   Flower:   http://localhost:5555"
echo "   Frontend: iniciar aparte con npm run dev en services/frontend"
