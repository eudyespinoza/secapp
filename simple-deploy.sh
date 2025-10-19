#!/bin/bash

# ==============================================
# DEPLOY SIMPLE - SIN BACKUP
# ==============================================

echo "🚀 DEPLOYING SecureApprove (SIN BACKUP)"
echo "======================================"

# Generar .env si no existe
if [ ! -f ".env" ]; then
    echo "⚡ Generando .env..."
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo "✅ .env creado desde template"
        echo "⚠️  EDITA EL ARCHIVO .env Y CAMBIA LAS CONTRASEÑAS"
        exit 1
    else
        echo "❌ No hay .env.template. Usa: node scripts/generate-production-secrets.js"
        exit 1
    fi
fi

# Limpiar builds anteriores
echo "🧹 Limpiando..."
docker compose down --remove-orphans 2>/dev/null || true

# Solo construir servicios principales (sin backup)
echo "🔨 Construyendo servicios principales..."
docker compose build --no-cache api-1 api-2 api-3 frontend

# Iniciar servicios
echo "🚀 Iniciando servicios..."
docker compose up -d

echo ""
echo "✅ DONE!"
echo "Frontend: http://localhost:3001"
echo "API: http://localhost:3000"
echo ""
echo "Ver logs: docker compose logs -f"