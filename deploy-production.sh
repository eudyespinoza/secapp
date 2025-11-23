#!/bin/bash
# ================================================
# SecureApprove - Production Deployment Script
# ================================================

set -e

echo "================================================"
echo "SecureApprove Production Deployment"
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found. Are you in the project root?${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[1/6] Pulling latest code from repository...${NC}"
git pull origin master

echo -e "\n${YELLOW}[2/6] Stopping services...${NC}"
docker compose down

echo -e "\n${YELLOW}[3/6] Rebuilding web container (includes collectstatic)...${NC}"
docker compose build web --no-cache

echo -e "\n${YELLOW}[4/6] Starting services...${NC}"
docker compose up -d

echo -e "\n${YELLOW}[5/6] Waiting for services to be ready...${NC}"
sleep 10

echo -e "\n${YELLOW}[5.5/6] Running database migrations...${NC}"
echo "Creating missing migrations..."
docker compose exec -T web python manage.py makemigrations --noinput
echo "Applying migrations..."
docker compose exec -T web python manage.py migrate --noinput

echo -e "\n${YELLOW}[6/6] Verifying deployment...${NC}"

# Check if web is running
if docker compose ps | grep -q "web.*running"; then
    echo -e "${GREEN}✓ Web service is running${NC}"
else
    echo -e "${RED}✗ Web service is not running${NC}"
    docker compose logs web --tail=50
    exit 1
fi

# Check if tenant_chat.js exists in container
echo -e "\nChecking for tenant_chat.js..."
if docker compose exec -T web test -f /app/staticfiles/chat/js/tenant_chat.js; then
    echo -e "${GREEN}✓ tenant_chat.js found in staticfiles${NC}"
    docker compose exec -T web ls -lh /app/staticfiles/chat/js/tenant_chat.js
else
    echo -e "${RED}✗ tenant_chat.js NOT found in staticfiles${NC}"
    echo "Checking source location..."
    if docker compose exec -T web test -f /app/apps/chat/static/chat/js/tenant_chat.js; then
        echo -e "${YELLOW}! File exists in source but not in staticfiles${NC}"
        echo -e "${YELLOW}! Running collectstatic manually...${NC}"
        docker compose exec -T web python manage.py collectstatic --noinput
    else
        echo -e "${RED}✗ File not found in source either${NC}"
        exit 1
    fi
fi

# Check health endpoint
echo -e "\nChecking health endpoint..."
sleep 5
if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi

echo -e "\n${GREEN}================================================"
echo "✓ Deployment completed successfully!"
echo "================================================${NC}"
echo ""
echo "Service URLs:"
echo "  - Application: https://secureapprove.com"
echo "  - Health: http://localhost:8000/health/"
echo ""
echo "Useful commands:"
echo "  - View logs: docker compose logs -f web"
echo "  - Check status: docker compose ps"
echo "  - Restart: docker compose restart web"
echo ""
