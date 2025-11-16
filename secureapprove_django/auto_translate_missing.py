#!/usr/bin/env python3
"""
Rellena automáticamente traducciones faltantes en los archivos .po
para es, en y pt_BR usando googletrans.

Estrategia:
- Tomamos el archivo en/LC_MESSAGES/django.po como referencia de todos los msgid.
- Para cada msgid:
    - en: msgstr = msgid si está vacío.
    - es: si no existe entrada o msgstr está vacío, traducimos a español.
    - pt_BR: si no existe entrada o msgstr está vacío, traducimos a portugués.

Después de ejecutar este script, hay que recompilar los .mo:
    python secureapprove_django/compile_mo.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import polib
from googletrans import Translator


BASE_DIR = Path(__file__).resolve().parent
LOCALE_DIR = BASE_DIR / "locale"


def ensure_po(lang_dir: Path) -> polib.POFile | None:
    po_path = lang_dir / "LC_MESSAGES" / "django.po"
    if not po_path.exists():
        print(f"[SKIP] No se encontró {po_path}")
        return None
    return polib.pofile(str(po_path))


def main() -> None:
    en_dir = LOCALE_DIR / "en"
    es_dir = LOCALE_DIR / "es"
    pt_dir = LOCALE_DIR / "pt_BR"

    en_po = ensure_po(en_dir)
    es_po = ensure_po(es_dir)
    pt_po = ensure_po(pt_dir)

    if not en_po or not es_po or not pt_po:
        return

    # Índices rápidos por msgid
    es_index: Dict[str, polib.POEntry] = {e.msgid: e for e in es_po if e.msgid}
    pt_index: Dict[str, polib.POEntry] = {e.msgid: e for e in pt_po if e.msgid}

    translator = Translator()

    def translate_text(text: str, dest: str) -> str:
        # Evitar traducir cadenas triviales (un solo símbolo, etc.)
        stripped = text.strip()
        if not stripped:
            return text
        try:
            result = translator.translate(text, dest=dest)
            return result.text
        except Exception as exc:  # pragma: no cover - red de terceros
            print(f"[WARN] Error traduciendo '{text[:40]}...' a {dest}: {exc}")
            return text

    changed_en = changed_es = changed_pt = 0

    for entry in en_po:
        if entry.obsolete or not entry.msgid:
            continue

        msgid = entry.msgid

        # 1) Inglés: si msgstr vacío, poner msgid
        if not entry.msgstr:
            entry.msgstr = msgid
            changed_en += 1

        # 2) Español
        es_entry = es_index.get(msgid)
        if es_entry is None:
            es_entry = polib.POEntry(msgid=msgid, msgstr="")
            es_po.append(es_entry)
            es_index[msgid] = es_entry

        if not es_entry.msgstr:
            es_entry.msgstr = translate_text(msgid, dest="es")
            changed_es += 1

        # 3) Portugués (Brasil)
        pt_entry = pt_index.get(msgid)
        if pt_entry is None:
            pt_entry = polib.POEntry(msgid=msgid, msgstr="")
            pt_po.append(pt_entry)
            pt_index[msgid] = pt_entry

        if not pt_entry.msgstr:
            pt_entry.msgstr = translate_text(msgid, dest="pt")
            changed_pt += 1

    # Guardar archivos modificados
    en_po.save()
    es_po.save()
    pt_po.save()

    print(f"[EN] Traducciones nuevas/ajustadas: {changed_en}")
    print(f"[ES] Traducciones nuevas/ajustadas: {changed_es}")
    print(f"[PT-BR] Traducciones nuevas/ajustadas: {changed_pt}")


if __name__ == "__main__":
    main()

