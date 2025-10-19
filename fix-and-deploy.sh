#!/bin/bash

# ==============================================
# SecureApprove - Build Fix & Deploy Script
# ==============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🔧 ARREGLANDO Y DESPLEGANDO SECUREAPPROVE"
echo "========================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    log_error "Archivo .env no encontrado!"
    log_info "Ejecutando generador de secretos..."
    
    if command -v node &> /dev/null; then
        node scripts/generate-production-secrets.js
        if [ -f ".env.secrets" ]; then
            cp .env.secrets .env
            log_success "Archivo .env creado"
        fi
    else
        log_error "Node.js no encontrado. Debes crear el archivo .env manualmente"
        exit 1
    fi
fi

# Generate package-lock.json for frontend if missing
log_info "Verificando package-lock.json del frontend..."
if [ ! -f "frontend/package-lock.json" ]; then
    log_info "Generando package-lock.json para el frontend..."
    cd frontend
    npm install --package-lock-only
    cd ..
    log_success "package-lock.json generado para frontend"
fi

# Clean any previous failed builds
log_info "Limpiando builds anteriores..."
docker compose down --remove-orphans 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# Build images one by one to better handle errors
log_info "Construyendo imágenes individualmente..."

# Build backend first
log_info "Construyendo backend..."
if docker compose build --no-cache api-1; then
    log_success "Backend construido exitosamente"
else
    log_error "Error construyendo backend"
    log_info "Intentando con --legacy-peer-deps..."
    # The Dockerfile already has --legacy-peer-deps
    exit 1
fi

# Build frontend
log_info "Construyendo frontend..."
if docker compose build --no-cache frontend; then
    log_success "Frontend construido exitosamente"
else
    log_error "Error construyendo frontend"
    exit 1
fi

# Build other services
log_info "Construyendo servicios restantes..."
docker compose build --no-cache

# Start services
log_info "Iniciando servicios..."
docker compose up -d

# Wait for services
log_info "Esperando que los servicios estén listos..."
sleep 30

# Check services
log_info "Verificando servicios..."
docker compose ps

log_success "¡Deployment completado!"
echo ""
echo "📋 SERVICIOS DISPONIBLES:"
echo "   • Frontend: http://localhost:3001"
echo "   • API: http://localhost:3000"
echo "   • Grafana: http://localhost:3002"
echo ""
echo "🔍 VER LOGS:"
echo "   docker compose logs -f"