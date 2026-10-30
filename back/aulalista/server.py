"""Servidor local: sirve la API y los archivos estáticos de `front/` en el mismo origen."""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from .api import handle_request, is_api_path
from .config import Settings, load_settings
from .factory import build_service
from .service import Service
from .static import SECURITY_HEADERS, resolve_static


def make_handler(service: Service, front_dir: Optional[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AulaLista/0.2"

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

        def _dispatch(self) -> None:
            path = self.path.split("?", 1)[0]
            if is_api_path(path):
                self._api()
            elif self.command in ("GET", "HEAD"):
                status, body, ctype = resolve_static(front_dir, self.path)
                self._send(status, body, ctype, {"Cache-Control": "no-cache"})
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
    print("AulaLista en http://%s:%d  (generador: %s, almacén: %s, modo demo: %s)"
          % (settings.host, httpd.server_address[1], settings.generator, settings.store, settings.demo_mode))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        httpd.service.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    main()
