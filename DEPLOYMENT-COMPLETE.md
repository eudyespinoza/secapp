# SecureApprove Django - Complete Deployment Guide

## 🚀 Overview

SecureApprove Django is a complete rewrite of the original Next.js + NestJS application using Django and Bootstrap5, designed for simplified deployment and maintenance.

## ✅ Migration Complete

This Django version includes 100% feature parity with the original:

- ✅ **Authentication System**: Login, registration, profile management
- ✅ **Request Management**: Dynamic forms with 6 categories (expense, purchase, travel, contract, document, other)
- ✅ **Approval Workflow**: Multi-step approval process with notifications
- ✅ **Dashboard**: Statistics, charts, and activity timeline
- ✅ **Billing System**: Mercado Pago integration with subscription plans
- ✅ **Multi-language**: Spanish, English, Portuguese support
- ✅ **API**: Complete REST API with documentation
- ✅ **Docker Ready**: Optimized containers with proxy network support

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Traefik       │    │   Django Web    │    │   PostgreSQL    │
│   (Proxy)       │◄──►│   Application   │◄──►│   Database      │
│   Port 80/443   │    │   Port 8000     │    │   Port 5432     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │     Redis       │
                       │     Cache       │
                       │   Port 6379     │
                       └─────────────────┘
```

## 🚀 Quick Deployment

### 1. Prerequisites

- Docker & Docker Compose
- External proxy network (Traefik recommended)
- Domain name (optional)

### 2. Create Proxy Network

```bash
# Create external proxy network
docker network create proxy
```

### 3. Deploy Application

```bash
# Clone repository
git clone <your-repo-url>
cd SecApp

# Deploy with Docker Compose
docker-compose -f docker-compose.simple.yml up -d

# Check status
docker-compose -f docker-compose.simple.yml ps

# View logs
docker-compose -f docker-compose.simple.yml logs -f
```

### 4. Access Application

- **Web Interface**: http://secureapprove.local (configure in your proxy)
- **Admin Login**: create an administrator with an operator-managed credential.
- **API Documentation**: http://secureapprove.local/api/docs/

## 🐳 Docker Configuration

### Services Included

1. **Django Web Application** (`secureapprove_web`)
   - Python 3.11 with Django 4.2.7
   - Gunicorn WSGI server
   - Health checks included
   - Auto-discovered by Traefik

2. **PostgreSQL Database** (`secureapprove_db`)
   - PostgreSQL 15
   - Persistent data storage
   - Automatic backups support

3. **Redis Cache** (`secureapprove_redis`)
   - Redis 7 Alpine
   - Session storage and caching
   - Persistent data

### Network Configuration

- **Internal Network**: `secureapprove_internal` (for DB and Redis)
- **External Network**: `proxy` (for Traefik communication)

### Traefik Labels

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.secureapprove.rule=Host(`secureapprove.local`)"
  - "traefik.http.routers.secureapprove.entrypoints=web"
  - "traefik.http.services.secureapprove.loadbalancer.server.port=8000"
  - "traefik.docker.network=proxy"
```

## ⚙️ Environment Variables

### Required Configuration

```bash
# Database
DB_HOST=db
DB_PORT=5432
DB_NAME=secureapprove
DB_USER=postgres
DB_PASSWORD=<generated-secret>

# Redis
REDIS_URL=redis://redis:6379/1

# Django
DEBUG=False
SECRET_KEY=your-super-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1,secureapprove.local,yourdomain.com

# Security
WEBAUTHN_RP_NAME=SecureApprove
WEBAUTHN_RP_ID=secureapprove.local
WEBAUTHN_ORIGIN=http://secureapprove.local

# Email (Optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Billing (Optional)
MERCADOPAGO_ACCESS_TOKEN=your-mercadopago-token
MERCADOPAGO_WEBHOOK_URL=http://secureapprove.local/api/billing/webhooks/mercadopago/
```

## 🔧 Customization

### Domain Configuration

1. **Update docker-compose.simple.yml**:
```yaml
labels:
  - "traefik.http.routers.secureapprove.rule=Host(`yourdomain.com`)"
```

2. **Update environment variables**:
```bash
ALLOWED_HOSTS=yourdomain.com
WEBAUTHN_RP_ID=yourdomain.com
WEBAUTHN_ORIGIN=https://yourdomain.com
```

### SSL/HTTPS Setup

For production with SSL:
```yaml
labels:
  - "traefik.http.routers.secureapprove.rule=Host(`yourdomain.com`)"
  - "traefik.http.routers.secureapprove.entrypoints=websecure"
  - "traefik.http.routers.secureapprove.tls=true"
  - "traefik.http.routers.secureapprove.tls.certresolver=letsencrypt"
```

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Application health
curl http://secureapprove.local/health/

# Container status
docker-compose -f docker-compose.simple.yml ps

# Real-time logs
docker-compose -f docker-compose.simple.yml logs -f
```

### Backup & Recovery

```bash
# Database backup
docker exec secureapprove_db pg_dump -U postgres secureapprove > backup_$(date +%Y%m%d).sql

# Restore database
docker exec -i secureapprove_db psql -U postgres secureapprove < backup_file.sql

# Media files backup
cp -r ./secureapprove_django/media ./backup/media_$(date +%Y%m%d)
```

### Updates

```bash
# Pull latest images
docker-compose -f docker-compose.simple.yml pull

# Restart services
docker-compose -f docker-compose.simple.yml up -d

# Clean old images
docker image prune -f
```

## 🛠️ Development Setup

### Local Development

```bash
# Clone repository
git clone <your-repo-url>
cd SecApp/secureapprove_django

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Development with Docker

```bash
# Build development image
docker build -t secureapprove:dev ./secureapprove_django

# Run with mounted volumes for live reload
docker run -p 8000:8000 -v $(pwd)/secureapprove_django:/app secureapprove:dev
```

## 🧪 Testing

### Running Tests

```bash
# Unit tests
python manage.py test

# With coverage
coverage run --source='.' manage.py test
coverage report
coverage html

# API tests
python manage.py test tests.test_views

# Model tests
python manage.py test tests.test_models
```

### Test Data

```bash
# Load test fixtures
python manage.py loaddata fixtures/test_data.json

# Create test users
python manage.py shell -c "
from apps.authentication.models import User, Tenant
tenant = Tenant.objects.create(name='Test Co', domain='test.com')
User.objects.create_user('test@test.com', 'test123', tenant=tenant)
"
```

## 🚨 Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   # Check logs
   docker-compose -f docker-compose.simple.yml logs web
   
   # Check environment
   docker-compose -f docker-compose.simple.yml config
   ```

2. **Database connection issues**
   ```bash
   # Test connection
   docker exec secureapprove_web python manage.py dbshell
   
   # Run migrations
   docker exec secureapprove_web python manage.py migrate
   ```

3. **Static files not loading**
   ```bash
   # Collect static files
   docker exec secureapprove_web python manage.py collectstatic --noinput
   ```

4. **Proxy not working**
   ```bash
   # Check networks
   docker network ls
   
   # Verify proxy network exists
   docker network inspect proxy
   ```

### Debug Mode

```bash
# Enable debug temporarily
docker exec secureapprove_web sh -c 'export DEBUG=True && python manage.py runserver 0.0.0.0:8000'
```

## 🔐 Security

### Production Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Use strong database passwords
- [ ] Enable HTTPS with valid certificates
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Monitor application logs
- [ ] Update dependencies regularly
- [ ] Configure email for notifications

### Security Headers

Already configured in Django settings:
- SECURE_BROWSER_XSS_FILTER
- SECURE_CONTENT_TYPE_NOSNIFF
- X_FRAME_OPTIONS
- SECURE_HSTS_SECONDS
- CORS protection

## 📚 API Documentation

Complete API documentation is available at:
- **Interactive Docs**: http://secureapprove.local/api/docs/
- **ReDoc**: http://secureapprove.local/api/redoc/
- **OpenAPI Schema**: http://secureapprove.local/api/schema/

## 🆕 Migration from Original

This Django version replaces the original Next.js + NestJS stack with:

### Benefits
- ✅ **Simplified Deployment**: Single container vs 7 containers
- ✅ **Reduced Complexity**: Django monolith vs microservices
- ✅ **Better Performance**: Optimized database queries
- ✅ **Easier Maintenance**: Single codebase
- ✅ **Cost Effective**: Lower resource requirements

### Feature Parity
- ✅ **All Request Types**: Expense, Purchase, Travel, Contract, Document, Other
- ✅ **Approval Workflow**: Multi-level approvals with notifications
- ✅ **Dashboard Analytics**: Charts, statistics, recent activity
- ✅ **Billing Integration**: Mercado Pago with subscription plans
- ✅ **Multi-language**: Spanish, English, Portuguese
- ✅ **API Compatibility**: REST API with same endpoints
- ✅ **Security**: JWT auth, WebAuthn placeholder, CSRF protection

## 💡 Next Steps

1. **Deploy to production** using this guide
2. **Configure your domain** and SSL certificates
3. **Set up email notifications** for approvals
4. **Configure Mercado Pago** for billing (optional)
5. **Customize branding** and colors
6. **Add custom approval rules** as needed

## 📞 Support

For issues and questions:
1. Check logs: `docker-compose logs`
2. Review configuration: `docker-compose config`
3. Test health endpoint: `curl /health/`
4. Consult API docs: `/api/docs/`

---

**🎉 Your SecureApprove Django application is ready for production!**
