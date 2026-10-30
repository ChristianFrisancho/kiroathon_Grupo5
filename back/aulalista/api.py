"""Enrutador HTTP independiente del servidor.

`handle_request` recibe método, ruta, consulta, cabeceras y cuerpo en bytes, y devuelve (estado, cuerpo JSON).
Así la fase 2 puede envolverlo en una función Lambda sin reescribir rutas.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlsplit

from .errors import ApiError
from .seed import DEMO_USER_ID
from .service import Service
from .validators import validate_user_id

MAX_BODY_BYTES = 256 * 1024

Handler = Callable[["Request"], Tuple[int, Any]]


class Request:
    def __init__(self, service: Service, user: str, body: Dict[str, Any], query: Dict[str, str],
                 params: Dict[str, str]):
        self.service = service
        self.user = user
        self.body = body
        self.query = query
        self.params = params


_ROUTES: List[Tuple[str, "re.Pattern[str]", Handler]] = []


def route(method: str, pattern: str):
    regex = re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern) + "$")

    def decorator(fn: Handler) -> Handler:
        _ROUTES.append((method, regex, fn))
        return fn

    return decorator


def is_api_path(path: str) -> bool:
    """Rutas atendidas por la API (el resto se sirve como archivos estáticos del front)."""
    return path.startswith("/api/") or path == "/health" or path == "/items" or path.startswith("/items/") \
        or path == "/jobs" or path.startswith("/jobs/")


def _parse_body(raw: bytes, method: str) -> Dict[str, Any]:
    if method not in ("POST", "PUT", "PATCH"):
        return {}
    if len(raw) > MAX_BODY_BYTES:
        raise ApiError(413, "body_too_large", "La solicitud es demasiado grande.")
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ApiError(400, "invalid_json", "El cuerpo de la solicitud no es JSON válido.")
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "El cuerpo de la solicitud debe ser un objeto JSON.")
    return data


def handle_request(service: Service, method: str, target: str, headers: Optional[Dict[str, str]] = None,
                   raw_body: bytes = b"") -> Tuple[int, Any]:
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    parts = urlsplit(target)
    path = parts.path.rstrip("/") or "/"
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    try:
        allowed = set()
        for route_method, regex, handler in _ROUTES:
            match = regex.match(path)
            if not match:
                continue
            allowed.add(route_method)
            if route_method != method:
                continue
            # Usuario de demostración. No es autenticación: la fase 2 usará identidad real.
            user = validate_user_id(headers.get("x-user-id") or DEMO_USER_ID)
            body = _parse_body(raw_body, method)
            return handler(Request(service, user, body, query, match.groupdict()))
        if allowed:
            raise ApiError(405, "method_not_allowed", "Método no permitido.")
        raise ApiError(404, "not_found", "Ruta no encontrada.")
    except ApiError as exc:
        return exc.status, exc.to_body()
    except Exception:  # noqa: BLE001 - nunca filtrar trazas ni datos al cliente
        return 500, {"error": {"code": "internal_error", "message": "Ocurrió un error inesperado. Intenta de nuevo."}}


# ---- contratos de insignias -------------------------------------------------
@route("GET", "/health")
def health(req: Request):
    return 200, req.service.health()


@route("POST", "/items")
def create_item(req: Request):
    return 201, req.service.create_item(req.body)


@route("GET", "/items")
def list_items(req: Request):
    return 200, req.service.list_items()


@route("GET", "/items/{item_id}")
def get_item(req: Request):
    return 200, req.service.get_item(req.params["item_id"])


@route("POST", "/jobs")
def create_job(req: Request):
    return 202, req.service.create_job(req.body)


@route("GET", "/jobs/{job_id}")
def get_job(req: Request):
    return 200, req.service.get_job(req.params["job_id"])


# ---- Hoy / aprendizaje --------------------------------------------------------
@route("GET", "/api/overview")
def overview(req: Request):
    return 200, req.service.overview(req.user)


@route("GET", "/api/modules")
def modules(req: Request):
    return 200, req.service.list_modules()


@route("GET", "/api/modules/{module_id}")
def module(req: Request):
    return 200, req.service.get_module(req.params["module_id"])


# ---- Mi aula ----------------------------------------------------------------------
@route("POST", "/api/drafts/generate")
def generate_draft(req: Request):
    return 200, req.service.generate_draft(req.user, req.body)


@route("POST", "/api/sessions")
def create_session(req: Request):
    return 201, req.service.create_session(req.user, req.body)


@route("GET", "/api/sessions")
def list_sessions(req: Request):
    return 200, req.service.list_sessions(req.user)


@route("GET", "/api/sessions/{session_id}")
def get_session(req: Request):
    return 200, req.service.get_session(req.user, req.params["session_id"])


@route("POST", "/api/sessions/{session_id}/versions")
def add_version(req: Request):
    return 201, req.service.add_version(req.user, req.params["session_id"], req.body)


@route("POST", "/api/sessions/{session_id}/versions/{version_id}/review")
def review_version(req: Request):
    return 200, req.service.review_version(req.user, req.params["session_id"], req.params["version_id"])


@route("POST", "/api/sessions/{session_id}/regenerate")
def regenerate(req: Request):
    return 201, req.service.regenerate(req.user, req.params["session_id"], req.body)


@route("POST", "/api/sessions/{session_id}/copy")
def copy_session(req: Request):
    return 201, req.service.copy_session(req.user, req.params["session_id"], req.body)


@route("POST", "/api/sessions/{session_id}/records")
def add_record(req: Request):
    return 201, req.service.add_record(req.user, req.params["session_id"], req.body)


@route("POST", "/api/sessions/{session_id}/share")
def share_session(req: Request):
    return 201, req.service.share_session(req.user, req.params["session_id"], req.body)


# ---- Mi red ----------------------------------------------------------------------
@route("GET", "/api/experiences")
def list_experiences(req: Request):
    return 200, req.service.list_experiences(req.user)


@route("GET", "/api/experiences/{experience_id}")
def get_experience(req: Request):
    return 200, req.service.get_experience(req.user, req.params["experience_id"])


@route("POST", "/api/experiences/{experience_id}/ratings")
def rate_experience(req: Request):
    result = req.service.rate_experience(req.user, req.params["experience_id"], req.body)
    return (201 if result["created"] else 200), result


@route("POST", "/api/experiences/{experience_id}/comments")
def add_comment(req: Request):
    return 201, req.service.add_comment(req.user, req.params["experience_id"], req.body)


@route("GET", "/api/experiences/{experience_id}/summary")
def summarize_experience(req: Request):
    return 200, req.service.summarize_experience(req.user, req.params["experience_id"])


@route("POST", "/api/experiences/{experience_id}/adapt")
def adapt_experience(req: Request):
    return 200, req.service.adapt_experience(req.user, req.params["experience_id"], req.body)


@route("GET", "/api/recognitions")
def recognitions(req: Request):
    return 200, req.service.recognitions(req.user)


# ---- Mi bienestar -------------------------------------------------------------------
@route("GET", "/api/preferences")
def get_preferences(req: Request):
    return 200, req.service.get_preferences(req.user)


@route("PUT", "/api/preferences")
def set_preferences(req: Request):
    return 200, req.service.set_preferences(req.user, req.body)
