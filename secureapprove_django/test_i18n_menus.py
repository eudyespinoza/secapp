#!/usr/bin/env python
"""
Script para verificar que todas las traducciones funcionan correctamente
en todos los menús de la aplicación.
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils.translation import activate, gettext as _
from django.conf import settings


def test_menu_translations():
    """Prueba las traducciones en todos los idiomas configurados."""
    
    print("=" * 70)
    print("VERIFICACIÓN DE TRADUCCIONES EN MENÚS")
    print("=" * 70)
    
    # Términos comunes de menús que deben estar traducidos
    menu_terms = [
        "Dashboard",
        "Requests",
        "New Request",
        "All Requests",
        "My Requests",
        "Pending",
        "Approved",
        "Rejected",
        "Profile",
        "Login",
        "Logout",
        "Register",
        "Settings",
        "Billing",
        "Choose Your Plan",
        "Administration",
        "Cerrar Sesión",
        "Perfil",
        "Solicitudes",
        "Iniciar Sesión",
        "Registrarse",
    ]
    
    for lang_code, lang_name in settings.LANGUAGES:
        print(f"\n{'='*70}")
        print(f"Idioma: {lang_name} ({lang_code})")
        print(f"{'='*70}")
        
        # Activar el idioma
        activate(lang_code)
        
        # Probar traducciones
        for term in menu_terms:
            translated = _(term)
            status = "✓" if translated != term or lang_code == 'en' else "✗"
            print(f"{status} {term:30} → {translated}")
        
        print(f"\nIdioma activo confirmado: {django.utils.translation.get_language()}")


def test_language_switcher():
    """Verifica que el selector de idiomas tenga la configuración correcta."""
    
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DEL SELECTOR DE IDIOMAS")
    print("=" * 70)
    
    print(f"\nIdioma por defecto: {settings.LANGUAGE_CODE}")
    print(f"Idiomas disponibles: {len(settings.LANGUAGES)}")
    
    for lang_code, lang_name in settings.LANGUAGES:
        flag = ""
        if lang_code == 'es':
            flag = "🇪🇸"
        elif lang_code == 'en':
            flag = "🇺🇸"
        elif lang_code == 'pt-br':
            flag = "🇧🇷"
        
        print(f"  {flag} {lang_code:6} - {lang_name}")
    
    print(f"\nMiddleware de localización: {'django.middleware.locale.LocaleMiddleware' in settings.MIDDLEWARE}")
    print(f"Procesador de contexto i18n: {'django.template.context_processors.i18n' in str(settings.TEMPLATES)}")
    print(f"USE_I18N: {settings.USE_I18N}")
    print(f"Rutas de locale: {settings.LOCALE_PATHS}")


def check_translation_files():
    """Verifica que existan los archivos de traducción compilados."""
    
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE ARCHIVOS DE TRADUCCIÓN")
    print("=" * 70)
    
    locale_path = settings.LOCALE_PATHS[0]
    
    for lang_code, lang_name in settings.LANGUAGES:
        # Convertir pt-br a pt_BR
        locale_dir = lang_code.replace('-', '_')
        
        po_file = locale_path / locale_dir / 'LC_MESSAGES' / 'django.po'
        mo_file = locale_path / locale_dir / 'LC_MESSAGES' / 'django.mo'
        
        print(f"\n{lang_name} ({lang_code}):")
        print(f"  .po file: {po_file.exists()} - {po_file}")
        print(f"  .mo file: {mo_file.exists()} - {mo_file}")
        
        if po_file.exists():
            # Contar mensajes
            with open(po_file, 'r', encoding='utf-8') as f:
                content = f.read()
                msgid_count = content.count('msgid "') - 1  # -1 para header
                msgstr_count = content.count('msgstr "') - 1
                
            print(f"  Mensajes: ~{msgid_count} definidos")
        
        if not mo_file.exists():
            print(f"  ⚠️  ADVERTENCIA: Archivo .mo no encontrado. Ejecutar: python manage.py compilemessages")


def main():
    """Ejecuta todas las verificaciones."""
    try:
        test_language_switcher()
        check_translation_files()
        test_menu_translations()
        
        print("\n" + "=" * 70)
        print("✓ VERIFICACIÓN COMPLETADA")
        print("=" * 70)
        print("\nPara probar el cambio de idioma en la aplicación:")
        print("1. Abrir http://localhost:8000")
        print("2. Usar el selector de idioma en el menú superior")
        print("3. Verificar que todos los menús cambien correctamente")
        print("\nPara recompilar traducciones:")
        print("docker-compose exec web python manage.py compilemessages")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
