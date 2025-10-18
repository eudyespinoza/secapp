#!/bin/bash

# ==============================================
# SecureApprove - Production Deployment Script
# ==============================================
# Usage: ./deploy-production.sh
# ==============================================

set -e  # Exit on any error

echo "🚀 INICIANDO DEPLOYMENT DE SECUREAPPROVE EN PRODUCCIÓN"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function for colored output
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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   log_error "Este script no debe ejecutarse como root"
   exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    log_error "Archivo .env no encontrado!"
    log_info "Por favor crea el archivo .env con la configuración de producción"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_error "Docker no está instalado"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose no está instalado"
    exit 1
fi

log_info "Verificando dependencias..."
log_success "Docker y Docker Compose encontrados"

# Create external Traefik network if it doesn't exist
log_info "Verificando red de Traefik..."
if ! docker network ls | grep -q "traefik_proxy"; then
    log_info "Creando red traefik_proxy..."
    docker network create traefik_proxy
    log_success "Red traefik_proxy creada"
else
    log_success "Red traefik_proxy ya existe"
fi

# Create data directories
log_info "Creando directorios de datos..."
mkdir -p ./data/mongodb/data
mkdir -p ./data/mongodb/logs
mkdir -p ./data/redis/data
mkdir -p ./data/prometheus/data
mkdir -p ./data/grafana/data
mkdir -p ./data/grafana/logs
mkdir -p ./backups
mkdir -p ./logs

# Set proper permissions
log_info "Configurando permisos..."
sudo chown -R $USER:$USER ./data
sudo chown -R $USER:$USER ./backups
sudo chown -R $USER:$USER ./logs

# Create SSL certificates directory if it doesn't exist
if [ ! -d "./certs" ]; then
    log_info "Creando directorio de certificados SSL..."
    mkdir -p ./certs
fi

# Stop any existing containers
log_info "Deteniendo contenedores existentes..."
docker-compose down --remove-orphans 2>/dev/null || true

# Pull latest images
log_info "Descargando imágenes más recientes..."
docker-compose pull

# Build custom images
log_info "Construyendo imágenes personalizadas..."
docker-compose build --no-cache

# Start services
log_info "Iniciando servicios en modo producción..."
docker-compose up -d

# Wait for services to be ready
log_info "Esperando que los servicios estén listos..."

# Wait for MongoDB
log_info "Esperando MongoDB..."
sleep 30

# Wait for API
log_info "Esperando API..."
for i in {1..30}; do
    if curl -f -s http://localhost:3000/api/health >/dev/null 2>&1; then
        log_success "API está respondiendo"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "La API no respondió después de 5 minutos"
        exit 1
    fi
    sleep 10
done

# Wait for Frontend
log_info "Esperando Frontend..."
for i in {1..30}; do
    if curl -f -s http://localhost:3001 >/dev/null 2>&1; then
        log_success "Frontend está respondiendo"
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "El Frontend no respondió después de 5 minutos"
        exit 1
    fi
    sleep 10
done

# Show status
log_info "Verificando estado de los servicios..."
docker-compose ps

# Show logs summary
log_info "Últimos logs de los servicios:"
echo "================================"
docker-compose logs --tail=10 api
docker-compose logs --tail=10 frontend

echo ""
echo "🎉 DEPLOYMENT COMPLETADO EXITOSAMENTE!"
echo "======================================"
echo ""
log_success "SecureApprove está ejecutándose en producción"
echo ""
echo "📋 INFORMACIÓN DE LOS SERVICIOS:"
echo "   • Frontend: http://localhost:3001"
echo "   • API: http://localhost:3000"
echo "   • Grafana: http://localhost:3002"
echo "   • Prometheus: http://localhost:9091"
echo ""
echo "🔍 COMANDOS ÚTILES:"
echo "   • Ver logs: docker-compose logs -f [servicio]"
echo "   • Reiniciar: docker-compose restart [servicio]"
echo "   • Detener: docker-compose down"
echo "   • Estado: docker-compose ps"
echo ""
log_warning "Recuerda configurar tu proxy Traefik para que apunte a estos servicios"
echo ""