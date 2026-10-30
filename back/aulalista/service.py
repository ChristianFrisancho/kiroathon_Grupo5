"""Lógica de negocio de Docente Presente. El docente decide; la IA solo prepara borradores."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from . import scoring, seed
from .config import Settings
from .errors import AlreadyExists, ApiError, VersionConflict, version_conflict
from .generator import Generator, GeneratorError
from .jobs import process_job
from .validators import (
    clean_text,
    deep_copy,
    normalize_context,
    parse_declared_date,
    validate_lesson_content,
)

REVIEW_DRAFT = "borrador"
REVIEW_REVIEWED = "revisada"
ITEMS_LIST_LIMIT = 100
RECENT_LIMIT = 5
DRAFT_TTL = timedelta(hours=24)
STALE_OPERATION = timedelta(minutes=2)
OPERATION_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{8,80}$")

MANUAL_ORIGIN = {"engine": "manual", "isBedrock": False, "label": "Escrita por el docente."}
UNVERIFIED_NOTE = ("No pudimos verificar el borrador de origen (no existe, caducó o no es tuyo); "
                   "la sesión se guardó como contenido del docente.")


def new_id(prefix: str) -> str:
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def user_label(user_id: str) -> str:
    return seed.USERS.get(user_id, "Docente (%s)" % user_id)


def content_digest(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


class Service:
    def __init__(self, repo: Any, generator: Generator, settings: Settings,
                 clock: Callable[[], str] = utc_now, dispatcher: Optional[Callable[[str], None]] = None):
        self.repo = repo
        self.generator = generator
        self.settings = settings
        self.clock = clock
        self.dispatcher = dispatcher
        self._jobs = (ThreadPoolExecutor(max_workers=2, thread_name_prefix="aulalista-job")
                      if settings.job_mode == "thread" else None)
        if hasattr(repo, "migrate_legacy"):
            repo.migrate_legacy()
        self.seed_demo_data()

    def close(self) -> None:
        if self._jobs is not None:
            self._jobs.shutdown(wait=True)
        self.repo.close()

    # ------------------------------------------------------------------
    # Datos simulados (ids fijos: sembrar dos veces no duplica)
    # ------------------------------------------------------------------
    def seed_demo_data(self) -> None:
        exp = seed.SEED_EXPERIENCE
        if not self.repo.get_experience(exp["id"]):
            module = self.get_module(exp["context"]["moduleId"])
            content = validate_lesson_content(exp["content"], module, exp["context"])
            try:
                self.repo.add_experience({
                    "id": exp["id"], "authorId": exp["authorId"], "sourceSessionId": None, "sourceVersionId": None,
                    "title": exp["title"], "purpose": exp["purpose"], "grade": exp["grade"],
                    "materials": exp["materials"], "description": exp["description"],
                    "observation": exp["observation"], "improvement": exp["improvement"],
                    "context": exp["context"], "content": content, "isSimulated": True, "createdAt": self.clock(),
                })
            except AlreadyExists:
                pass
        if self.repo.list_ratings(exp["id"]):
            return
        now = "2026-10-30T10:00:00.000+00:00"
        for reviewer, values, context in exp["ratings"]:
            self.repo.upsert_rating({
                "id": "rt-seed-%s" % reviewer, "versionId": exp["id"], "reviewerId": reviewer,
                "clarity": values[0], "feasibility": values[1], "coherence": values[2],
                "observation": values[3], "context": context, "whatToKeep": "", "whatToChange": "",
                "isSimulated": True, "createdAt": now, "updatedAt": now,
            })
        self.repo.add_comment({
            "id": "cm-seed-1", "versionId": exp["id"], "authorId": "u-sim-2",
            "text": "Yo probaría mostrar primero una demostración breve con dos voluntarios.",
            "isSimulated": True, "createdAt": now,
        })

    # ------------------------------------------------------------------
    # Salud y portada
    # ------------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "team": self.settings.team_id}

    def overview(self, user: str) -> Dict[str, Any]:
        """Acotado: una consulta de resúmenes (máximo 5) y un conteo; no lee versiones ni registros."""
        recent = self.repo.list_sessions(user, limit=RECENT_LIMIT)
        return {
            "user": {"id": user, "label": user_label(user)},
            "demoMode": self.settings.demo_mode,
            "generator": self.generator.info(),
            "recentSessions": [self._summary_view(s, set()) for s in recent],
            "sessionCount": self.repo.count_sessions(user),
            "defaultCase": seed.DEFAULT_CASE,
        }

    # ------------------------------------------------------------------
    # Mi aprendizaje
    # ------------------------------------------------------------------
    def list_modules(self) -> List[Dict[str, Any]]:
        return [self._module_summary(m) for m in seed.MODULES.values()]

    @staticmethod
    def _module_summary(module: Dict[str, Any]) -> Dict[str, Any]:
        return {k: module[k] for k in ("id", "version", "title", "sourceLabel", "isSimulated")}

    def get_module(self, module_id: Any) -> Dict[str, Any]:
        module = seed.MODULES.get(module_id) if isinstance(module_id, str) else None
        if module is None:
            raise ApiError(404, "module_not_found", "No encontramos ese módulo.")
        return deep_copy(module)

    # ------------------------------------------------------------------
    # Idempotencia: misma clave + mismo contenido → mismo resultado, sin duplicar
    # ------------------------------------------------------------------
    def _once(self, user: str, op: str, payload: Dict[str, Any], fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        key = payload.get("operationKey")
        if key is None:
            return fn()
        if not isinstance(key, str) or not OPERATION_KEY_RE.match(key):
            raise ApiError(422, "invalid_operation_key", "La clave de operación no es válida.")
        body = {k: v for k, v in payload.items() if k != "operationKey"}
        digest = content_digest({"op": op, "payload": body})
        now = self.clock()
        existing = self.repo.reserve_operation(user, key, digest, now)
        if existing is not None:
            if existing["digest"] != digest:
                raise ApiError(422, "operation_key_reused",
                               "Esta clave de operación ya se usó con otro contenido. Vuelve a intentarlo.")
            if existing["status"] == "done":
                return existing["result"]
            started = existing.get("createdAt")
            if not started or _parse_time(now) - _parse_time(started) < STALE_OPERATION:
                raise ApiError(409, "operation_in_progress",
                               "Esta operación todavía se está procesando. Revisa Mi portafolio en unos segundos.")
        try:
            result = fn()
        except Exception:
            self.repo.release_operation(user, key)
            raise
        self.repo.complete_operation(user, key, result)
        return result

    # ------------------------------------------------------------------
    # Mi aula: borradores emitidos por el servidor
    # ------------------------------------------------------------------
    def _generation(self, fn: Callable[..., Dict[str, Any]], *args: Any) -> Dict[str, Any]:
        """Ejecuta el motor. El resultado puede traer `_generatedBy` y `_reviewNotes`."""
        try:
            return fn(*args)
        except ApiError:
            raise
        except GeneratorError as exc:
            raise ApiError(502, "generation_failed",
                           "No pudimos crear el borrador: %s Tus datos siguen aquí y puedes reintentar." % exc)
        except Exception:  # noqa: BLE001 - cualquier fallo del motor se informa sin perder lo escrito
            raise ApiError(502, "generation_failed",
                           "No pudimos crear el borrador por un fallo inesperado. Tus datos siguen aquí y puedes reintentar.")

    def _engine_of(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(raw.get("_generatedBy"), dict):
            return raw.pop("_generatedBy")
        return self.generator.info()

    @staticmethod
    def _notes_of(raw: Dict[str, Any]) -> List[str]:
        notes = raw.pop("_reviewNotes", None)
        return [n for n in notes if isinstance(n, str)] if isinstance(notes, list) else []

    def _issue_draft(self, user: str, module, context, content, engine, notes, provenance) -> Dict[str, Any]:
        now = self.clock()
        expires = _parse_time(now) + DRAFT_TTL
        draft = {
            "id": new_id("drf"), "ownerId": user, "moduleId": module["id"], "moduleVersion": module["version"],
            "context": context, "content": content, "digest": content_digest(content), "generatedBy": engine,
            "reviewNotes": notes, "provenance": provenance, "createdAt": now,
            "expiresAt": expires.isoformat(timespec="milliseconds"), "expiresEpoch": int(expires.timestamp()),
        }
        self.repo.put_draft(draft)
        return {
            "draftId": draft["id"], "isDraft": True, "reviewStatus": REVIEW_DRAFT, "context": context,
            "content": content, "generatedBy": engine, "reviewNotes": notes,
            "module": self._module_summary(module), "provenance": provenance, "expiresAt": draft["expiresAt"],
        }

    def generate_draft(self, user: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        module = self.get_module(payload.get("moduleId"))
        context = normalize_context(payload, module)
        raw = self._generation(self.generator.generate, module, context)
        engine, notes = self._engine_of(raw), self._notes_of(raw)
        content = validate_lesson_content(raw, module, context)
        return self._issue_draft(user, module, context, content, engine, notes, None)

    def _valid_draft(self, user: str, draft_id: Any, module_id: str) -> Optional[Dict[str, Any]]:
        if not isinstance(draft_id, str) or not draft_id:
            return None
        draft = self.repo.get_draft(draft_id)
        if not draft or draft.get("ownerId") != user or draft.get("moduleId") != module_id:
            return None
        if _parse_time(draft["expiresAt"]) < _parse_time(self.clock()):
            return None
        return draft

    def _resolve_provenance(self, raw: Any) -> Optional[Dict[str, Any]]:
        if raw is None:
            return None
        if not isinstance(raw, dict) or not isinstance(raw.get("experienceId"), str):
            raise ApiError(422, "invalid_provenance", "La procedencia de la adaptación no es válida.")
        exp = self.repo.get_experience(raw["experienceId"])
        if not exp:
            raise ApiError(422, "invalid_provenance", "La experiencia de origen no existe.")
        return {
            "type": "adaptacion", "experienceId": exp["id"], "versionId": exp["versionId"], "title": exp["title"],
            "authorLabel": user_label(exp["authorId"]), "isSimulated": exp["isSimulated"],
        }

    # ------------------------------------------------------------------
    # Mi aula / portafolio: sesiones y versiones
    # ------------------------------------------------------------------
    def _owned_session(self, user: str, session_id: str) -> Dict[str, Any]:
        session = self.repo.get_session(session_id)
        if not session:
            raise ApiError(404, "session_not_found", "No encontramos esa sesión.")
        if session["ownerId"] != user:
            raise ApiError(403, "forbidden", "Esta sesión pertenece a otra persona.")
        return session

    def _version_of(self, session_id: str, version_id: Any) -> Dict[str, Any]:
        version = self.repo.get_version(session_id, version_id) if isinstance(version_id, str) else None
        if not version:
            raise ApiError(404, "version_not_found", "No encontramos esa versión en esta sesión.")
        return version

    @staticmethod
    def _review_status(payload: Dict[str, Any]) -> str:
        return REVIEW_REVIEWED if payload.get("markReviewed") is True else REVIEW_DRAFT

    def create_session(self, user: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._once(user, "create_session", payload, lambda: self._create_session(user, payload))

    def _create_session(self, user: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        module = self.get_module(payload.get("moduleId"))
        context = normalize_context(payload.get("context"), module)
        content = validate_lesson_content(payload.get("content"), module, context)
        draft = self._valid_draft(user, payload.get("draftId"), module["id"])
        # La procedencia sale del borrador guardado en el servidor, nunca del navegador.
        if draft is not None:
            generated_by, edited, source_id = draft["generatedBy"], content_digest(content) != draft["digest"], draft["id"]
            provenance, note = draft.get("provenance"), None
        else:
            generated_by, edited, source_id = dict(MANUAL_ORIGIN), True, None
            provenance = self._resolve_provenance(payload.get("provenance"))
            note = UNVERIFIED_NOTE if payload.get("draftId") else None
        now = self.clock()
        session_id, version_id = new_id("ses"), new_id("ver")
        session = {
            "id": session_id, "ownerId": user, "title": content["title"], "moduleId": module["id"],
            "moduleVersion": module["version"], "provenance": provenance, "createdAt": now, "updatedAt": now,
        }
        version = {
            "id": version_id, "sessionId": session_id, "number": 1, "parentVersionId": None, "context": context,
            "content": content, "reviewStatus": self._review_status(payload),
            "reason": clean_text(payload.get("reason"), "motivo del cambio", max_len=300) or "Primera versión",
            "generatedBy": generated_by, "editedByTeacher": edited, "sourceDraftId": source_id, "createdAt": now,
        }
        self.repo.create_session(session, version)
        result = self.get_session(user, session_id)
        if note:
            result["provenanceNote"] = note
        return result

    def add_version(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._once(user, "add_version:" + session_id, payload, lambda: self._add_version(user, session_id, payload))

    def _parent(self, session: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        expected = payload.get("parentVersionId") or session["currentVersionId"]
        if expected != session["currentVersionId"]:
            raise version_conflict()
        return self._version_of(session["id"], expected)

    def _commit_version(self, session_id: str, parent: Dict[str, Any], version: Dict[str, Any], title: str) -> None:
        try:
            self.repo.add_version(version, title, version["createdAt"], parent["id"])
        except VersionConflict:
            raise version_conflict()

    def _add_version(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        parent = self._parent(session, payload)
        module = self.get_module(session["moduleId"])
        context_in = payload.get("context")
        context = parent["context"] if context_in is None else normalize_context(context_in, module)
        content = validate_lesson_content(payload.get("content"), module, context)
        version = {
            "id": new_id("ver"), "sessionId": session_id, "number": parent["number"] + 1,
            "parentVersionId": parent["id"], "context": context, "content": content,
            # Una edición posterior es siempre otro borrador, salvo revisión expresa del docente.
            "reviewStatus": self._review_status(payload),
            "reason": clean_text(payload.get("reason"), "motivo del cambio", max_len=300) or "Edición del docente",
            # La procedencia se hereda de la versión de partida (dato del servidor) y se marca la edición.
            "generatedBy": parent["generatedBy"],
            "editedByTeacher": bool(parent.get("editedByTeacher")) or content_digest(content) != content_digest(parent["content"]),
            "sourceDraftId": parent.get("sourceDraftId"), "createdAt": self.clock(),
        }
        self._commit_version(session_id, parent, version, content["title"])
        return self.get_session(user, session_id)

    def review_version(self, user: str, session_id: str, version_id: str) -> Dict[str, Any]:
        self._owned_session(user, session_id)
        self._version_of(session_id, version_id)
        try:
            self.repo.set_review_status(session_id, version_id, REVIEW_REVIEWED, self.clock())
        except VersionConflict:
            raise version_conflict()
        return self.get_session(user, session_id)

    def regenerate(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Regenera con el contexto vigente. La nueva versión es borrador: no hereda la aprobación."""
        session = self._owned_session(user, session_id)
        parent = self._parent(session, payload)
        module = self.get_module(session["moduleId"])
        merged = dict(parent["context"])
        for key in ("grade", "durationMinutes", "materials", "notes"):
            if key in payload:
                merged[key] = payload[key]
        context = normalize_context(merged, module)
        raw = self._generation(self.generator.generate, module, context)
        engine = self._engine_of(raw)
        self._notes_of(raw)
        content = validate_lesson_content(raw, module, context)
        version = {
            "id": new_id("ver"), "sessionId": session_id, "number": parent["number"] + 1,
            "parentVersionId": parent["id"], "context": context, "content": content,
            "reviewStatus": REVIEW_DRAFT, "reason": "Regenerada con el contexto indicado",
            "generatedBy": engine, "editedByTeacher": False, "sourceDraftId": None, "createdAt": self.clock(),
        }
        self._commit_version(session_id, parent, version, content["title"])
        return self.get_session(user, session_id)

    def copy_session(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._once(user, "copy:" + session_id, payload, lambda: self._copy_session(user, session_id, payload))

    def _copy_session(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        source = self._version_of(session_id, payload.get("versionId") or session["currentVersionId"])
        now = self.clock()
        new_session_id = new_id("ses")
        content = deep_copy(source["content"])
        content["title"] = ("Copia de " + source["content"]["title"])[:200]
        copy = {
            "id": new_session_id, "ownerId": user, "title": content["title"], "moduleId": session["moduleId"],
            "moduleVersion": session["moduleVersion"],
            "provenance": {"type": "copia", "sessionId": session_id, "versionId": source["id"]},
            "createdAt": now, "updatedAt": now,
        }
        version = {
            "id": new_id("ver"), "sessionId": new_session_id, "number": 1, "parentVersionId": None,
            "context": deep_copy(source["context"]), "content": content,
            # La copia no hereda la revisión: el docente debe revisarla de nuevo.
            "reviewStatus": REVIEW_DRAFT, "reason": "Copia de la versión %d" % source["number"],
            "generatedBy": source["generatedBy"], "editedByTeacher": bool(source.get("editedByTeacher")),
            "sourceDraftId": source.get("sourceDraftId"), "createdAt": now,
        }
        self.repo.create_session(copy, version)
        return self.get_session(user, new_session_id)

    def _shared_session_ids(self, user: str) -> set:
        return {e["sourceSessionId"] for e in self.repo.list_experiences()
                if e["authorId"] == user and e.get("sourceSessionId")}

    @staticmethod
    def _summary_view(s: Dict[str, Any], shared: set) -> Dict[str, Any]:
        return {
            "id": s["id"], "title": s["title"], "moduleId": s["moduleId"], "updatedAt": s["updatedAt"],
            "createdAt": s["createdAt"], "versionCount": s.get("versionCount", 1),
            "currentVersionNumber": s.get("currentVersionNumber", 1), "reviewStatus": s.get("reviewStatus"),
            "recordCount": s.get("recordCount", 0), "provenance": s.get("provenance"),
            "isShared": s["id"] in shared,
        }

    def list_sessions(self, user: str) -> List[Dict[str, Any]]:
        """Dos consultas en total: resúmenes del docente y el feed de experiencias (para «Copia compartida»)."""
        shared = self._shared_session_ids(user)
        return [self._summary_view(s, shared) for s in self.repo.list_sessions(user)]

    def get_session(self, user: str, session_id: str) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        versions = self.repo.list_versions(session_id)
        module = self.get_module(session["moduleId"])
        current = next((v for v in versions if v["id"] == session["currentVersionId"]), None)
        if current is None:
            raise ApiError(500, "inconsistent_session", "La sesión no tiene una versión vigente válida.")
        base = {k: session[k] for k in ("id", "ownerId", "title", "moduleId", "moduleVersion", "provenance",
                                        "currentVersionId", "createdAt", "updatedAt")}
        return {**base, "currentVersion": current, "versions": versions,
                "records": self.repo.list_records(session_id), "module": self._module_summary(module)}

    # ------------------------------------------------------------------
    # Mi portafolio: registro de aplicación
    # ------------------------------------------------------------------
    def add_record(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._once(user, "record:" + session_id, payload, lambda: self._add_record(user, session_id, payload))

    def _add_record(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        version = self._version_of(session_id, payload.get("versionId") or session["currentVersionId"])
        record = {
            "id": new_id("rec"), "sessionId": session_id, "versionId": version["id"],
            "versionNumber": version["number"],
            "declaredDate": parse_declared_date(payload.get("declaredDate")),
            "activity": clean_text(payload.get("activity"), "actividad realizada", required=True),
            "observation": clean_text(payload.get("observation"), "observación", required=True),
            "nextAdjustment": clean_text(payload.get("nextAdjustment"), "próximo ajuste"),
            # En la demo pública todo registro es simulado, aunque el cliente diga otra cosa.
            "isSimulated": True if self.settings.demo_mode else bool(payload.get("isSimulated", False)),
            "createdAt": self.clock(),
        }
        try:
            self.repo.add_record(record)
        except VersionConflict:
            raise ApiError(409, "busy_session", "La sesión cambió mientras guardabas el registro. Inténtalo de nuevo.")
        return record

    # ------------------------------------------------------------------
    # Mi red: Aprendemos juntos
    # ------------------------------------------------------------------
    def share_session(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._once(user, "share:" + session_id, payload, lambda: self._share_session(user, session_id, payload))

    def _share_session(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        if payload.get("confirm") is not True:
            raise ApiError(422, "confirm_required", "Confirma expresamente que quieres compartir una copia.")
        version = self._version_of(session_id, payload.get("versionId") or session["currentVersionId"])
        if version["reviewStatus"] != REVIEW_REVIEWED:
            raise ApiError(409, "not_reviewed", "Revisa la versión antes de compartirla.")
        experience = {
            "id": new_id("exp"), "authorId": user, "sourceSessionId": session_id, "sourceVersionId": version["id"],
            "title": clean_text(payload.get("title"), "título", max_len=200) or version["content"]["title"],
            "purpose": clean_text(payload.get("purpose"), "propósito", required=True),
            "grade": version["context"]["grade"], "materials": version["content"]["materials"],
            "description": clean_text(payload.get("description"), "descripción", required=True),
            # Solo se comparte lo que el autor escribió aquí; los registros privados no se copian.
            "observation": clean_text(payload.get("observation"), "observación", max_len=1000),
            "improvement": clean_text(payload.get("improvement"), "mejora propuesta", max_len=1000),
            "context": deep_copy(version["context"]), "content": deep_copy(version["content"]),
            "isSimulated": True if self.settings.demo_mode else False, "createdAt": self.clock(),
        }
        try:
            self.repo.add_experience(experience)
        except AlreadyExists:
            raise ApiError(409, "already_shared", "Ya compartiste una copia de esta versión.")
        return self.get_experience(user, experience["id"])

    def list_experiences(self, user: str) -> List[Dict[str, Any]]:
        return [self._experience_card(e, user) for e in self.repo.list_experiences()]

    def _experience_card(self, e: Dict[str, Any], user: str, ratings=None) -> Dict[str, Any]:
        ratings = self.repo.list_ratings(e["id"]) if ratings is None else ratings
        return {
            "id": e["id"], "versionId": e["versionId"], "title": e["title"], "purpose": e["purpose"],
            "grade": e["grade"], "materials": e["materials"], "description": e["description"],
            "observation": e["observation"], "improvement": e["improvement"],
            "authorLabel": user_label(e["authorId"]), "isMine": e["authorId"] == user,
            "isSimulated": e["isSimulated"], "createdAt": e["createdAt"],
            "ratingSummary": scoring.summarize(ratings),
        }

    def get_experience(self, user: str, experience_id: str) -> Dict[str, Any]:
        e = self.repo.get_experience(experience_id)
        if not e:
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        ratings = self.repo.list_ratings(experience_id)
        card = self._experience_card(e, user, ratings)
        card["content"] = e["content"]
        card["context"] = e["context"]
        card["ratings"] = [
            {
                **{k: r[k] for k in ("clarity", "feasibility", "coherence", "observation", "context",
                                     "whatToKeep", "whatToChange", "isSimulated", "createdAt", "updatedAt")},
                "complete": scoring.is_complete(r), "reviewerLabel": user_label(r["reviewerId"]),
                "isMine": r["reviewerId"] == user,
            }
            for r in ratings
        ]
        card["myRating"] = next((r for r in card["ratings"] if r["isMine"]), None)
        card["comments"] = [
            {"id": c["id"], "text": c["text"], "authorLabel": user_label(c["authorId"]),
             "isSimulated": c["isSimulated"], "createdAt": c["createdAt"], "kind": "diseno"}
            for c in self.repo.list_comments(experience_id)
        ]
        return card

    def rate_experience(self, user: str, experience_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        e = self.repo.get_experience(experience_id)
        if not e:
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        if e["authorId"] == user:
            raise ApiError(403, "own_rating", "La autoevaluación del autor no entra en la valoración de la comunidad.")
        if payload.get("declaredUse") is not True:
            raise ApiError(422, "use_not_declared",
                           "Solo puedes valorar si declaras que usaste la actividad. Si solo la leíste, deja un comentario de diseño.")
        values = scoring.parse_values(payload)
        if all(v is None for v in values.values()):
            raise ApiError(422, "empty_rating", "Valora al menos un criterio o deja un comentario de diseño.")
        now = self.clock()
        try:
            created = self.repo.upsert_rating({
                "id": new_id("rt"), "versionId": experience_id, "reviewerId": user, **values,
                "context": clean_text(payload.get("context"), "contexto de uso", required=True, max_len=200),
                "whatToKeep": clean_text(payload.get("whatToKeep"), "qué mantendrías", max_len=1000),
                "whatToChange": clean_text(payload.get("whatToChange"), "qué cambiarías", max_len=1000),
                "isSimulated": self.settings.demo_mode, "createdAt": now, "updatedAt": now,
            })
        except VersionConflict:
            raise ApiError(409, "busy_rating", "Tu valoración cambió en otra pestaña. Recarga y vuelve a intentarlo.")
        return {"created": created, "experience": self.get_experience(user, experience_id)}

    def add_comment(self, user: str, experience_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._once(user, "comment:" + experience_id, payload,
                          lambda: self._add_comment(user, experience_id, payload))

    def _add_comment(self, user: str, experience_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.repo.get_experience(experience_id):
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        self.repo.add_comment({
            "id": new_id("cm"), "versionId": experience_id, "authorId": user,
            "text": clean_text(payload.get("text"), "comentario", required=True, max_len=1000),
            "isSimulated": self.settings.demo_mode, "createdAt": self.clock(),
        })
        return self.get_experience(user, experience_id)

    def summarize_experience(self, user: str, experience_id: str) -> Dict[str, Any]:
        e = self.repo.get_experience(experience_id)
        if not e:
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        ratings = self.repo.list_ratings(experience_id)
        comments = self.repo.list_comments(experience_id)
        return self._generation(self.generator.summarize, e, scoring.summarize(ratings), ratings, comments)

    def adapt_experience(self, user: str, experience_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        e = self.repo.get_experience(experience_id)
        if not e:
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        module = self.get_module(e["context"]["moduleId"])
        merged = dict(e["context"])
        for key in ("grade", "durationMinutes", "materials", "notes"):
            if key in payload:
                merged[key] = payload[key]
        context = normalize_context(merged, module)
        raw = self._generation(self.generator.adapt, module, context, e)
        engine, notes = self._engine_of(raw), self._notes_of(raw)
        content = validate_lesson_content(raw, module, context)
        provenance = self._resolve_provenance({"experienceId": experience_id})
        return self._issue_draft(user, module, context, content, engine, notes, provenance)

    # ------------------------------------------------------------------
    # Reconocimientos descriptivos (derivados de acciones comprobables)
    # ------------------------------------------------------------------
    def recognitions(self, user: str) -> Dict[str, Any]:
        mine = [e["id"] for e in self.repo.list_experiences() if e["authorId"] == user]
        documented = sum(s.get("documentedVersions", 0) for s in self.repo.list_sessions(user))
        adapted = self.repo.count_adaptations(mine, user)
        return {
            "sharedExperiences": len(mine), "documentedImprovements": documented, "adaptedByOthers": adapted,
            "text": "Has compartido %d experiencias, documentado %d mejoras y %d de tus recursos fueron adaptados por otras personas."
            % (len(mine), documented, adapted),
        }

    # ------------------------------------------------------------------
    # Mi bienestar
    # ------------------------------------------------------------------
    DEFAULT_PREFERENCES = {"remindersEnabled": False, "reminderTime": None, "sharePublicly": False}

    def get_preferences(self, user: str) -> Dict[str, Any]:
        return {**self.DEFAULT_PREFERENCES, **(self.repo.get_preferences(user) or {})}

    def set_preferences(self, user: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_preferences(user)
        for key in ("remindersEnabled", "sharePublicly"):
            if key in payload:
                if not isinstance(payload[key], bool):
                    raise ApiError(422, "invalid_field", "«%s» debe ser sí o no." % key)
                current[key] = payload[key]
        if "reminderTime" in payload:
            value = payload["reminderTime"]
            if value is not None:
                try:
                    datetime.strptime(str(value), "%H:%M")
                except ValueError:
                    raise ApiError(422, "invalid_field", "La hora del recordatorio debe tener formato HH:MM.")
            current["reminderTime"] = value
        self.repo.set_preferences(user, current)
        return current

    # ------------------------------------------------------------------
    # Contratos de insignias (/items, /jobs)
    # ------------------------------------------------------------------
    def create_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "value" not in payload or payload["value"] is None:
            raise ApiError(422, "missing_field", "Falta «value».")
        encoded = json.dumps(payload["value"], ensure_ascii=False)
        if len(encoded) > 2000:
            raise ApiError(422, "field_too_long", "«value» es demasiado largo.")
        item_id = new_id("item")
        self.repo.add_item(item_id, encoded, self.clock())
        return {"id": item_id, "value": payload["value"]}

    def get_item(self, item_id: str) -> Dict[str, Any]:
        item = self.repo.get_item(item_id)
        if not item:
            raise ApiError(404, "item_not_found", "No encontramos ese elemento.")
        return {"id": item["id"], "value": json.loads(item["value"])}

    def list_items(self) -> List[Dict[str, Any]]:
        return [{"id": i["id"], "value": json.loads(i["value"])} for i in self.repo.list_items(ITEMS_LIST_LIMIT)]

    def create_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        value = payload.get("input")
        if not isinstance(value, str) or not value or len(value) > 1000:
            raise ApiError(422, "invalid_field", "«input» debe ser un texto de 1 a 1000 caracteres.")
        job_id = new_id("job")
        self.repo.add_job(job_id, value, self.clock())
        if self._jobs is not None:
            # Servidor local: un hilo del proceso (de larga vida) procesa el trabajo.
            self._jobs.submit(process_job, self.repo, job_id, self.clock)
        elif self.dispatcher is not None:
            # Lambda: se invoca de forma asíncrona la función worker; GET solo lee el estado.
            try:
                self.dispatcher(job_id)
            except Exception as exc:  # noqa: BLE001
                self.repo.update_job(job_id, "failed", self.clock(), error="dispatch_failed:%s" % type(exc).__name__)
                raise ApiError(503, "job_dispatch_failed",
                               "No pudimos enviar el trabajo al worker. Intenta de nuevo.", {"jobId": job_id})
        else:
            self.repo.update_job(job_id, "failed", self.clock(), error="no_worker")
            raise ApiError(503, "job_worker_missing", "No hay un worker configurado para procesar trabajos.",
                           {"jobId": job_id})
        return {"jobId": job_id, "status": "queued"}

    def get_job(self, job_id: str) -> Dict[str, Any]:
        job = self.repo.get_job(job_id)
        if not job:
            raise ApiError(404, "job_not_found", "No encontramos ese trabajo.")
        body = {"jobId": job["jobId"], "status": job["status"], "output": job.get("output")}
        if job["status"] == "failed":
            body["error"] = job.get("error")
        return body
