#!/usr/bin/env python
"""
Script para verificar archivos de traducción sin cargar Django
"""
import os

print("="*60)
print("🌍 Verificación de Archivos de Traducción - SecureApprove")
print("="*60)

# Directorio base
locale_dir = os.path.join(os.path.dirname(__file__), 'locale')

languages = [
    ('es', 'Español'),
    ('en', 'English'),
    ('pt_BR', 'Português (Brasil)'),
]

print(f"\n📁 Directorio de traducciones: {locale_dir}")
print(f"   Existe: {'✅' if os.path.exists(locale_dir) else '❌'}")

for lang_code, lang_name in languages:
    print(f"\n{'='*60}")
    print(f"📌 Idioma: {lang_name} ({lang_code})")
    print(f"{'='*60}")
    
    lang_dir = os.path.join(locale_dir, lang_code, 'LC_MESSAGES')
    po_file = os.path.join(lang_dir, 'django.po')
    mo_file = os.path.join(lang_dir, 'django.mo')
    
    # Check directory
    dir_exists = os.path.exists(lang_dir)
    print(f"📂 Directorio: {'✅' if dir_exists else '❌'} {lang_dir}")
    
    # Check .po file
    po_exists = os.path.exists(po_file)
    print(f"\n📝 Archivo .po: {'✅' if po_exists else '❌'}")
    if po_exists:
        po_size = os.path.getsize(po_file)
        print(f"   Ruta: {po_file}")
        print(f"   Tamaño: {po_size} bytes")
        
        # Check if fuzzy
        with open(po_file, 'r', encoding='utf-8') as f:
            content = f.read()
            has_fuzzy = '#, fuzzy' in content
            print(f"   Marcador 'fuzzy': {'❌ PRESENTE (malo)' if has_fuzzy else '✅ NO PRESENTE (bueno)'}")
            
            # Count translations
            msgid_count = content.count('msgid "') - 1  # -1 for header
            msgstr_count = content.count('msgstr "') - 1
            print(f"   Cadenas msgid: {msgid_count}")
            print(f"   Cadenas msgstr: {msgstr_count}")
    
    # Check .mo file
    mo_exists = os.path.exists(mo_file)
    print(f"\n⚙️  Archivo .mo: {'✅' if mo_exists else '❌ NO ENCONTRADO - Necesita compilación'}")
    if mo_exists:
        mo_size = os.path.getsize(mo_file)
        print(f"   Ruta: {mo_file}")
        print(f"   Tamaño: {mo_size} bytes")
        
        # Verify .mo file is newer than .po
        if po_exists:
            po_mtime = os.path.getmtime(po_file)
            mo_mtime = os.path.getmtime(mo_file)
            if mo_mtime >= po_mtime:
                print(f"   Estado: ✅ Actualizado (más reciente que .po)")
            else:
                print(f"   Estado: ⚠️  Desactualizado (más antiguo que .po)")

print("\n" + "="*60)
print("✅ Verificación de archivos completada")
print("="*60)

# Summary
print("\n� RESUMEN:")
print("-" * 60)
all_ok = True
for lang_code, lang_name in languages:
    po_file = os.path.join(locale_dir, lang_code, 'LC_MESSAGES', 'django.po')
    mo_file = os.path.join(locale_dir, lang_code, 'LC_MESSAGES', 'django.mo')
    
    po_ok = os.path.exists(po_file)
    mo_ok = os.path.exists(mo_file)
    
    if po_ok:
        with open(po_file, 'r', encoding='utf-8') as f:
            fuzzy_ok = '#, fuzzy' not in f.read()
    else:
        fuzzy_ok = False
    
    status = "✅" if (po_ok and mo_ok and fuzzy_ok) else "❌"
    all_ok = all_ok and po_ok and mo_ok and fuzzy_ok
    
    print(f"{status} {lang_name}: .po={'✅' if po_ok else '❌'} .mo={'✅' if mo_ok else '❌'} sin-fuzzy={'✅' if fuzzy_ok else '❌'}")

if all_ok:
    print("\n✅ ¡Todos los archivos de traducción están correctos!")
else:
    print("\n⚠️  Algunos archivos necesitan atención")

print("\n💡 NOTA: Si hiciste cambios, reinicia el servidor Django para aplicarlos.")
