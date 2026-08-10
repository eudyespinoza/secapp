#!/bin/bash
# ================================================
# SecureApprove - Docker Initialization Script
# ================================================

set -e

echo "[*] Starting SecureApprove initialization..."

# Ensure media directories exist and are writable
echo "[*] Ensuring media directories exist..."
mkdir -p /app/media/chat_attachments /app/media/attachments /app/logs 2>/dev/null || true

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

# Migrate chat schema BEFORE running all migrations
# This handles old to new schema transition automatically
echo "[*] Checking chat schema migration..."
python manage.py migrate_chat_schema --force || {
  echo "[!] Chat schema migration had issues, but continuing..."
}

echo "[*] Running database migrations..."
python manage.py migrate --noinput

# Optionally create a bootstrap superuser. Production leaves these variables
# unset after initial provisioning; no fixed account or password is embedded.
if [ -n "${SECUREAPPROVE_BOOTSTRAP_ADMIN_EMAIL:-}" ] || [ -n "${SECUREAPPROVE_BOOTSTRAP_ADMIN_PASSWORD:-}" ]; then
  if [ -z "${SECUREAPPROVE_BOOTSTRAP_ADMIN_EMAIL:-}" ] || [ -z "${SECUREAPPROVE_BOOTSTRAP_ADMIN_PASSWORD:-}" ]; then
    echo "[!] Both bootstrap admin email and password are required" >&2
    exit 1
  fi
  echo "[*] Ensuring configured bootstrap superuser exists..."
  python manage.py shell << 'EOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = os.environ['SECUREAPPROVE_BOOTSTRAP_ADMIN_EMAIL'].strip().lower()

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(
        username=email.split('@', 1)[0],
        email=email,
        name='Bootstrap Admin',
        password=os.environ['SECUREAPPROVE_BOOTSTRAP_ADMIN_PASSWORD'],
    )
    print('[+] Bootstrap superuser created')
else:
    print('[=] Bootstrap superuser already exists')
EOF
else
  echo "[*] Bootstrap superuser disabled"
fi

# Compile messages
echo "[*] Compiling translation messages..."
if ! python manage.py compilemessages; then
  echo "[!] No translations to compile or compilemessages failed"
fi

# Optional primary WebAuthn administrator bootstrap. This never runs unless an
# explicit email is supplied by the operator.
if [ -n "${SECUREAPPROVE_BOOTSTRAP_PRIMARY_EMAIL:-}" ]; then
  echo "[*] Setting up configured primary WebAuthn administrator..."
  python manage.py shell << 'EOF'
import os
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant

User = get_user_model()
email = os.environ['SECUREAPPROVE_BOOTSTRAP_PRIMARY_EMAIL'].strip().lower()

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
else
  echo "[*] Primary WebAuthn administrator bootstrap disabled"
fi

echo "[*] Initialization complete!"
echo "[*] Access the application at: http://localhost:8005"

# Start the application
exec "$@"
