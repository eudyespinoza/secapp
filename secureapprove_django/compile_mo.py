#!/usr/bin/env python
"""
Compilador manual de archivos .po a .mo sin usar gettext
Basado en la estructura del formato .mo de GNU gettext
"""
import struct
import array
import os

def generate_mo_file(po_file, mo_file):
    """Convierte archivo .po a .mo"""
    
    # Leer archivo .po
    with open(po_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Parsear entradas
    entries = {}
    current_msgid = None
    current_msgstr = None
    in_msgid = False
    in_msgstr = False
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('msgid "'):
            if current_msgid and current_msgstr:
                entries[current_msgid] = current_msgstr
            current_msgid = line[7:-1]  # Remover 'msgid "' y '"'
            in_msgid = True
            in_msgstr = False
            current_msgstr = None
            
        elif line.startswith('msgstr "'):
            current_msgstr = line[8:-1]  # Remover 'msgstr "' y '"'
            in_msgid = False
            in_msgstr = True
            
        elif line.startswith('"') and line.endswith('"'):
            # Continuación de línea
            text = line[1:-1]
            if in_msgid and current_msgid is not None:
                current_msgid += text
            elif in_msgstr and current_msgstr is not None:
                current_msgstr += text
    
    # Agregar última entrada
    if current_msgid and current_msgstr:
        entries[current_msgid] = current_msgstr
    
    # Remover entrada vacía
    if '' in entries:
        del entries['']
    
    print(f"📝 Encontradas {len(entries)} traducciones")
    
    # Crear archivo .mo
    keys = sorted(entries.keys())
    offsets = []
    ids = b''
    strs = b''
    
    for key in keys:
        # Agregar msgid
        offsets.append((len(ids), len(key.encode('utf-8')), 
                       len(strs), len(entries[key].encode('utf-8'))))
        ids += key.encode('utf-8') + b'\x00'
        strs += entries[key].encode('utf-8') + b'\x00'
    
    # Crear header .mo
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)
    
    # Magic number, version, número de entradas
    output = struct.pack('Iiiiiii',
                        0x950412de,      # Magic number
                        0,                # Version
                        len(keys),        # Número de entradas
                        7 * 4,            # Offset de tabla de IDs
                        7 * 4 + 8 * len(keys), # Offset de tabla de strings
                        0,                # Hash table size
                        0)                # Hash table offset
    
    # Tabla de offsets para IDs
    for o1, l1, o2, l2 in offsets:
        output += struct.pack('ii', l1, o1 + keystart)
    
    # Tabla de offsets para strings
    for o1, l1, o2, l2 in offsets:
        output += struct.pack('ii', l2, o2 + valuestart)
    
    # Datos
    output += ids + strs
    
    # Escribir archivo .mo
    with open(mo_file, 'wb') as f:
        f.write(output)
    
    print(f"✅ Archivo .mo creado: {mo_file}")

# Procesar archivos
locale_dir = os.path.dirname(__file__)

for lang in ['es', 'en', 'pt_BR']:
    po_file = os.path.join(locale_dir, 'locale', lang, 'LC_MESSAGES', 'django.po')
    mo_file = os.path.join(locale_dir, 'locale', lang, 'LC_MESSAGES', 'django.mo')
    
    if os.path.exists(po_file):
        print(f"\n🌍 Compilando {lang}...")
        try:
            generate_mo_file(po_file, mo_file)
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"⚠️  No encontrado: {po_file}")

print("\n🎉 ¡Compilación completada!")
