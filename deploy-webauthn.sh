#!/bin/bash

# ==================================================
# SecureApprove Django - WebAuthn Deployment Script
# ==================================================

echo "🔒 Deploying SecureApprove Django with WebAuthn Support"
echo "=================================================="

# Stop existing containers
echo "⏹️ Stopping existing containers..."
docker-compose -f docker-compose.simple.yml down

# Remove old Django image to force rebuild
echo "🧹 Cleaning up old images..."
docker image rm secapp-web 2>/dev/null || true

# Rebuild with new WebAuthn dependencies
echo "🔧 Building Django container with WebAuthn support..."
docker-compose -f docker-compose.simple.yml build --no-cache web

# Start services
echo "🚀 Starting services..."
docker-compose -f docker-compose.simple.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Run migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.simple.yml exec web python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose -f docker-compose.simple.yml exec web python manage.py collectstatic --noinput

# Check container status
echo "📊 Container status:"
docker-compose -f docker-compose.simple.yml ps

# Show logs for verification
echo "📋 Recent logs:"
docker-compose -f docker-compose.simple.yml logs --tail=20 web

echo ""
echo "✅ WebAuthn deployment complete!"
echo "🌐 Access your application at: http://localhost:8000"
echo "🔐 WebAuthn Login: http://localhost:8000/auth/login/"
echo "📝 WebAuthn Register: http://localhost:8000/auth/register/"
echo ""
echo "🔍 To view logs: docker-compose -f docker-compose.simple.yml logs -f web"
echo "🛠️ To access shell: docker-compose -f docker-compose.simple.yml exec web bash"