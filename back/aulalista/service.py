"""Lógica de negocio de AulaLista. El docente decide; la IA solo prepara borradores."""
from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from . import scoring, seed
from .config import Settings
from .errors import ApiError
from .generator import Generator, GeneratorError
from .repository import Repository
from .validators import (
    clean_text,
    deep_copy,
    normalize_context,
    parse_declared_date,
    validate_lesson_content,
)

REVIEW_DRAFT = "borrador"
REVIEW_REVIEWED = "revisada"
JOB_READY_DELAY = timedelta(seconds=1)
ITEMS_LIST_LIMIT = 100
KNOWN_ENGINES = ("local-simulado", "local-respaldo", "bedrock")


def new_id(prefix: str) -> str:
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def user_label(user_id: str) -> str:
    return seed.USERS.get(user_id, "Docente (%s)" % user_id)


class Service:
    def __init__(self, repo: Repository, generator: Generator, settings: Settings,
                 clock: Callable[[], str] = utc_now):
        self.repo = repo
        self.generator = generator
        self.settings = settings
        self.clock = clock
        self._jobs = (ThreadPoolExecutor(max_workers=2, thread_name_prefix="aulalista-job")
                      if settings.job_mode == "thread" else None)
        self.seed_demo_data()

    def close(self) -> None:
        if self._jobs is not None:
            self._jobs.shutdown(wait=True)
        self.repo.close()

    # ------------------------------------------------------------------
    # Datos simulados
    # ------------------------------------------------------------------
    def seed_demo_data(self) -> None:
        exp = seed.SEED_EXPERIENCE
        if self.repo.get_experience(exp["id"]):
            return
        module = self.get_module(exp["context"]["moduleId"])
        content = validate_lesson_content(exp["content"], module, exp["context"])
        now = self.clock()
        self.repo.add_experience(
            {
                "id": exp["id"], "authorId": exp["authorId"], "sourceSessionId": None, "sourceVersionId": None,
                "title": exp["title"], "purpose": exp["purpose"], "grade": exp["grade"],
                "materials": exp["materials"], "description": exp["description"],
                "observation": exp["observation"], "improvement": exp["improvement"],
                "context": exp["context"], "content": content, "isSimulated": True, "createdAt": now,
            }
        )
        for reviewer, values, context in exp["ratings"]:
            self.repo.upsert_rating(
                {
                    "id": "rt-seed-%s" % reviewer, "versionId": exp["id"], "reviewerId": reviewer,
                    "clarity": values[0], "feasibility": values[1], "coherence": values[2],
                    "observation": values[3], "context": context, "whatToKeep": "", "whatToChange": "",
                    "isSimulated": True, "createdAt": now, "updatedAt": now,
                }
            )
        self.repo.add_comment(
            {
                "id": "cm-seed-1", "versionId": exp["id"], "authorId": "u-sim-2",
                "text": "Yo probaría mostrar primero una demostración breve con dos voluntarios.",
                "isSimulated": True, "createdAt": now,
            }
        )

    # ------------------------------------------------------------------
    # Salud y portada
    # ------------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "team": self.settings.team_id}

    def overview(self, user: str) -> Dict[str, Any]:
        sessions = self.list_sessions(user)
        return {
            "user": {"id": user, "label": user_label(user)},
            "demoMode": self.settings.demo_mode,
            "generator": self.generator.info(),
            "recentSessions": sessions[:5],
            "sessionCount": len(sessions),
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
    # Mi aula: borradores
    # ------------------------------------------------------------------
    def _generation(self, fn: Callable[..., Dict[str, Any]], *args: Any) -> Dict[str, Any]:
        """Ejecuta el motor. Devuelve el resultado; el motor puede indicar en `_generatedBy` quién lo produjo."""
        try:
            return fn(*args)
        except ApiError:
            raise
        except GeneratorError as exc:
            raise ApiError(
                502,
                "generation_failed",
                "No pudimos crear el borrador: %s Tus datos siguen aquí y puedes reintentar." % exc,
            )
        except Exception:  # noqa: BLE001 - cualquier fallo del motor se informa sin perder lo escrito
            raise ApiError(
                502,
                "generation_failed",
                "No pudimos crear el borrador por un fallo inesperado. Tus datos siguen aquí y puedes reintentar.",
            )

    def generate_draft(self, user: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        module = self.get_module(payload.get("moduleId"))
        context = normalize_context(payload, module)
        raw = self._generation(self.generator.generate, module, context)
        engine = self._engine_of(raw)
        content = validate_lesson_content(raw, module, context)
        return self._draft_response(module, context, content, None, engine)

    def _engine_of(self, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict) and isinstance(raw.get("_generatedBy"), dict):
            return raw.pop("_generatedBy")
        return self.generator.info()

    def _draft_response(self, module, context, content, provenance, engine) -> Dict[str, Any]:
        return {
            "isDraft": True,
            "reviewStatus": REVIEW_DRAFT,
            "context": context,
            "content": content,
            "generatedBy": engine,
            "module": self._module_summary(module),
            "provenance": provenance,
        }

    def _generated_by(self, claimed: Any) -> Dict[str, Any]:
        """Origen declarado por el cliente al guardar. Solo se aceptan motores conocidos de este servidor."""
        engine = claimed.get("engine") if isinstance(claimed, dict) else None
        if engine == self.generator.name:
            return self.generator.info()
        if engine == "local-respaldo" and self.generator.name == "bedrock":
            return self.generator.fallback_info()  # type: ignore[attr-defined]
        return {"engine": "manual", "isBedrock": False, "label": "Escrita o editada por el docente."}

    def _resolve_provenance(self, raw: Any) -> Optional[Dict[str, Any]]:
        if raw is None:
            return None
        if not isinstance(raw, dict) or not isinstance(raw.get("experienceId"), str):
            raise ApiError(422, "invalid_provenance", "La procedencia de la adaptación no es válida.")
        exp = self.repo.get_experience(raw["experienceId"])
        if not exp:
            raise ApiError(422, "invalid_provenance", "La experiencia de origen no existe.")
        return {
            "type": "adaptacion",
            "experienceId": exp["id"],
            "versionId": exp["versionId"],
            "title": exp["title"],
            "authorLabel": user_label(exp["authorId"]),
            "isSimulated": exp["isSimulated"],
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

    @staticmethod
    def _review_status(payload: Dict[str, Any]) -> str:
        return REVIEW_REVIEWED if payload.get("markReviewed") is True else REVIEW_DRAFT

    def create_session(self, user: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        module = self.get_module(payload.get("moduleId"))
        context = normalize_context(payload.get("context"), module)
        content = validate_lesson_content(payload.get("content"), module, context)
        provenance = self._resolve_provenance(payload.get("provenance"))
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
            "generatedBy": self._generated_by(payload.get("generatedBy")), "createdAt": now,
        }
        self.repo.create_session(session, version)
        return self.get_session(user, session_id)

    def add_version(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        parent = self.repo.get_version(session["currentVersionId"])
        module = self.get_module(session["moduleId"])
        context_in = payload.get("context")
        if context_in is None:
            context = parent["context"]
        else:
            context = normalize_context(context_in, module)
        content = validate_lesson_content(payload.get("content"), module, context)
        now = self.clock()
        version = {
            "id": new_id("ver"), "sessionId": session_id, "number": self._next_number(session_id),
            "parentVersionId": parent["id"], "context": context, "content": content,
            # Una edición posterior es siempre otro borrador, salvo revisión expresa del docente.
            "reviewStatus": self._review_status(payload),
            "reason": clean_text(payload.get("reason"), "motivo del cambio", max_len=300) or "Edición del docente",
            "generatedBy": self._generated_by(payload.get("generatedBy")), "createdAt": now,
        }
        self.repo.add_version(version, content["title"], now)
        return self.get_session(user, session_id)

    def _next_number(self, session_id: str) -> int:
        versions = self.repo.list_versions(session_id)
        return (versions[-1]["number"] + 1) if versions else 1

    def review_version(self, user: str, session_id: str, version_id: str) -> Dict[str, Any]:
        self._owned_session(user, session_id)
        version = self.repo.get_version(version_id)
        if not version or version["sessionId"] != session_id:
            raise ApiError(404, "version_not_found", "No encontramos esa versión.")
        self.repo.set_review_status(version_id, REVIEW_REVIEWED)
        self.repo.touch_session(session_id, self.clock())
        return self.get_session(user, session_id)

    def regenerate(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Regenera con el contexto vigente. La nueva versión es borrador: no hereda la aprobación."""
        session = self._owned_session(user, session_id)
        parent = self.repo.get_version(session["currentVersionId"])
        module = self.get_module(session["moduleId"])
        merged = dict(parent["context"])
        for key in ("grade", "durationMinutes", "materials", "notes"):
            if key in payload:
                merged[key] = payload[key]
        context = normalize_context(merged, module)
        raw = self._generation(self.generator.generate, module, context)
        engine = self._engine_of(raw)
        content = validate_lesson_content(raw, module, context)
        now = self.clock()
        version = {
            "id": new_id("ver"), "sessionId": session_id, "number": self._next_number(session_id),
            "parentVersionId": parent["id"], "context": context, "content": content,
            "reviewStatus": REVIEW_DRAFT, "reason": "Regenerada con el contexto indicado",
            "generatedBy": engine, "createdAt": now,
        }
        self.repo.add_version(version, content["title"], now)
        return self.get_session(user, session_id)

    def copy_session(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        version_id = payload.get("versionId") or session["currentVersionId"]
        source = self.repo.get_version(version_id)
        if not source or source["sessionId"] != session_id:
            raise ApiError(404, "version_not_found", "No encontramos esa versión.")
        now = self.clock()
        new_session_id = new_id("ses")
        content = deep_copy(source["content"])
        content["title"] = "Copia de " + source["content"]["title"]
        copy_session = {
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
            "generatedBy": source["generatedBy"], "createdAt": now,
        }
        self.repo.create_session(copy_session, version)
        return self.get_session(user, new_session_id)

    def list_sessions(self, user: str) -> List[Dict[str, Any]]:
        shared_sources = {
            e["sourceVersionId"] for e in self.repo.list_experiences() if e["authorId"] == user and e["sourceVersionId"]
        }
        result = []
        for session in self.repo.list_sessions(user):
            versions = self.repo.list_versions(session["id"])
            current = next(v for v in versions if v["id"] == session["currentVersionId"])
            result.append(
                {
                    "id": session["id"], "title": session["title"], "moduleId": session["moduleId"],
                    "updatedAt": session["updatedAt"], "createdAt": session["createdAt"],
                    "versionCount": len(versions), "currentVersionNumber": current["number"],
                    "reviewStatus": current["reviewStatus"],
                    "recordCount": len(self.repo.list_records(session["id"])),
                    "provenance": session["provenance"],
                    "isShared": any(v["id"] in shared_sources for v in versions),
                }
            )
        return result

    def get_session(self, user: str, session_id: str) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        versions = self.repo.list_versions(session_id)
        module = self.get_module(session["moduleId"])
        return {
            **session,
            "currentVersion": next(v for v in versions if v["id"] == session["currentVersionId"]),
            "versions": versions,
            "records": self.repo.list_records(session_id),
            "module": self._module_summary(module),
        }

    # ------------------------------------------------------------------
    # Mi portafolio: registro de aplicación
    # ------------------------------------------------------------------
    def add_record(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        version_id = payload.get("versionId") or session["currentVersionId"]
        version = self.repo.get_version(version_id)
        if not version or version["sessionId"] != session_id:
            raise ApiError(404, "version_not_found", "No encontramos esa versión.")
        record = {
            "id": new_id("rec"), "sessionId": session_id, "versionId": version_id,
            "declaredDate": parse_declared_date(payload.get("declaredDate")),
            "activity": clean_text(payload.get("activity"), "actividad realizada", required=True),
            "observation": clean_text(payload.get("observation"), "observación", required=True),
            "nextAdjustment": clean_text(payload.get("nextAdjustment"), "próximo ajuste"),
            # En la demo pública todo registro es simulado, aunque el cliente diga otra cosa.
            "isSimulated": True if self.settings.demo_mode else bool(payload.get("isSimulated", False)),
            "createdAt": self.clock(),
        }
        self.repo.add_record(record)
        self.repo.touch_session(session_id, record["createdAt"])
        return record

    # ------------------------------------------------------------------
    # Mi red: Aprendemos juntos
    # ------------------------------------------------------------------
    def share_session(self, user: str, session_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        session = self._owned_session(user, session_id)
        if payload.get("confirm") is not True:
            raise ApiError(422, "confirm_required", "Confirma expresamente que quieres compartir una copia.")
        version_id = payload.get("versionId") or session["currentVersionId"]
        version = self.repo.get_version(version_id)
        if not version or version["sessionId"] != session_id:
            raise ApiError(404, "version_not_found", "No encontramos esa versión.")
        if version["reviewStatus"] != REVIEW_REVIEWED:
            raise ApiError(409, "not_reviewed", "Revisa la versión antes de compartirla.")
        if self.repo.find_experience_by_source(user, version_id):
            raise ApiError(409, "already_shared", "Ya compartiste una copia de esta versión.")
        experience = {
            "id": new_id("exp"), "authorId": user, "sourceSessionId": session_id, "sourceVersionId": version_id,
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
        self.repo.add_experience(experience)
        return self.get_experience(user, experience["id"])

    def list_experiences(self, user: str) -> List[Dict[str, Any]]:
        return [self._experience_card(e, user) for e in self.repo.list_experiences()]

    def _rating_summary(self, experience: Dict[str, Any]) -> Dict[str, Any]:
        return scoring.summarize(self.repo.list_ratings(experience["id"]))

    def _experience_card(self, e: Dict[str, Any], user: str) -> Dict[str, Any]:
        return {
            "id": e["id"], "versionId": e["versionId"], "title": e["title"], "purpose": e["purpose"],
            "grade": e["grade"], "materials": e["materials"], "description": e["description"],
            "observation": e["observation"], "improvement": e["improvement"],
            "authorLabel": user_label(e["authorId"]), "isMine": e["authorId"] == user,
            "isSimulated": e["isSimulated"], "createdAt": e["createdAt"],
            "ratingSummary": self._rating_summary(e),
        }

    def get_experience(self, user: str, experience_id: str) -> Dict[str, Any]:
        e = self.repo.get_experience(experience_id)
        if not e:
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        card = self._experience_card(e, user)
        ratings = self.repo.list_ratings(experience_id)
        card["content"] = e["content"]
        card["context"] = e["context"]
        card["ratings"] = [
            {
                **{k: r[k] for k in ("clarity", "feasibility", "coherence", "observation", "context",
                                     "whatToKeep", "whatToChange", "isSimulated", "createdAt", "updatedAt")},
                "complete": scoring.is_complete(r),
                "reviewerLabel": user_label(r["reviewerId"]),
                "isMine": r["reviewerId"] == user,
            }
            for r in ratings
        ]
        card["myRating"] = next((r for r in card["ratings"] if r["isMine"]), None)
        card["comments"] = [
            {
                "id": c["id"], "text": c["text"], "authorLabel": user_label(c["authorId"]),
                "isSimulated": c["isSimulated"], "createdAt": c["createdAt"], "kind": "diseno",
            }
            for c in self.repo.list_comments(experience_id)
        ]
        return card

    def rate_experience(self, user: str, experience_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        e = self.repo.get_experience(experience_id)
        if not e:
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        if e["authorId"] == user:
            raise ApiError(
                403, "own_rating", "La autoevaluación del autor no entra en la valoración de la comunidad."
            )
        if payload.get("declaredUse") is not True:
            raise ApiError(
                422, "use_not_declared",
                "Solo puedes valorar si declaras que usaste la actividad. Si solo la leíste, deja un comentario de diseño.",
            )
        values = scoring.parse_values(payload)
        if all(v is None for v in values.values()):
            raise ApiError(422, "empty_rating", "Valora al menos un criterio o deja un comentario de diseño.")
        now = self.clock()
        created = self.repo.upsert_rating(
            {
                "id": new_id("rt"), "versionId": experience_id, "reviewerId": user, **values,
                "context": clean_text(payload.get("context"), "contexto de uso", required=True, max_len=200),
                "whatToKeep": clean_text(payload.get("whatToKeep"), "qué mantendrías", max_len=1000),
                "whatToChange": clean_text(payload.get("whatToChange"), "qué cambiarías", max_len=1000),
                "isSimulated": self.settings.demo_mode, "createdAt": now, "updatedAt": now,
            }
        )
        return {"created": created, "experience": self.get_experience(user, experience_id)}

    def add_comment(self, user: str, experience_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.repo.get_experience(experience_id):
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        self.repo.add_comment(
            {
                "id": new_id("cm"), "versionId": experience_id, "authorId": user,
                "text": clean_text(payload.get("text"), "comentario", required=True, max_len=1000),
                "isSimulated": self.settings.demo_mode, "createdAt": self.clock(),
            }
        )
        return self.get_experience(user, experience_id)

    def summarize_experience(self, user: str, experience_id: str) -> Dict[str, Any]:
        e = self.repo.get_experience(experience_id)
        if not e:
            raise ApiError(404, "experience_not_found", "No encontramos esa experiencia.")
        ratings = self.repo.list_ratings(experience_id)
        comments = self.repo.list_comments(experience_id)
        return self._generation(
            self.generator.summarize, e, scoring.summarize(ratings), ratings, comments
        )

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
        engine = self._engine_of(raw)
        content = validate_lesson_content(raw, module, context)
        provenance = self._resolve_provenance({"experienceId": experience_id})
        return self._draft_response(module, context, content, provenance, engine)

    # ------------------------------------------------------------------
    # Reconocimientos descriptivos (derivados de acciones comprobables)
    # ------------------------------------------------------------------
    def recognitions(self, user: str) -> Dict[str, Any]:
        mine = [e for e in self.repo.list_experiences() if e["authorId"] == user]
        mine_ids = {e["id"] for e in mine}
        sessions = self.repo.list_all_sessions()
        documented = 0
        for session in self.repo.list_sessions(user):
            for version in self.repo.list_versions(session["id"]):
                if version["number"] > 1 and len((version.get("reason") or "").strip()) >= 10:
                    documented += 1
        adapted_by_others = sum(
            1 for s in sessions
            if s["ownerId"] != user and s["provenance"] and s["provenance"].get("experienceId") in mine_ids
        )
        return {
            "sharedExperiences": len(mine),
            "documentedImprovements": documented,
            "adaptedByOthers": adapted_by_others,
            "text": "Has compartido %d experiencias, documentado %d mejoras y %d de tus recursos fueron adaptados por otras personas."
            % (len(mine), documented, adapted_by_others),
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
        newest = sorted(self.repo.list_items(), key=lambda i: (i["createdAt"], i["id"]), reverse=True)
        return [{"id": i["id"], "value": json.loads(i["value"])} for i in newest[:ITEMS_LIST_LIMIT]]

    def create_job(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        value = payload.get("input")
        if not isinstance(value, str) or not value or len(value) > 1000:
            raise ApiError(422, "invalid_field", "«input» debe ser un texto de 1 a 1000 caracteres.")
        job_id = new_id("job")
        self.repo.add_job(job_id, value, self.clock())
        if self._jobs is not None:
            # Servidor local: un worker en segundo plano procesa el trabajo.
            self._jobs.submit(self._run_job, job_id, value)
        # En Lambda (job_mode «lazy») el trabajo queda en cola y se resuelve en la primera lectura
        # posterior a su hora de disponibilidad (1 s), con el estado persistido en DynamoDB.
        return {"jobId": job_id, "status": "queued"}

    def _run_job(self, job_id: str, value: str) -> None:
        try:
            self.repo.update_job(job_id, "running", self.clock())
            self.repo.update_job(job_id, "done", self.clock(), output=value[::-1])
        except Exception as exc:  # noqa: BLE001
            self.repo.update_job(job_id, "failed", self.clock(), error=str(exc)[:200])

    def _job_ready(self, job: Dict[str, Any]) -> bool:
        try:
            created = datetime.fromisoformat(job["createdAt"])
            now = datetime.fromisoformat(self.clock())
        except (KeyError, TypeError, ValueError):
            return True
        return now - created >= JOB_READY_DELAY

    def get_job(self, job_id: str) -> Dict[str, Any]:
        job = self.repo.get_job(job_id)
        if not job:
            raise ApiError(404, "job_not_found", "No encontramos ese trabajo.")
        if self._jobs is None and job["status"] == "queued" and self._job_ready(job):
            self._run_job(job_id, job["input"])
            job = self.repo.get_job(job_id)
        body = {"jobId": job["jobId"], "status": job["status"], "output": job.get("output")}
        if job["status"] == "done":
            body["output"] = job["output"]
        if job["status"] == "failed":
            body["error"] = job["error"]
        return body
