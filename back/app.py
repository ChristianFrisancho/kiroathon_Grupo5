"""Punto de entrada de AWS Lambda (API Gateway HTTP API, payload 2.0).

Una sola función atiende la API (`/health`, `/items`, `/jobs`, `/api/...`) y entrega el frontend de `front/`
en el mismo dominio. Variables (template.yaml): TEAM_ID, TABLE_NAME, MODEL_ID, JOB_WORKER_FUNCTION.

Cada petición fija un plazo con `context.get_remaining_time_in_millis()` (budget.py) para que Bedrock no
consuma el tiempo que hace falta para validar, guardar y responder.
"""
from __future__ import annotations

import base64
import json
import os
import re
from typing import Any, Callable, Dict, Optional

from aulalista import budget
from aulalista.api import handle_request, is_api_path
from aulalista.config import Settings, load_settings
from aulalista.factory import build_service
from aulalista.service import Service
from aulalista.static import SECURITY_HEADERS, resolve_static

_service: Optional[Service] = None
_settings: Optional[Settings] = None


def lambda_settings() -> Settings:
    env = dict(os.environ)
    env.setdefault("AULALISTA_STORE", "dynamodb")
    env.setdefault("AULALISTA_GENERATOR", "bedrock")
    env.setdefault("AULALISTA_JOB_MODE", "lambda")
    env.setdefault("AULALISTA_FRONT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "front"))
    return load_settings(env)


def lambda_dispatcher(function_name: str) -> Callable[[str], None]:
    """Invoca el worker de forma asíncrona (InvocationType=Event). No espera su resultado."""
    import boto3

    client = boto3.client("lambda")

    def dispatch(job_id: str) -> None:
        response = client.invoke(FunctionName=function_name, InvocationType="Event",
                                 Payload=json.dumps({"jobId": job_id}).encode("utf-8"))
        if response.get("StatusCode") != 202:
            raise RuntimeError("El worker no aceptó el trabajo (estado %s)." % response.get("StatusCode"))

    return dispatch


def get_service() -> Service:
    """Un servicio por contenedor de Lambda (se reutiliza entre invocaciones)."""
    global _service, _settings
    if _service is None:
        _settings = lambda_settings()
        worker = os.environ.get("JOB_WORKER_FUNCTION")
        _service = build_service(_settings, dispatcher=lambda_dispatcher(worker) if worker else None)
    return _service


# La API es pública (contratos de las insignias): se permite leerla desde cualquier origen, sin credenciales.
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,Accept,X-User-Id",
    "Access-Control-Max-Age": "600",
}


def _response(status: int, body: bytes, content_type: str, cache: str, cors: bool = False) -> Dict[str, Any]:
    headers = {"Content-Type": content_type, "Cache-Control": cache, **SECURITY_HEADERS}
    if cors:
        headers.update(CORS_HEADERS)
    return {"statusCode": status, "headers": headers, "body": body.decode("utf-8"), "isBase64Encoded": False}


def _log(method: str, path: str, status: int, headers: Dict[str, Any]) -> None:
    """Registro mínimo para diagnosticar al verificador: sin cuerpo ni datos personales."""
    lower = {str(k).lower(): v for k, v in (headers or {}).items()}
    print(json.dumps({"event": "request", "method": method, "path": path, "status": status,
                      "origin": lower.get("origin"), "userAgent": (lower.get("user-agent") or "")[:120]}))


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    http = (event.get("requestContext") or {}).get("http") or {}
    method = (http.get("method") or event.get("httpMethod") or "GET").upper()
    # «//health» (URL base guardada con barra final) es la misma ruta que «/health».
    path = re.sub(r"/{2,}", "/", event.get("rawPath") or event.get("path") or "/")
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    query = event.get("rawQueryString") or ""
    target = path + ("?" + query if query else "")
    headers = event.get("headers") or {}

    if is_api_path(path) and method == "OPTIONS":  # preflight CORS
        _log(method, path, 204, headers)
        return _response(204, b"", "text/plain; charset=utf-8", "no-store", cors=True)

    if is_api_path(path):
        remaining = context.get_remaining_time_in_millis() if hasattr(context, "get_remaining_time_in_millis") else None
        budget.set_deadline_from_remaining_ms(remaining)
        try:
            raw = event.get("body") or ""
            raw_bytes = base64.b64decode(raw) if event.get("isBase64Encoded") else raw.encode("utf-8")
            status, payload = handle_request(get_service(), method, target, headers, raw_bytes)
        finally:
            budget.set_deadline(None)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        _log(method, path, status, headers)
        return _response(status, body, "application/json; charset=utf-8", "no-store", cors=True)

    if method not in ("GET", "HEAD"):
        return _response(405, b"Method not allowed", "text/plain; charset=utf-8", "no-store")
    front_dir = (_settings or lambda_settings()).front_dir
    status, body, ctype = resolve_static(front_dir, path)
    return _response(status, body, ctype, "no-cache")
