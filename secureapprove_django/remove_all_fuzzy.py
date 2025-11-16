#!/usr/bin/env python3
"""Script para eliminar TODAS las marcas fuzzy de los archivos .po"""

import re
from pathlib import Path

def remove_fuzzy_marks(po_file_path):
    """Elimina todas las líneas que contengan '#, fuzzy' del archivo .po"""
    
    print(f"\n{'='*60}")
    print(f"Procesando: {po_file_path}")
    print(f"{'='*60}")
    
    with open(po_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Contar líneas fuzzy
    fuzzy_count = sum(1 for line in lines if line.strip() == '#, fuzzy')
    print(f"Líneas fuzzy encontradas: {fuzzy_count}")
    
    if fuzzy_count == 0:
        print("✓ No hay marcas fuzzy en este archivo")
        return
    
    # Eliminar líneas fuzzy
    cleaned_lines = [line for line in lines if line.strip() != '#, fuzzy']
    
    # Escribir archivo limpio
    with open(po_file_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    
    print(f"✓ {fuzzy_count} marcas fuzzy eliminadas")

def main():
    # Procesar todos los archivos .po
    locale_dir = Path(__file__).parent / 'locale'
    
    po_files = [
        locale_dir / 'en' / 'LC_MESSAGES' / 'django.po',
        locale_dir / 'es' / 'LC_MESSAGES' / 'django.po',
        locale_dir / 'pt_BR' / 'LC_MESSAGES' / 'django.po',
    ]
    
    for po_file in po_files:
        if po_file.exists():
            remove_fuzzy_marks(po_file)
        else:
            print(f"⚠ Archivo no encontrado: {po_file}")
    
    print(f"\n{'='*60}")
    print("TODAS LAS MARCAS FUZZY HAN SIDO ELIMINADAS")
    print("Ahora ejecuta: python manage.py compilemessages")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
