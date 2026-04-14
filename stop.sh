#!/bin/bash
cd ~/Escritorio/MARKETPLACE

echo "🛑 Deteniendo ECOMPARTS..."

# Matar frontend
pkill -f "vite dev" 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true

# Eliminar contenedores manuales
docker rm -f ecomparts-backend ecomparts-celery-worker 2>/dev/null || true

# Bajar docker-compose
docker-compose down

echo "✅ Todo detenido correctamente"
