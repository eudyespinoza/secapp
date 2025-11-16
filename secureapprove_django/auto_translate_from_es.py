#!/usr/bin/env python3
"""
Script para copiar traducciones del español y auto-traducir lo restante
Usa el archivo ES como base para llenar PT
"""

import re
from pathlib import Path

# Traducciones automáticas ES → PT (reglas simples)
AUTO_TRANSLATE_RULES = {
    # Terminaciones comunes
    'ción': 'ção',
    'ciones': 'ções',
    'mente': 'mente',
    'dad': 'dade',
    
    # Palabras completas
    ' y ': ' e ',
    ' o ': ' ou ',
    ' para ': ' para ',
    ' con ': ' com ',
    ' sin ': ' sem ',
    ' en ': ' em ',
    ' de ': ' de ',
    ' del ': ' do ',
    ' la ': ' a ',
    ' el ': ' o ',
    ' los ': ' os ',
    ' las ': ' as ',
    ' un ': ' um ',
    ' una ': ' uma ',
    ' tu ': ' seu ',
    ' tus ': ' seus ',
    ' su ': ' seu ',
    ' sus ': ' seus ',
    ' que ': ' que ',
    ' por ': ' por ',
    ' más ': ' mais ',
    
    # Palabras iniciales
    'Configuración': 'Configuração',
    'Información': 'Informação',
    'Notificación': 'Notificação',
    'Autenticación': 'Autenticação',
    'Autorización': 'Autorização',
    'Verificación': 'Verificação',
    'Creación': 'Criação',
    'Edición': 'Edição',
    'Eliminación': 'Eliminação',
    'Actualización': 'Atualização',
    'Gestión': 'Gestão',
    'Administración': 'Administração',
}

def simple_es_to_pt(text):
    """Aplica reglas simples de traducción ES → PT"""
    result = text
    for es, pt in AUTO_TRANSLATE_RULES.items():
        result = result.replace(es, pt)
    return result

def extract_translations_from_es(po_file_path):
    """Extrae todas las traducciones del archivo ES"""
    with open(po_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    translations = {}
    
    # Buscar todos los pares msgid/msgstr
    pattern = r'msgid "([^"]*)"\nmsgstr "([^"]*)"'
    matches = re.findall(pattern, content, re.MULTILINE)
    
    for msgid, msgstr in matches:
        if msgid and msgid != msgstr:  # Solo si hay traducción real
            translations[msgid] = msgstr
    
    return translations

def fill_empty_translations(po_pt_path, po_es_path):
    """Llena las traducciones vacías del PT usando ES como base"""
    
    print(f"\n{'='*60}")
    print(f"LLENANDO TRADUCCIONES VACÍAS")
    print(f"{'='*60}\n")
    
    # Leer traducciones del español
    print("1. Extrayendo traducciones del archivo ES...")
    es_translations = extract_translations_from_es(po_es_path)
    print(f"   ✓ {len(es_translations)} traducciones encontradas en ES\n")
    
    # Leer archivo PT
    with open(po_pt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    empty_before = content.count('msgstr ""')
    translated_count = 0
    auto_translated_count = 0
    
    # Buscar todos los msgid con msgstr vacío
    print("2. Llenando traducciones vacías...")
    pattern = r'msgid "([^"]*)"\nmsgstr ""'
    
    def replace_empty(match):
        nonlocal translated_count, auto_translated_count
        msgid = match.group(1)
        
        if not msgid:  # Header vacío
            return match.group(0)
        
        # Si existe traducción en ES, usarla como base
        if msgid in es_translations:
            es_text = es_translations[msgid]
            # Auto-traducir de ES a PT
            pt_text = simple_es_to_pt(es_text)
            translated_count += 1
            if translated_count <= 10:  # Mostrar primeros 10
                print(f"   ✓ {msgid[:40]}")
                print(f"     ES: {es_text[:40]}")
                print(f"     PT: {pt_text[:40]}\n")
            return f'msgid "{msgid}"\nmsgstr "{pt_text}"'
        else:
            # Si no hay en ES, intentar auto-traducir el msgid mismo
            pt_text = simple_es_to_pt(msgid)
            if pt_text != msgid:  # Solo si cambió algo
                auto_translated_count += 1
                return f'msgid "{msgid}"\nmsgstr "{pt_text}"'
            else:
                return match.group(0)  # Dejar vacío
    
    content = re.sub(pattern, replace_empty, content)
    
    # Guardar archivo modificado
    with open(po_pt_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    empty_after = content.count('msgstr ""')
    
    print(f"\n{'='*60}")
    print(f"RESUMEN:")
    print(f"  - Traducciones desde ES: {translated_count}")
    print(f"  - Auto-traducciones: {auto_translated_count}")
    print(f"  - Total procesadas: {translated_count + auto_translated_count}")
    print(f"  - msgstr vacíos antes: {empty_before}")
    print(f"  - msgstr vacíos después: {empty_after}")
    print(f"  - msgstr vacíos eliminados: {empty_before - empty_after}")
    print(f"{'='*60}\n")

def main():
    locale_dir = Path(__file__).parent / 'locale'
    
    po_pt = locale_dir / 'pt_BR' / 'LC_MESSAGES' / 'django.po'
    po_es = locale_dir / 'es' / 'LC_MESSAGES' / 'django.po'
    
    if not po_es.exists():
        print(f"✗ No se encontró: {po_es}")
        return
    
    if not po_pt.exists():
        print(f"✗ No se encontró: {po_pt}")
        return
    
    fill_empty_translations(po_pt, po_es)
    
    print("✓ Proceso completado")
    print("  Ahora ejecuta:")
    print("  1. python manage.py compilemessages")
    print("  2. docker compose restart web")

if __name__ == '__main__':
    main()
