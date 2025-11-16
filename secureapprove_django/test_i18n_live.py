#!/usr/bin/env python
"""
Test i18n live - verifica traducciones en el servidor corriendo
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils.translation import activate, gettext
from django.conf import settings

print("="*70)
print("🧪 TEST DE TRADUCCIONES EN VIVO")
print("="*70)

test_strings = [
    "Dashboard",
    "Welcome back",
    "Requests",
    "New Request",
    "Pending",
    "Approved",
]

print(f"\n📋 Configuración:")
print(f"   LANGUAGE_CODE: {settings.LANGUAGE_CODE}")
print(f"   LANGUAGES: {settings.LANGUAGES}")
print(f"   USE_I18N: {settings.USE_I18N}")
print(f"   LOCALE_PATHS: {settings.LOCALE_PATHS}")

for lang_code, lang_name in settings.LANGUAGES:
    print(f"\n{'='*70}")
    print(f"🌍 Probando: {lang_name} ({lang_code})")
    print(f"{'='*70}")
    
    activate(lang_code)
    
    for test_str in test_strings:
        translated = gettext(test_str)
        if translated == test_str:
            status = "❌ NO traducido"
        else:
            status = "✅ Traducido"
        print(f"{status:20} '{test_str}' → '{translated}'")

print(f"\n{'='*70}")
print("✅ Test completado")
print(f"{'='*70}")
