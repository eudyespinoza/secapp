#!/usr/bin/env python3
"""
Script para identificar traducciones faltantes o incorrectas en django.po

Este script:
  1) Verifica que ciertos textos clave tengan msgid/msgstr en el .po
  2) Informa si la traducción está vacía, sin traducir o correcta
  3) Lista un resumen de msgstr vacíos (primeros 10) y el total
"""

from pathlib import Path
import re


def check_translations(po_file_path: Path, target_texts):
    """Verifica si los textos específicos tienen traducción."""
    with po_file_path.open("r", encoding="utf-8") as f:
        content = f.read()

    print("\n" + "=" * 60)
    print(f"VERIFICANDO: {po_file_path}")
    print("=" * 60 + "\n")

    for text in target_texts:
        escaped_text = re.escape(text)
        pattern = rf'msgid "{escaped_text}"\nmsgstr "([^"]*)"'
        match = re.search(pattern, content, re.MULTILINE)

        if match:
            translation = match.group(1)
            if not translation:
                print(f"[EMPTY]       {text[:40]}")
            elif translation == text:
                print(f"[UNTRANSLATED] {text[:40]}")
                print(f'  msgstr = "{translation}"')
            else:
                print(f"[OK]          {text[:40]}")
                print(f"  -> {translation}")
        else:
            print(f"[NOT FOUND]   {text[:40]}")
        print()


def main():
    locale_dir = Path(__file__).parent / "locale"

    # Textos que deben estar traducidos
    target_texts = [
        "Ver Demo",
        "Planes de Suscripción",
        "Características",
        "Preços",  # Ya en portugués
        "Contato",  # Ya en portugués
        "Sistema de Aprovações Seguras",  # Ya en portugués
        "Automatiza tus procesos de aprobación con seguridad de nivel "
        "empresarial y autenticación biométrica avanzada.",
    ]

    po_pt = locale_dir / "pt_BR" / "LC_MESSAGES" / "django.po"
    if not po_pt.exists():
        print(f"No se encontró el archivo: {po_pt}")
        return

    check_translations(po_pt, target_texts)

    print("\n" + "=" * 60)
    print("Buscando msgstr vacíos...")
    print("=" * 60 + "\n")

    with po_pt.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    empty_count = 0
    shown = 0

    for i, line in enumerate(lines):
        if line.strip() == 'msgstr ""' and i > 0:
            prev_line = lines[i - 1].strip()
            if prev_line.startswith('msgid "'):
                msgid = prev_line[7:-1]  # texto entre comillas
                if msgid:
                    empty_count += 1
                    if shown < 10:
                        shown += 1
                        print(f"{shown}. {msgid[:80]}")

    print(f"\nTotal de msgstr vacíos: {empty_count}")


if __name__ == "__main__":
    main()

