#!/bin/bash
# ================================================
# SecureApprove - Quick Deploy Script (External Proxy)
# ================================================

set -e

echo "🚀 SecureApprove Quick Deploy (External Proxy)"
echo "=============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if proxy network exists
if ! docker network ls | grep -q "proxy"; then
    echo "⚠️ Creating external proxy network..."
    docker network create proxy
    echo "✅ Proxy network created"
else
    echo "✅ Proxy network already exists"
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.simple.yml down

# Build and start services
echo "🔨 Building and starting services..."
docker-compose -f docker-compose.simple.yml up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service status
echo "🔍 Checking service status..."
docker-compose -f docker-compose.simple.yml ps

# Show access information
echo ""
echo "🎉 Deployment complete!"
echo "=============================================="
echo "🌐 Application: http://secureapprove.local"
echo "👤 Admin Login: admin@secureapprove.com / admin123"
echo "� API Docs: http://secureapprove.local/api/docs/"
echo "�🗄️ Database: PostgreSQL (internal network)"
echo "🔄 Cache: Redis (internal network)"
echo ""
echo "🔗 Networks:"
echo "  - proxy (external): For proxy communication"
echo "  - secureapprove_internal: For internal services"
echo ""
echo "📝 Useful commands:"
echo "  View logs: docker-compose -f docker-compose.simple.yml logs -f"
echo "  Stop all: docker-compose -f docker-compose.simple.yml down"
echo "  Restart: docker-compose -f docker-compose.simple.yml restart"
echo "  Health check: curl http://secureapprove.local/health/"
echo ""