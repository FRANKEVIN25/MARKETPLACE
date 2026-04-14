#!/bin/bash
set -e
cd ~/Escritorio/MARKETPLACE

echo "============================================"
echo "  🚀 ECOMPARTS — Iniciando servicios"
echo "============================================"

echo ""
echo "🧹 Limpiando contenedores anteriores..."
docker rm -f ecomparts-backend ecomparts-celery-worker 2>/dev/null || true

echo "🚀 Levantando servicios base..."
docker-compose up -d postgres redis odoo

echo "⏳ Esperando postgres (15s)..."
sleep 15

echo "🔧 Configurando red (detectando bridge automáticamente)..."
NETWORK_ID=$(docker network ls --filter name=marketplace_ecomparts-net --format "{{.ID}}")
if [ -n "$NETWORK_ID" ]; then
    BRIDGE_ID=$(echo $NETWORK_ID | cut -c1-12)
    sudo iptables -I DOCKER-USER -i br-$BRIDGE_ID -o br-$BRIDGE_ID -j ACCEPT 2>/dev/null || true
    echo "   ✅ Red configurada (bridge: br-$BRIDGE_ID)"
else
    echo "   ⚠️ No se pudo detectar el bridge"
fi

echo "🐍 Levantando backend Django..."
docker run -d \
  --name ecomparts-backend \
  --network marketplace_ecomparts-net \
  -p 8000:8000 \
  -e DJANGO_SECRET_KEY='django-insecure-ecomparts-2025-change-in-production' \
  -e DJANGO_DEBUG='True' \
  -e DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,ecomparts-backend,backend' \
  -e DJANGO_DB_NAME='ecomparts_marketplace' \
  -e DJANGO_DB_USER='ecomparts_user' \
  -e 'DJANGO_DB_PASSWORD=EcomParts!Secure2025' \
  -e DJANGO_DB_HOST='postgres' \
  -e DJANGO_DB_PORT='5432' \
  -e ODOO_URL='http://odoo:8069' \
  -e ODOO_DB='ecomparts_odoo_shared' \
  -e ODOO_USERNAME='admin' \
  -e ODOO_PASSWORD='admin' \
  -e REDIS_HOST='ecomparts-redis' \
  -e REDIS_PORT='6379' \
  -e CELERY_BROKER_URL='redis://ecomparts-redis:6379/0' \
  -e CELERY_RESULT_BACKEND='redis://ecomparts-redis:6379/0' \
  -e CLOUDINARY_CLOUD_NAME='dwvmmbpwv' \
  -e CLOUDINARY_API_KEY='166351963189161' \
  -e 'CLOUDINARY_API_SECRET=JybzUdHjMy4xxQkU2PwB7A1CCjg' \
  -v "$(pwd)/services/backend:/app" \
  marketplace_backend \
  /app/entrypoint.sh gunicorn ecomparts.wsgi:application --bind 0.0.0.0:8000 --workers 2

echo "⏳ Esperando backend (20s)..."
sleep 20

echo "⚙️  Levantando Celery worker..."
docker build -t marketplace_celery_worker ./services/backend/ -q
docker run -d \
  --name ecomparts-celery-worker \
  --network marketplace_ecomparts-net \
  -e DJANGO_SECRET_KEY='django-insecure-ecomparts-2025-change-in-production' \
  -e DJANGO_DEBUG='True' \
  -e DJANGO_ALLOWED_HOSTS='localhost,127.0.0.1,ecomparts-backend,backend' \
  -e DJANGO_DB_NAME='ecomparts_marketplace' \
  -e DJANGO_DB_USER='ecomparts_user' \
  -e 'DJANGO_DB_PASSWORD=EcomParts!Secure2025' \
  -e DJANGO_DB_HOST='postgres' \
  -e DJANGO_DB_PORT='5432' \
  -e ODOO_URL='http://odoo:8069' \
  -e ODOO_DB='ecomparts_odoo_shared' \
  -e ODOO_USERNAME='admin' \
  -e ODOO_PASSWORD='admin' \
  -e REDIS_HOST='ecomparts-redis' \
  -e REDIS_PORT='6379' \
  -e CELERY_BROKER_URL='redis://ecomparts-redis:6379/0' \
  -e CELERY_RESULT_BACKEND='redis://ecomparts-redis:6379/0' \
  -e CLOUDINARY_CLOUD_NAME='dwvmmbpwv' \
  -e CLOUDINARY_API_KEY='166351963189161' \
  -e 'CLOUDINARY_API_SECRET=JybzUdHjMy4xxQkU2PwB7A1CCjg' \
  -v "$(pwd)/services/backend:/app" \
  marketplace_celery_worker \
  celery -A ecomparts worker --loglevel=info --concurrency=4

echo "🎨 Levantando frontend SvelteKit..."
pkill -f "vite dev" 2>/dev/null || true
sleep 2
cd services/frontend && npm run dev &
cd ../..

echo ""
echo "============================================"
echo "  ✅ ECOMPARTS corriendo"
echo "============================================"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   Odoo:     http://localhost:8070"
echo "   Admin:    http://localhost:8000/admin"
echo "   Flower:   http://localhost:5555"
echo "   API Docs: http://localhost:8000/api/docs/"
echo "============================================"
