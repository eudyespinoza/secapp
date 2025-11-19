# ============================================================================
# SecureApprove - Production Deployment Script (PowerShell)
# ============================================================================
# This script handles the complete deployment process including:
# - Database migrations (including chat schema migration)
# - Static files collection
# - Service restart
# - Health checks
#
# Usage:
#   .\deploy.ps1                    # Standard deployment
#   .\deploy.ps1 -ForceChatReset    # Force chat schema recreation (data loss!)
#   .\deploy.ps1 -SkipMigrations    # Skip database migrations
#   .\deploy.ps1 -CheckOnly         # Only check, don't deploy
# ============================================================================

param(
    [string]$ComposeFile = "docker-compose.yml",
    [switch]$ForceChatReset,
    [switch]$SkipMigrations,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Step($step, $total, $message) {
    Write-ColorOutput Green "[$step/$total] $message"
}

function Write-Info($message) {
    Write-ColorOutput Cyan $message
}

function Write-Warning($message) {
    Write-ColorOutput Yellow $message
}

function Write-Error($message) {
    Write-ColorOutput Red $message
}

Write-Info "============================================================================"
Write-Info "  SecureApprove Production Deployment"
Write-Info "============================================================================"
Write-Output ""

# Check if Docker is available
try {
    docker --version | Out-Null
} catch {
    Write-Error "Error: Docker is not installed or not in PATH"
    exit 1
}

# Check if Docker Compose is available
$dockerComposeCmd = "docker compose"
try {
    & docker compose version | Out-Null
} catch {
    try {
        & docker-compose --version | Out-Null
        $dockerComposeCmd = "docker-compose"
    } catch {
        Write-Error "Error: Docker Compose is not installed"
        exit 1
    }
}

Write-Step 1 8 "Pre-deployment checks"
Write-Output "Using compose file: $ComposeFile"

# Check if compose file exists
if (-not (Test-Path $ComposeFile)) {
    Write-Error "Error: Compose file not found: $ComposeFile"
    exit 1
}

# Check if services are running
$runningServices = & $dockerComposeCmd -f $ComposeFile ps
if ($runningServices -notmatch "Up") {
    Write-Warning "Warning: Services are not running. Starting them first..."
    & $dockerComposeCmd -f $ComposeFile up -d
    Start-Sleep -Seconds 10
}

if ($CheckOnly) {
    Write-Info "[CHECK ONLY MODE] Checking chat schema migration status..."
    & $dockerComposeCmd -f $ComposeFile exec -T web python manage.py migrate_chat_schema --check-only
    Write-ColorOutput Green "Check complete!"
    exit 0
}

Write-Step 2 8 "Pulling latest images"
& $dockerComposeCmd -f $ComposeFile pull

Write-Step 3 8 "Building services"
& $dockerComposeCmd -f $ComposeFile build

Write-Info "[*] Applying new containers with updated image/config"
& $dockerComposeCmd -f $ComposeFile up -d

if (-not $SkipMigrations) {
    Write-Step 4 8 "Running database migrations"
    
    # Wait for database to be ready
    Write-Output "Waiting for database..."
    & $dockerComposeCmd -f $ComposeFile exec -T web bash -c @"
        while ! nc -z `$DB_HOST `$DB_PORT; do
            sleep 0.1
        done
        echo 'Database is ready!'
"@
    
    # Run standard migrations
    Write-Output "Running standard migrations..."
    & $dockerComposeCmd -f $ComposeFile exec -T web python manage.py migrate --noinput
    
    # Handle chat schema migration
    Write-Output "Checking chat schema migration..."
    if ($ForceChatReset) {
        Write-Warning "WARNING: Force chat reset enabled. All chat data will be deleted!"
        $confirmation = Read-Host "Type 'yes' to confirm"
        if ($confirmation -eq "yes") {
            & $dockerComposeCmd -f $ComposeFile exec -T web python manage.py migrate_chat_schema --force
        } else {
            Write-Output "Chat reset cancelled."
        }
    } else {
        # Check if migration is needed
        $checkResult = & $dockerComposeCmd -f $ComposeFile exec -T web python manage.py migrate_chat_schema --check-only 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Chat schema migration is needed."
            & $dockerComposeCmd -f $ComposeFile exec -T web python manage.py migrate_chat_schema
        } else {
            Write-Output "Chat schema is up to date."
        }
    }
} else {
    Write-Warning "[4/8] Skipping migrations (--SkipMigrations flag)"
}

Write-Step 5 8 "Collecting static files"
& $dockerComposeCmd -f $ComposeFile exec -T web python manage.py collectstatic --noinput --clear

Write-Step 6 8 "Compiling translations"
& $dockerComposeCmd -f $ComposeFile exec -T web python manage.py compilemessages 2>$null

Write-Step 7 8 "Restarting services"
& $dockerComposeCmd -f $ComposeFile restart web

# Wait for services to be healthy
Write-Output "Waiting for services to be healthy..."
Start-Sleep -Seconds 5

Write-Step 8 8 "Running health checks"

# Check web service
$webStatus = & $dockerComposeCmd -f $ComposeFile ps web
if ($webStatus -match "Up") {
    Write-ColorOutput Green "✓ Web service is running"
} else {
    Write-Error "✗ Web service is not running"
    & $dockerComposeCmd -f $ComposeFile logs --tail=50 web
    exit 1
}

# Check database
$dbStatus = & $dockerComposeCmd -f $ComposeFile ps db
if ($dbStatus -match "Up") {
    Write-ColorOutput Green "✓ Database service is running"
} else {
    Write-Error "✗ Database service is not running"
    exit 1
}

# Check Redis
$redisStatus = & $dockerComposeCmd -f $ComposeFile ps redis
if ($redisStatus -match "Up") {
    Write-ColorOutput Green "✓ Redis service is running"
} else {
    Write-Warning "⚠ Redis service is not running (chat real-time features may not work)"
}

# Test HTTP endpoint
Write-Output "Testing HTTP endpoint..."
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing -TimeoutSec 5
    $statusCode = $response.StatusCode
    if ($statusCode -eq 200 -or $statusCode -eq 302) {
        Write-ColorOutput Green "✓ HTTP endpoint is responding (HTTP $statusCode)"
    } else {
        Write-Warning "⚠ HTTP endpoint returned HTTP $statusCode"
    }
} catch {
    Write-Warning "⚠ Could not connect to HTTP endpoint"
}

# Display service status
Write-Output ""
Write-Info "============================================================================"
Write-ColorOutput Green "Deployment Summary:"
& $dockerComposeCmd -f $ComposeFile ps

Write-Output ""
Write-ColorOutput Green "✓ Deployment completed successfully!"
Write-Info "============================================================================"
Write-Output ""
Write-Output "Next steps:"
Write-Output "  1. Check logs: $dockerComposeCmd -f $ComposeFile logs -f web"
Write-Output "  2. Access the application: http://localhost:8000"
Write-Output "  3. Check admin panel: http://localhost:8000/admin"
Write-Output ""
Write-Output "Chat system status:"
Write-Output "  - Database tables: ✓ Created/Migrated"
Write-Output "  - Static files: ✓ Collected"

$redisRunning = docker ps -q -f name=redis
if ($redisRunning) {
    Write-Output "  - WebSocket support: ✓ Enabled"
} else {
    Write-Output "  - WebSocket support: ⚠ Disabled (Redis not running)"
}
Write-Output ""

exit 0
