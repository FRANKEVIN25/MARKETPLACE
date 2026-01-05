#!/bin/sh
set -e

echo "🔍 Verificando conexión a PostgreSQL..."
until pg_isready -h "$DJANGO_DB_HOST" -p "$DJANGO_DB_PORT" -U "$DJANGO_DB_USER" > /dev/null 2>&1; do
    echo "⏳ Esperando a PostgreSQL..."
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
fi

echo "🚀 Iniciando servicio..."
exec "$@"
