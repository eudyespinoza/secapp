#!/bin/bash
# ================================================
# SecureApprove - Docker Initialization Script
# ================================================

set -e

echo "[*] Starting SecureApprove initialization..."

# Wait for database
echo "[*] Waiting for PostgreSQL on ${DB_HOST}:${DB_PORT}..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 0.1
done
echo "[+] PostgreSQL is ready!"

# Wait for Redis
echo "[*] Waiting for Redis on redis:6379..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "[+] Redis is ready!"

# Run migrations
echo "[*] Creating initial migrations..."
python manage.py makemigrations authentication
python manage.py makemigrations tenants
python manage.py makemigrations requests
python manage.py makemigrations billing
python manage.py makemigrations chat

# Migrate chat schema BEFORE running all migrations
# This handles old to new schema transition automatically
echo "[*] Checking chat schema migration..."
python manage.py migrate_chat_schema --force || {
  echo "[!] Chat schema migration had issues, but continuing..."
}

echo "[*] Running database migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist (admin@secureapprove.com)
echo "[*] Ensuring default superuser (admin@secureapprove.com)..."
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model

User = get_user_model()
email = 'admin@secureapprove.com'

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        username='admin',
        email=email,
        name='Admin User',
        password='admin123',
    )
    print('[+] Superuser created: admin@secureapprove.com / admin123')
else:
    print('[=] Superuser already exists')
EOF

# Compile messages
echo "[*] Compiling translation messages..."
if ! python manage.py compilemessages; then
  echo "[!] No translations to compile or compilemessages failed"
fi

# Setup admin user configuration for eudyespinoza@gmail.com
echo "[*] Setting up primary admin user configuration..."
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant

User = get_user_model()
email = 'eudyespinoza@gmail.com'

try:
    # Ensure admin user exists (passwordless, WebAuthn only)
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': 'eudyespinoza',
            'name': 'Eudys Espinoza',
            'role': 'admin',
            'is_active': True,
        },
    )

    # Make sure this account has full admin flags
    user.is_superuser = True
    user.is_staff = True
    user.role = 'admin'
    # No password is set here on purpose: this account is meant to use WebAuthn
    user.save()

    # Ensure the primary tenant "secureapprove" exists
    tenant, created_tenant = Tenant.objects.get_or_create(
        key='secureapprove',
        defaults={
            'name': 'SecureApprove',
            'plan_id': 'scale',
            'seats': 10,
            'approver_limit': 999,
            'status': 'active',
            'is_active': True,
            'billing': {
                'provider': 'internal',
                'provisioned_via': 'entrypoint',
            },
        },
    )

    # Associate the admin user with this tenant
    user.tenant = tenant
    user.save(update_fields=['tenant'])

    print(f'[+] Configured {user.email} as admin with tenant {tenant.name}')
except Exception as e:
    print(f'[!] Admin setup error: {e}')
EOF

echo "[*] Initialization complete!"
echo "[*] Access the application at: http://localhost:8000"
echo "[*] Admin login: admin@secureapprove.com / admin123"
echo "[*] Your WebAuthn admin login: eudyespinoza@gmail.com"

# Start the application
exec "$@"

