"""Entrega de archivos de `front/`, compartida por el servidor local y la Lambda."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import unquote

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'",
}

NOT_FOUND = (404, b"Not found", "text/plain; charset=utf-8")


def resolve_static(front_dir: Optional[str], raw_path: str) -> Tuple[int, bytes, str]:
    """Devuelve (estado, cuerpo, content-type). Nunca sale de `front_dir`."""
    if not front_dir:
        return NOT_FOUND
    root = Path(front_dir).resolve()
    rel = unquote(raw_path.split("?", 1)[0].split("#", 1)[0])
    rel = "index.html" if rel in ("", "/") else rel.lstrip("/")
    target = (root / rel).resolve()
    if root not in target.parents and target != root:
        return NOT_FOUND
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file():
        return NOT_FOUND
    ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    if ctype == "text/javascript":
        ctype = "application/javascript"
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
        ctype += "; charset=utf-8"
    return 200, target.read_bytes(), ctype
