#!/usr/bin/env python
"""
Script to migrate existing WebAuthn credentials to include is_active field
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.authentication.models import User

def migrate_credentials():
    """Add is_active field to all existing credentials"""
    users_updated = 0
    credentials_updated = 0
    
    for user in User.objects.all():
        if user.webauthn_credentials:
            updated = False
            for cred in user.webauthn_credentials:
                if 'is_active' not in cred:
                    cred['is_active'] = True
                    credentials_updated += 1
                    updated = True
                    
                # Also add other missing fields
                if 'display_name' not in cred:
                    cred['display_name'] = f"Device {credentials_updated}"
                    
                if 'last_used_at' not in cred:
                    cred['last_used_at'] = None
            
            if updated:
                user.save(update_fields=['webauthn_credentials'])
                users_updated += 1
                print(f"✓ Updated {len(user.webauthn_credentials)} credentials for user: {user.email}")
    
    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"Users updated: {users_updated}")
    print(f"Credentials updated: {credentials_updated}")
    print(f"{'='*60}")

if __name__ == '__main__':
    migrate_credentials()
