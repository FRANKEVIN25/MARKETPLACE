#!/bin/bash
cd ~/Escritorio/MARKETPLACE

echo "🛑 Deteniendo worker..."
docker rm -f ecomparts-celery-worker 2>/dev/null || true

echo "🛑 Deteniendo todos los servicios..."
docker-compose down

echo "✅ Todo detenido correctamente"
