"""
Compat module for Python 3.13 where the stdlib `cgi` module
was removed but some third‑party libraries (like older httpx
used by googletrans) still import `cgi.parse_header`.

This implements only `parse_header` with a minimal behavior
good enough for Content-Type parsing.
"""

from __future__ import annotations

from typing import Dict, Tuple


def parse_header(value: str) -> Tuple[str, Dict[str, str]]:
    """
    Parse a Content-Type like header.

    Returns (main_value, params_dict), similar to the old cgi.parse_header.
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

