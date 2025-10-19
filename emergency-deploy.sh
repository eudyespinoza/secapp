#!/bin/bash

echo "🆘 EMERGENCY DEPLOY - Mínimo absoluto"
echo "===================================="

# Parar todo
docker compose down --remove-orphans 2>/dev/null || true

# Solo construir frontend con fix
echo "🔧 Construyendo SOLO frontend..."
docker compose build --no-cache frontend

if [ $? -eq 0 ]; then
    echo "✅ Frontend construido exitosamente"
    
    # Construir API
    echo "🔧 Construyendo API..."
    docker compose build --no-cache api-1
    
    if [ $? -eq 0 ]; then
        echo "✅ API construida exitosamente"
        echo "🚀 Iniciando servicios básicos..."
        docker compose up -d mongodb-primary redis-master api-1 frontend
        echo "✅ LISTO!"
        echo "Frontend: http://localhost:3001"
        echo "API: http://localhost:3000"
    else
        echo "❌ Error en API"
    fi
else
    echo "❌ Error en Frontend"
fi