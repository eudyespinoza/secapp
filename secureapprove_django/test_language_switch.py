#!/usr/bin/env python
"""
Test directo del cambio de idioma simulando una petición HTTP
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware.locale import LocaleMiddleware
from django.utils.translation import get_language, activate
from django.conf import settings

print("="*70)
print("🧪 TEST DE CAMBIO DE IDIOMA")
print("="*70)

# Crear un cliente de prueba
client = Client()

print("\n1️⃣ Estado inicial:")
print(f"   LANGUAGE_CODE por defecto: {settings.LANGUAGE_CODE}")
print(f"   LANGUAGES disponibles: {settings.LANGUAGES}")

print("\n2️⃣ Probando cambio a inglés (en):")
response = client.post('/i18n/setlang/', {
    'language': 'en',
    'next': '/es/'
})
print(f"   Status: {response.status_code}")
print(f"   Location: {response.get('Location', 'N/A')}")
print(f"   Cookies: {response.cookies}")
if 'django_language' in response.cookies:
    print(f"   Cookie django_language: {response.cookies['django_language'].value}")

print("\n3️⃣ Probando cambio a portugués (pt-br):")
response = client.post('/i18n/setlang/', {
    'language': 'pt-br',
    'next': '/es/'
})
print(f"   Status: {response.status_code}")
print(f"   Location: {response.get('Location', 'N/A')}")
if 'django_language' in response.cookies:
    print(f"   Cookie django_language: {response.cookies['django_language'].value}")

print("\n4️⃣ Verificando activación manual:")
for lang_code, lang_name in settings.LANGUAGES:
    activate(lang_code)
    current = get_language()
    print(f"   {lang_code} → get_language(): {current}")

print(f"\n{'='*70}")
print("✅ Test completado")
print(f"{'='*70}")
