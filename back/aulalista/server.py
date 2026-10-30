"""Servidor local: sirve la API y los archivos estáticos de `front/` en el mismo origen."""
from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .api import handle_request, is_api_path
from .config import Settings, load_settings
from .generator import build_generator
from .repository import Repository
from .service import Service

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'",
}


def build_service(settings: Settings) -> Service:
    return Service(Repository(settings.db_path), build_generator(settings.generator), settings)


def make_handler(service: Service, front_dir: Optional[str]):
    front_root = Path(front_dir).resolve() if front_dir else None

    class Handler(BaseHTTPRequestHandler):
        server_version = "AulaLista/0.1"

        def log_message(self, fmt, *args):  # registros sin datos del cuerpo
            if os.environ.get("AULALISTA_QUIET"):
                return
            sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

        def _send(self, status: int, body: bytes, content_type: str, extra: Optional[dict] = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for key, value in SECURITY_HEADERS.items():
                self.send_header(key, value)
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _api(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(min(length, 512 * 1024)) if length else b""
            status, payload = handle_request(service, self.command, self.path, dict(self.headers), raw)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(status, body, "application/json; charset=utf-8", {"Cache-Control": "no-store"})

        def _static(self) -> None:
            if front_root is None:
                return self._send(404, b"Not found", "text/plain; charset=utf-8")
            rel = self.path.split("?", 1)[0].split("#", 1)[0]
            rel = "index.html" if rel in ("", "/") else rel.lstrip("/")
            target = (front_root / rel).resolve()
            if front_root not in target.parents and target != front_root:
                return self._send(404, b"Not found", "text/plain; charset=utf-8")
            if target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                return self._send(404, b"Not found", "text/plain; charset=utf-8")
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
                ctype += "; charset=utf-8"
            self._send(200, target.read_bytes(), ctype, {"Cache-Control": "no-cache"})

        def _dispatch(self) -> None:
            path = self.path.split("?", 1)[0]
            if is_api_path(path):
                self._api()
            elif self.command in ("GET", "HEAD"):
                self._static()
            else:
                self._send(405, b"Method not allowed", "text/plain; charset=utf-8")

        do_GET = do_POST = do_PUT = do_HEAD = do_DELETE = do_PATCH = _dispatch

    return Handler


def create_server(settings: Settings, service: Optional[Service] = None) -> ThreadingHTTPServer:
    service = service or build_service(settings)
    httpd = ThreadingHTTPServer((settings.host, settings.port), make_handler(service, settings.front_dir))
    httpd.service = service  # type: ignore[attr-defined]
    return httpd


def main() -> None:
    settings = load_settings()
    httpd = create_server(settings)
    print("AulaLista en http://%s:%d  (generador: %s, modo demo: %s)"
          % (settings.host, httpd.server_address[1], settings.generator, settings.demo_mode))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        httpd.service.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
