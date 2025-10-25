#!/usr/bin/env python
"""
Script para compilar traducciones sin usar gettext tools
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command

print("🌍 Compilando traducciones...")

try:
    # Intentar compilar mensajes
    call_command('compilemessages', verbosity=2)
    print("✅ Traducciones compiladas exitosamente")
except Exception as e:
    print(f"❌ Error al compilar: {e}")
    print("\n⚠️  Necesitas instalar gettext tools:")
    print("   Windows: https://mlocati.github.io/articles/gettext-iconv-windows.html")
    print("   O instalar via: choco install gettext")
    sys.exit(1)
