"""
Compat module for Python 3.13 where the stdlib `cgi` module
ya no existe, pero algunas dependencias (como httpx usado por
googletrans) todavía hacen `import cgi`.

Aquí implementamos solo `parse_header`, suficiente para que
httpx funcione correctamente.
"""

from __future__ import annotations

from typing import Dict, Tuple


def parse_header(value: str) -> Tuple[str, Dict[str, str]]:
    """
    Parse un encabezado tipo Content-Type.

    Devuelve (valor_principal, dict_parametros), similar al
    antiguo cgi.parse_header.
    """
    if not value:
        return "", {}

    parts = [p.strip() for p in value.split(";")]
    main = parts[0]
    params: Dict[str, str] = {}

    for part in parts[1:]:
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip().lower()
        val = val.strip().strip('"').strip("'")
        if key:
            params[key] = val

    return main, params


__all__ = ["parse_header"]

