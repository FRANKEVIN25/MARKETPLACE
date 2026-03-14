#!/bin/bash
set -e
cd ~/Escritorio/MARKETPLACE

echo "🔧 Configurando reglas de red (iptables)..."
sudo iptables -I DOCKER-USER -i br-45d67392cff6 -o br-45d67392cff6 -j ACCEPT 2>/dev/null || true

echo "🧹 Eliminando worker anterior..."
docker rm -f ecomparts-celery-worker 2>/dev/null || true

echo "🚀 Levantando todos los servicios..."
docker-compose up -d --no-recreate 2>/dev/null || docker-compose up -d

echo "🔨 Reconstruyendo worker con código actualizado..."
docker rm -f ecomparts-celery-worker 2>/dev/null || true
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
  -v "$(pwd)/services/backend:/app" \
  marketplace_celery_worker \
  celery -A ecomparts worker --loglevel=info --concurrency=4

echo ""
echo "✅ ECOMPARTS corriendo:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo "   Odoo:     http://localhost:8070"
echo "   Admin:    http://localhost:8000/admin"
echo "   Flower:   http://localhost:5555"
