#!/usr/bin/env python3
"""Test para verificar traducciones en portugués"""

import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils.translation import gettext
from django.utils import translation

translation.activate('pt-br')

# Textos a verificar
texts = [
    "Planes de Suscripción",
    "Ver Demo",
    "Automatiza tus procesos de aprobación con seguridad de nivel empresarial y autenticación biométrica avanzada.",
    "Sistema de Aprovações Seguras",
    "Características",
    "Preços",
    "Contato",
]

print("\n" + "="*60)
print("TEST DE TRADUCCIONES AL PORTUGUÉS (pt-br)")
print("="*60 + "\n")

for text in texts:
    translated = gettext(text)
    status = "✓" if translated != text else "✗"
    print(f"{status} {text[:40]}...")
    print(f"  → {translated[:60]}...\n")
