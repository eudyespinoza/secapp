#!/bin/bash

echo "🎯 DEPLOY COMPLETO - Frontend + Backend"
echo "======================================"

# Verificar .env
if [ ! -f ".env" ]; then
    echo "❌ Necesitas archivo .env"
    echo "Copia .env.template a .env y edita las contraseñas"
    exit 1
fi

echo "🧹 Limpiando builds anteriores..."
docker compose down --remove-orphans 2>/dev/null || true

echo "🔧 Construyendo BACKEND primero..."
if docker compose build --no-cache api-1 api-2 api-3; then
    echo "✅ Backend construido exitosamente"
else
    echo "❌ Error construyendo backend"
    exit 1
fi

echo "🔧 Construyendo FRONTEND (con fix)..."
if docker compose build --no-cache frontend; then
    echo "✅ Frontend construido exitosamente"
else
    echo "❌ Error construyendo frontend"
    exit 1
fi

echo "🗄️ Iniciando base de datos..."
docker compose up -d mongodb-primary mongodb-secondary1 mongodb-secondary2

echo "⏳ Esperando MongoDB..."
sleep 15

echo "🔄 Iniciando cache..."
docker compose up -d redis-master redis-slave1 redis-slave2

echo "⏳ Esperando Redis..."
sleep 10

echo "🚀 Iniciando API (3 instancias)..."
docker compose up -d api-1 api-2 api-3

echo "⏳ Esperando API..."
sleep 20

echo "🌐 Iniciando FRONTEND..."
docker compose up -d frontend

echo "⏳ Esperando Frontend..."
sleep 10

echo ""
echo "✅ APLICACIÓN COMPLETA DESPLEGADA!"
echo "=================================="
echo "🌐 Frontend: http://localhost:3001"
echo "🔌 API: http://localhost:3000"
echo ""
echo "📊 Verificar estado:"
echo "docker compose ps"
echo ""
echo "📝 Ver logs:"
echo "docker compose logs -f api-1"
echo "docker compose logs -f frontend"