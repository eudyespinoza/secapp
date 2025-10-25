# ==================================================
# SecureApprove Django - WebAuthn Deployment Script (Windows)
# ==================================================

Write-Host "🔒 Deploying SecureApprove Django with WebAuthn Support" -ForegroundColor Green
Write-Host "=================================================="

# Stop existing containers
Write-Host "⏹️ Stopping existing containers..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml down

# Remove old Django image to force rebuild
Write-Host "🧹 Cleaning up old images..." -ForegroundColor Yellow
docker image rm secapp-web 2>$null

# Rebuild with new WebAuthn dependencies
Write-Host "🔧 Building Django container with WebAuthn support..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml build --no-cache web

# Start services
Write-Host "🚀 Starting services..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml up -d

# Wait for services to be ready
Write-Host "⏳ Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Run migrations
Write-Host "🗄️ Running database migrations..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml exec web python manage.py migrate

# Collect static files
Write-Host "📁 Collecting static files..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml exec web python manage.py collectstatic --noinput

# Check container status
Write-Host "📊 Container status:" -ForegroundColor Cyan
docker-compose -f docker-compose.simple.yml ps

# Show logs for verification
Write-Host "📋 Recent logs:" -ForegroundColor Cyan
docker-compose -f docker-compose.simple.yml logs --tail=20 web

Write-Host ""
Write-Host "✅ WebAuthn deployment complete!" -ForegroundColor Green
Write-Host "🌐 Access your application at: http://localhost:8000" -ForegroundColor White
Write-Host "🔐 WebAuthn Login: http://localhost:8000/auth/login/" -ForegroundColor White
Write-Host "📝 WebAuthn Register: http://localhost:8000/auth/register/" -ForegroundColor White
Write-Host ""
Write-Host "🔍 To view logs: docker-compose -f docker-compose.simple.yml logs -f web" -ForegroundColor Gray
Write-Host "🛠️ To access shell: docker-compose -f docker-compose.simple.yml exec web bash" -ForegroundColor Gray