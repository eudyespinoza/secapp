#!/bin/bash

echo "🚀 DEPLOYMENT MÍNIMO - Solo lo esencial"
echo "======================================"

# Verificar .env
if [ ! -f ".env" ]; then
    echo "❌ Falta archivo .env"
    echo "Crea uno básico copiando .env.template"
    exit 1
fi

# Limpiar todo
docker compose down --volumes --remove-orphans 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# Iniciar solo servicios esenciales (uno por uno)
echo "🔥 Iniciando MongoDB..."
docker compose up -d mongodb-primary mongodb-secondary1 mongodb-secondary2

sleep 10
echo "🔥 Iniciando Redis..."  
docker compose up -d redis-master redis-slave1 redis-slave2 sentinel1 sentinel2 sentinel3

sleep 10
echo "🔥 Iniciando API..."
docker compose up -d api-1

sleep 15
echo "🔥 Iniciando Frontend..."
docker compose up -d frontend

echo ""
echo "✅ Servicios mínimos iniciados"
echo "Verificar: docker compose ps"