#!/bin/sh
set -e
echo "🔍 Verificando conexión a PostgreSQL..."
MAX_RETRIES=30
RETRY_COUNT=0
until timeout 3 python -c "import psycopg2; psycopg2.connect(host='$DJANGO_DB_HOST', port='$DJANGO_DB_PORT', database='$DJANGO_DB_NAME', user='$DJANGO_DB_USER', password='$DJANGO_DB_PASSWORD', connect_timeout=3)" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "❌ No se pudo conectar a PostgreSQL después de $MAX_RETRIES intentos"
        exit 1
    fi
    echo "⏳ Esperando a PostgreSQL... (intento $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done
echo "✅ PostgreSQL disponible"
echo "🔍 Verificando conexión a Redis..."
until nc -z "$REDIS_HOST" "$REDIS_PORT" > /dev/null 2>&1; do
    echo "⏳ Esperando a Redis..."
    sleep 2
done
echo "✅ Redis disponible"
# Solo hacer migrate si es el contenedor backend (no celery)
if [ "$1" = "gunicorn" ] || [ "$1" = "python" ]; then
    echo "🗄️ Aplicando migraciones..."
    python manage.py migrate --noinput || {
        echo "❌ Error en migraciones"
        exit 1
    }
    echo "📦 Recolectando archivos estáticos..."
    python manage.py collectstatic --noinput || {
        echo "⚠️ Warning: collectstatic falló"
    }
    echo "⚙️ Configurando Odoo (módulos, permisos, aislamiento)..."
    python manage.py setup_odoo || {
        echo "⚠️ Warning: setup_odoo falló (Odoo puede no estar listo aún)"
    }
fi
echo "🚀 Iniciando servicio..."
exec "$@"