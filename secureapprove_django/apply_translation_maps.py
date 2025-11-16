#!/usr/bin/env python3
"""
Aplica los diccionarios de traducciones existentes a los archivos .po
usando polib (maneja correctamente entradas multilínea).

Fuentes:
  - fix_all_translations.all_translations_en / all_translations_pt
  - translate_empty_entries.TRANSLATIONS (PT-BR)
  - fix_translations_pt.translations_pt (PT-BR)

Uso:
  python secureapprove_django/apply_translation_maps.py

Después de ejecutar, volver a compilar los .mo:
  python secureapprove_django/compile_mo.py
  (o `python manage.py compilemessages` dentro del proyecto Django)
"""

from pathlib import Path
import sys

import polib

# Asegurar que podamos importar los diccionarios definidos en la raíz
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fix_all_translations import all_translations_en, all_translations_pt  # type: ignore
from fix_translations_pt import translations_pt  # type: ignore
from translate_empty_entries import TRANSLATIONS as pt_extra_translations  # type: ignore


def apply_map(po_path: Path, translations_map: dict, label: str) -> int:
    po = polib.pofile(str(po_path))
    changed = 0

    for entry in po:
        if entry.obsolete or not entry.msgid:
            continue

        # No sobrescribir traducciones que ya existen
        if entry.msgstr:
            continue

        new_value = translations_map.get(entry.msgid)
        if new_value:
            entry.msgstr = new_value
            changed += 1

    if changed:
        po.save()

    print(f"{label}: {changed} traducciones agregadas en {po_path}")
    return changed


def main():
    locale_dir = Path(__file__).parent / "locale"

    # Inglés (en): traducir desde español a inglés donde falte
    en_po = locale_dir / "en" / "LC_MESSAGES" / "django.po"
    if en_po.exists():
        apply_map(en_po, all_translations_en, "EN")
    else:
        print(f"EN: no se encontró {en_po}")

    # Portugués brasileño (pt_BR)
    pt_po = locale_dir / "pt_BR" / "LC_MESSAGES" / "django.po"
    if pt_po.exists():
        # Unir todos los mapas conocidos para PT-BR
        pt_map: dict = {}
        pt_map.update(all_translations_pt)
        pt_map.update(translations_pt)
        pt_map.update(pt_extra_translations)

        apply_map(pt_po, pt_map, "PT-BR")
    else:
        print(f"PT-BR: no se encontró {pt_po}")


if __name__ == "__main__":
    main()

