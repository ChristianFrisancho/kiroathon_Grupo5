"""Apoyos comunes de las pruebas. Importar este módulo deja `back/` en sys.path."""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("AULALISTA_QUIET", "1")  # sin registro de peticiones durante las pruebas

ROOT = Path(__file__).resolve().parents[1]
BACK = ROOT / "back"
FRONT = ROOT / "front"
if str(BACK) not in sys.path:
    sys.path.insert(0, str(BACK))

from aulalista.api import handle_request  # noqa: E402
from aulalista.config import Settings  # noqa: E402
from aulalista.generator import GeneratorError, LocalSimulatedGenerator  # noqa: E402
from aulalista.repository import Repository  # noqa: E402
from aulalista.service import Service  # noqa: E402

CASE = {
    "moduleId": "mod-escucha-activa",
    "grade": "Cuarto de primaria",
    "durationMinutes": 45,
    "materials": ["pizarra", "papel", "lápiz"],
    "notes": "",
}


def make_settings(db_path=":memory:", demo_mode=True, port=0):
    return Settings(
        db_path=db_path, front_dir=str(FRONT), demo_mode=demo_mode, generator="local",
        host="127.0.0.1", port=port,
    )


def make_service(db_path=":memory:", demo_mode=True, generator=None):
    return Service(Repository(db_path), generator or LocalSimulatedGenerator(), make_settings(db_path, demo_mode))


class TempDb:
    """Directorio temporal con una base SQLite en archivo, para probar persistencia real."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self._tmp.name) / "test.db")
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()


class Api:
    """Llama al enrutador sin red. Devuelve (estado, cuerpo)."""

    def __init__(self, service):
        self.service = service

    def __call__(self, method, path, body=None, user=None):
        headers = {"X-User-Id": user} if user else {}
        raw = json.dumps(body).encode("utf-8") if body is not None else b""
        return handle_request(self.service, method, path, headers, raw)


class FailingGenerator(LocalSimulatedGenerator):
    """Simula un servicio de IA caído o que agotó su tiempo."""

    def generate(self, module, context):
        raise GeneratorError("El servicio no respondió a tiempo.")

    def adapt(self, module, context, experience):
        raise GeneratorError("El servicio no respondió a tiempo.")


class WrongMinutesGenerator(LocalSimulatedGenerator):
    """Devuelve una sesión cuyos minutos no suman la duración."""

    def generate(self, module, context):
        content = super().generate(module, context)
        content["activities"][0]["minutes"] += 1
        return content


class BadReferenceGenerator(LocalSimulatedGenerator):
    def generate(self, module, context):
        content = super().generate(module, context)
        content["activities"][0]["references"] = ["M99"]
        return content


class UndeclaredMaterialGenerator(LocalSimulatedGenerator):
    def generate(self, module, context):
        content = super().generate(module, context)
        content["materials"] = content["materials"] + ["proyector"]
        return content


def generate_and_save(api, reviewed=False, user=None, case=None):
    """Genera un borrador y lo guarda. Devuelve la sesión creada."""
    status, draft = api("POST", "/api/drafts/generate", case or CASE, user)
    assert status == 200, draft
    status, session = api(
        "POST",
        "/api/sessions",
        {
            "moduleId": draft["module"]["id"],
            "context": draft["context"],
            "content": draft["content"],
            "markReviewed": reviewed,
            "draftId": draft["draftId"],
        },
        user,
    )
    assert status == 201, session
    return session


def rating_payload(values, used=True, context="Cuarto de primaria · pizarra y papel", **extra):
    keys = ("clarity", "feasibility", "coherence", "observation")
    payload = {"declaredUse": used, "context": context}
    for key, value in zip(keys, values):
        payload[key] = value
    payload.update(extra)
    return payload
