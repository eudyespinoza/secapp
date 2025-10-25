#!/bin/bash
# ================================================
# SecureApprove - Docker Initialization Script
# ================================================

set -e

echo "🚀 Starting SecureApprove initialization..."

# Wait for database
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "✅ PostgreSQL is ready!"

# Wait for Redis
echo "⏳ Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "✅ Redis is ready!"

# Run migrations
echo "🔄 Creating initial migrations..."
python manage.py makemigrations authentication
python manage.py makemigrations tenants
python manage.py makemigrations requests
python manage.py makemigrations billing

echo "🔄 Running database migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist
echo "👤 Creating superuser..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@secureapprove.com').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@secureapprove.com',
        name='Admin User',
        password='admin123'
    )
    print('✅ Superuser created: admin@secureapprove.com / admin123')
else:
    print('ℹ️ Superuser already exists')
EOF

# Compile messages
echo "🌐 Compiling translation messages..."
python manage.py compilemessages || echo "⚠️ No translations to compile"

# Setup admin user configuration
echo "👨‍💼 Setting up admin user configuration..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant
try:
    User = get_user_model()
    user = User.objects.filter(email='eudyespinoza@gmail.com').first()
    if user:
        user.is_superuser = True
        user.is_staff = True
        user.role = 'admin'
        user.save()
        tenant, created = Tenant.objects.get_or_create(
            key='admin-tenant',
            defaults={
                'name': 'SecureApprove Admin',
                'plan_id': 'scale',
                'approver_limit': 999,
                'status': 'active',
                'is_active': True
            }
        )
        user.tenant = tenant
        user.save()
        print(f'✅ Configured {user.email} as admin with tenant {tenant.name}')
    else:
        print('⚠️ User eudyespinoza@gmail.com not found - will be configured on first login')
except Exception as e:
    print(f'⚠️ Admin setup error: {e}')
EOF

echo "🎉 Initialization complete!"
echo "🌐 Access the application at: http://localhost:8000"
echo "👤 Admin login: admin@secureapprove.com / admin123"
echo "👤 Your admin login: eudyespinoza@gmail.com (WebAuthn)"

# Start the application
exec "$@"