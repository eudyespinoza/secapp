#!/usr/bin/env python
"""
Compilación sencilla de archivos .po a .mo usando polib.

Evita depender de herramientas externas de gettext y maneja correctamente
entradas multilínea y encabezados.

Idiomas soportados (directorio estándar de Django):
  secureapprove_django/locale/<lang>/LC_MESSAGES/django.po

Uso:
  python secureapprove_django/compile_mo.py
"""

from pathlib import Path

import polib


def compile_language(base_locale: Path, lang_code: str) -> None:
    po_path = base_locale / lang_code / "LC_MESSAGES" / "django.po"
    mo_path = base_locale / lang_code / "LC_MESSAGES" / "django.mo"

    if not po_path.exists():
        print(f"[SKIP] No se encontró: {po_path}")
        return

    po = polib.pofile(str(po_path))
    po.save_as_mofile(str(mo_path))
    print(f"[OK]   Compilado {po_path} -> {mo_path}")


def main() -> None:
    project_root = Path(__file__).resolve().parent
    base_locale = project_root / "locale"

    if not base_locale.exists():
        print(f"No se encontró el directorio de locales: {base_locale}")
        return

    print(f"Compilando archivos .po en: {base_locale}")

    # Idiomas que usamos en el proyecto
    for lang in ("es", "en", "pt_BR"):
        compile_language(base_locale, lang)

    print("Compilación de mensajes completada.")


if __name__ == "__main__":
    main()

