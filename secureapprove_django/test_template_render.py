#!/usr/bin/env python
"""
Test de renderizado real de templates con diferentes idiomas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.utils.translation import activate
from django.template.loader import render_to_string
from django.template import Context, Template

print("="*70)
print("🧪 TEST DE RENDERIZADO DE TEMPLATES CON I18N")
print("="*70)

# Test simple con template string
template_string = """
{% load i18n %}
<h1>{% trans "Dashboard" %}</h1>
<p>{% trans "Welcome back" %}</p>
<p>{% trans "Requests" %}</p>
"""

for lang_code, lang_name in [('es', 'Español'), ('en', 'English'), ('pt-br', 'Português')]:
    print(f"\n{'='*70}")
    print(f"🌍 Renderizando en: {lang_name} ({lang_code})")
    print(f"{'='*70}")
    
    activate(lang_code)
    template = Template(template_string)
    context = Context({})
    rendered = template.render(context)
    
    print(rendered.strip())

print(f"\n{'='*70}")
print("✅ Test de renderizado completado")
print(f"{'='*70}")
