#!/usr/bin/env python3
"""
Reporte rápido de traducciones faltantes por idioma.

Usa polib para analizar los archivos:
    secureapprove_django/locale/<lang>/LC_MESSAGES/django.po

Muestra:
  - Total de entradas
  - Cuántas tienen msgstr vacío
  - Cuántas tienen msgid == msgstr (posible sin traducir)
  - Un pequeño listado de ejemplo para cada caso
"""

from pathlib import Path

import polib


def analyze_po(po: polib.POFile, po_path: Path, max_examples: int = 15):

    total = 0
    empty = []
    same = []

    for entry in po:
        if entry.obsolete or not entry.msgid:
            continue

        total += 1

        if not entry.msgstr:
            empty.append(entry)
        elif entry.msgstr == entry.msgid:
            same.append(entry)

    print("-" * 72)
    print(f"Archivo: {po_path}")
    print(f"Total entradas útiles: {total}")
    print(f"msgstr vacíos        : {len(empty)}")
    print(f"msgid == msgstr      : {len(same)}")

    def show_examples(label, items):
        if not items:
            return
        print(f"\nEjemplos de {label} (máx {max_examples}):")
        for e in items[:max_examples]:
            # Truncar para que sea legible en consola
            src = e.msgid.replace("\n", " ")[:80]
            dst = e.msgstr.replace("\n", " ")[:80] if e.msgstr else ""
            print(f"  - msgid : {src!r}")
            if dst:
                print(f"    msgstr: {dst!r}")

    show_examples("msgstr vacíos", empty)
    show_examples("msgid == msgstr", same)
    print()


def main():
    base_locale = Path(__file__).parent / "locale"
    if not base_locale.exists():
        print(f"No se encontró el directorio de locales: {base_locale}")
        return

    print(f"Analizando traducciones en: {base_locale}")

    # Cargar todos los .po primero
    pos: dict[str, polib.POFile] = {}
    po_paths: dict[str, Path] = {}

    for lang_dir in sorted(base_locale.iterdir(), key=lambda p: p.name.lower()):
        if not lang_dir.is_dir():
            continue

        po_path = lang_dir / "LC_MESSAGES" / "django.po"
        if not po_path.exists():
            continue

        lang_code = lang_dir.name
        po_obj = polib.pofile(str(po_path))
        pos[lang_code] = po_obj
        po_paths[lang_code] = po_path

        analyze_po(po_obj, po_path)

    # Verificar msgid que existen en un idioma pero faltan en otros
    if not pos:
        return

    all_msgids = set()
    lang_msgids: dict[str, set[str]] = {}

    for lang_code, po in pos.items():
        ids = {e.msgid for e in po if not e.obsolete and e.msgid}
        lang_msgids[lang_code] = ids
        all_msgids.update(ids)

    print("-" * 72)
    print("Cobertura cruzada de msgid entre idiomas")

    for lang_code in sorted(lang_msgids.keys()):
        missing = sorted(all_msgids - lang_msgids[lang_code])
        if not missing:
            print(f"[OK]  {lang_code}: sin msgid faltantes respecto a los demás idiomas.")
            continue

        print(f"[WARN] {lang_code}: {len(missing)} msgid presentes en otros idiomas pero no en {lang_code}")
        for msgid in missing[:15]:
            preview = msgid.replace("\n", " ")[:80]
            print(f"   - {preview!r}")
        if len(missing) > 15:
            print(f"   ... ({len(missing) - 15} adicionales)")


if __name__ == "__main__":
    main()
