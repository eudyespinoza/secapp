#!/bin/bash

# ==============================================
# SecureApprove - Quick Production Setup
# ==============================================
# This script generates .env and runs deployment
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

echo "🚀 SETUP RÁPIDO DE SECUREAPPROVE"
echo "================================="

# Generate secrets if .env doesn't exist
if [ ! -f ".env" ]; then
    log_info "Generando archivo .env con secretos seguros..."
    
    # Generate secrets using Node.js
    if command -v node &> /dev/null; then
        node scripts/generate-production-secrets.js
        if [ -f ".env.secrets" ]; then
            cp .env.secrets .env
            log_success "Archivo .env creado con secretos seguros"
        else
            log_warning "No se pudo generar .env.secrets, usando template"
            cp .env.template .env
        fi
    else
        log_warning "Node.js no encontrado, usando template básico"
        cp .env.template .env
        log_info "⚠️  IMPORTANTE: Debes cambiar las contraseñas en el archivo .env"
    fi
else
    log_success "Archivo .env ya existe"
fi

# Run the main deployment script
log_info "Ejecutando deployment..."
./deploy-production.sh

log_success "Setup completado!"