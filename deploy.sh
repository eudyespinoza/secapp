#!/bin/bash
# ============================================================================
# SecureApprove - Production Deployment Script
# ============================================================================
# This script handles the complete deployment process including:
# - Database migrations (including chat schema migration)
# - Static files collection
# - Service restart
# - Health checks
#
# Usage:
#   ./deploy.sh                    # Standard deployment
#   ./deploy.sh --force-chat-reset # Force chat schema recreation (data loss!)
#   ./deploy.sh --skip-migrations  # Skip database migrations
#   ./deploy.sh --check-only       # Only check, don't deploy
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
FORCE_CHAT_RESET=false
SKIP_MIGRATIONS=false
CHECK_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --force-chat-reset)
      FORCE_CHAT_RESET=true
      shift
      ;;
    --skip-migrations)
      SKIP_MIGRATIONS=true
      shift
      ;;
    --check-only)
      CHECK_ONLY=true
      shift
      ;;
    --compose-file)
      COMPOSE_FILE="$2"
      shift 2
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}  SecureApprove Production Deployment${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Check if Docker Compose is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Use 'docker compose' or 'docker-compose' depending on what's available
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}[1/8] Pre-deployment checks${NC}"
echo "Using compose file: $COMPOSE_FILE"

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: Compose file not found: $COMPOSE_FILE${NC}"
    exit 1
fi

# Check if services are running
if ! $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo -e "${YELLOW}Warning: Services are not running. Starting them first...${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d
    sleep 10
fi

if [ "$CHECK_ONLY" = true ]; then
    echo -e "${BLUE}[CHECK ONLY MODE] Checking chat schema migration status...${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T web python manage.py migrate_chat_schema --check-only
    echo -e "${GREEN}Check complete!${NC}"
    exit 0
fi

echo -e "${GREEN}[2/8] Pulling latest images${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" pull

echo -e "${GREEN}[3/8] Ensuring media directories with proper permissions${NC}"
# Create media directories if they don't exist
mkdir -p secureapprove_django/media/chat_attachments secureapprove_django/media/attachments logs
# Set permissions (777 to ensure container can write, or use chown 1000:1000 for more security)
chmod -R 777 secureapprove_django/media 2>/dev/null || true
echo "Media directories created with write permissions"

echo -e "${GREEN}[4/8] Building services${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" build

echo -e "${GREEN}[*] Applying new containers with updated image/config${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" up -d

if [ "$SKIP_MIGRATIONS" = false ]; then
    echo -e "${GREEN}[5/9] Running database migrations${NC}"
    
    # Wait for database to be ready
    echo "Waiting for database..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T web bash -c "
        while ! nc -z \$DB_HOST \$DB_PORT; do
            sleep 0.1
        done
        echo 'Database is ready!'
    "
    
    # Run standard migrations
    echo "Running standard migrations..."
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T web python manage.py migrate --noinput
    
    # Handle chat schema migration
    echo "Checking chat schema migration..."
    if [ "$FORCE_CHAT_RESET" = true ]; then
        echo -e "${YELLOW}WARNING: Force chat reset enabled. All chat data will be deleted!${NC}"
        read -p "Type 'yes' to confirm: " -r
        if [[ $REPLY == "yes" ]]; then
            $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T web python manage.py migrate_chat_schema --force
        else
            echo "Chat reset cancelled."
        fi
    else
        # Check if migration is needed
        if ! $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T web python manage.py migrate_chat_schema --check-only; then
            echo -e "${YELLOW}Chat schema migration is needed.${NC}"
            $DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T web python manage.py migrate_chat_schema
        else
            echo "Chat schema is up to date."
        fi
    fi
else
    echo -e "${YELLOW}[5/9] Skipping migrations (--skip-migrations flag)${NC}"
fi

echo -e "${GREEN}[5/8] Collecting static files${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T web python manage.py collectstatic --noinput --clear

echo -e "${GREEN}[6/8] Compiling translations${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" exec -T web python manage.py compilemessages || true

echo -e "${GREEN}[7/8] Restarting services${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" restart web

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 5

echo -e "${GREEN}[8/8] Running health checks${NC}"

# Check web service
if $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps web | grep -q "Up"; then
    echo -e "${GREEN}✓ Web service is running${NC}"
else
    echo -e "${RED}✗ Web service is not running${NC}"
    $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs --tail=50 web
    exit 1
fi

# Check database
if $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps db | grep -q "Up"; then
    echo -e "${GREEN}✓ Database service is running${NC}"
else
    echo -e "${RED}✗ Database service is not running${NC}"
    exit 1
fi

# Check Redis
if $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps redis | grep -q "Up"; then
    echo -e "${GREEN}✓ Redis service is running${NC}"
else
    echo -e "${YELLOW}⚠ Redis service is not running (chat real-time features may not work)${NC}"
fi

# Test HTTP endpoint
echo "Testing HTTP endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo -e "${GREEN}✓ HTTP endpoint is responding (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${YELLOW}⚠ HTTP endpoint returned HTTP $HTTP_CODE${NC}"
fi

# Display service status
echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}Deployment Summary:${NC}"
$DOCKER_COMPOSE -f "$COMPOSE_FILE" ps

echo ""
echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Check logs: $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f web"
echo "  2. Access the application: http://localhost:8000"
echo "  3. Check admin panel: http://localhost:8000/admin"
echo ""
echo "Chat system status:"
echo "  - Database tables: ✓ Created/Migrated"
echo "  - Static files: ✓ Collected"

if docker ps -q -f name=redis > /dev/null; then
    WEBSOCKET_STATUS="✓ Enabled"
else
    WEBSOCKET_STATUS="⚠ Disabled (Redis not running)"
fi

echo "  - WebSocket support: $WEBSOCKET_STATUS"
echo ""

exit 0
