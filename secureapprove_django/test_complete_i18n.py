#!/usr/bin/env python
"""
Test COMPLETO del sistema i18n - DEFINITIVO
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from django.utils.translation import activate, gettext as _
from django.template import Context, Template
from django.test import RequestFactory

print("="*80)
print("TEST COMPLETO DEL SISTEMA i18n")
print("="*80)

# 1. VERIFICAR CONFIGURACIÓN
print("\n1. CONFIGURACIÓN DE DJANGO:")
print(f"   LANGUAGE_CODE: {settings.LANGUAGE_CODE}")
print(f"   LANGUAGES: {settings.LANGUAGES}")
print(f"   USE_I18N: {settings.USE_I18N}")
print(f"   LOCALE_PATHS: {settings.LOCALE_PATHS}")

# 2. VERIFICAR ARCHIVOS .mo
print("\n2. ARCHIVOS .mo COMPILADOS:")
for lang_code, lang_name in settings.LANGUAGES:
    locale_code = lang_code.replace('-', '_')
    mo_file = settings.LOCALE_PATHS[0] / locale_code / 'LC_MESSAGES' / 'django.mo'
    exists = mo_file.exists()
    size = mo_file.stat().st_size if exists else 0
    print(f"   {lang_code} ({locale_code}): {'✓' if exists else '✗'} {mo_file} ({size} bytes)")

# 3. PROBAR TRADUCCIONES DIRECTAS
print("\n3. TRADUCCIONES DIRECTAS (función _):")
test_strings = [
    "Dashboard",
    "Welcome back",
    "Requests",
    "New Request",
    "Pending",
    "Approved",
    "Rejected"
]

for lang_code, lang_name in settings.LANGUAGES:
    activate(lang_code)
    print(f"\n   {lang_name} ({lang_code}):")
    for string in test_strings:
        translated = _(string)
        symbol = "✓" if translated != string else "✗"
        print(f"      {symbol} '{string}' → '{translated}'")

# 4. PROBAR TEMPLATE RENDERING
print("\n4. TEMPLATE RENDERING ({% trans %}):")
template_code = """{% load i18n %}
Dashboard: {% trans "Dashboard" %}
Welcome: {% trans "Welcome back" %}
Requests: {% trans "Requests" %}
"""

factory = RequestFactory()
for lang_code, lang_name in settings.LANGUAGES:
    activate(lang_code)
    request = factory.get(f'/{lang_code}/')
    request.LANGUAGE_CODE = lang_code
    
    template = Template(template_code)
    context = Context({'request': request})
    rendered = template.render(context)
    
    print(f"\n   {lang_name} ({lang_code}):")
    for line in rendered.strip().split('\n'):
        if line.strip():
            print(f"      {line.strip()}")

# 5. VERIFICAR MIDDLEWARE
print("\n5. MIDDLEWARE:")
middleware_list = settings.MIDDLEWARE
locale_pos = next((i for i, m in enumerate(middleware_list) if 'LocaleMiddleware' in m), -1)
session_pos = next((i for i, m in enumerate(middleware_list) if 'SessionMiddleware' in m), -1)

if locale_pos > session_pos:
    print(f"   ✓ LocaleMiddleware ({locale_pos}) está DESPUÉS de SessionMiddleware ({session_pos})")
else:
    print(f"   ✗ ERROR: LocaleMiddleware ({locale_pos}) está ANTES de SessionMiddleware ({session_pos})")

# 6. VERIFICAR URLs
print("\n6. URLs i18n:")
from django.urls import resolve, reverse
try:
    set_language_url = reverse('set_language')
    print(f"   ✓ URL 'set_language': {set_language_url}")
except:
    print(f"   ✗ ERROR: URL 'set_language' no encontrada")

print("\n" + "="*80)
print("RESUMEN:")
print("="*80)

# Determinar estado
all_mo_exist = all(
    (settings.LOCALE_PATHS[0] / lang_code.replace('-', '_') / 'LC_MESSAGES' / 'django.mo').exists()
    for lang_code, _ in settings.LANGUAGES
)

if all_mo_exist and locale_pos > session_pos:
    print("✓ Sistema i18n configurado CORRECTAMENTE")
    print("\nSi el selector de idioma NO funciona en el navegador, el problema es:")
    print("  1. Cache del navegador (Ctrl+Shift+R)")
    print("  2. Template usando enlaces <a href> en lugar de <form method='post'>")
    print("  3. JavaScript interfiriendo con el formulario")
else:
    print("✗ Sistema i18n tiene problemas de configuración")

print("="*80)
