"""Validación determinista. El código valida formato, minutos e IDs; la pertinencia pedagógica es humana."""
from __future__ import annotations

import copy
import re
from datetime import date
from typing import Any, Dict, List, Optional

from .errors import ApiError

MIN_MINUTES = 10
MAX_MINUTES = 180
MAX_TEXT = 2000
MAX_SHORT = 200
MAX_MATERIALS = 20
MAX_ACTIVITIES = 12

USER_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def clean_text(value: Any, field: str, *, required: bool = False, max_len: int = MAX_TEXT) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ApiError(422, "invalid_field", "El campo «%s» debe ser texto." % field, {"field": field})
    value = value.strip()
    if required and not value:
        raise ApiError(422, "missing_field", "Completa el campo «%s»." % field, {"field": field})
    if len(value) > max_len:
        raise ApiError(
            422, "field_too_long", "El campo «%s» supera %d caracteres." % (field, max_len), {"field": field}
        )
    return value


def normalize_materials(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [part for part in re.split(r"[,;\n]", value)]
    if not isinstance(value, list):
        raise ApiError(422, "invalid_field", "Los materiales deben ser una lista.", {"field": "materials"})
    result: List[str] = []
    seen = set()
    for item in value:
        text = clean_text(item, "materials", max_len=60)
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    if len(result) > MAX_MATERIALS:
        raise ApiError(422, "too_many_materials", "Indica como máximo %d materiales." % MAX_MATERIALS)
    return result


def normalize_context(payload: Any, module: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApiError(422, "invalid_context", "El contexto de la clase debe ser un objeto.")
    duration = payload.get("durationMinutes")
    if isinstance(duration, str) and duration.strip().isdigit():
        duration = int(duration.strip())
    if not _is_int(duration) or not MIN_MINUTES <= duration <= MAX_MINUTES:
        raise ApiError(
            422,
            "invalid_duration",
            "La duración debe ser un número entero de minutos entre %d y %d." % (MIN_MINUTES, MAX_MINUTES),
            {"field": "durationMinutes"},
        )
    return {
        "moduleId": module["id"],
        "moduleVersion": module["version"],
        "grade": clean_text(payload.get("grade"), "grado", required=True, max_len=60),
        "durationMinutes": duration,
        "materials": normalize_materials(payload.get("materials")),
        "notes": clean_text(payload.get("notes"), "indicaciones", max_len=500),
    }


def validate_lesson_content(content: Any, module: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Valida y normaliza una sesión. Devuelve una copia limpia con las fuentes resueltas por el servidor."""
    problems: List[str] = []
    if not isinstance(content, dict):
        raise ApiError(422, "invalid_lesson", "La sesión debe ser un objeto.", ["La sesión no tiene formato válido."])

    def text(field: str, label: str, required: bool = True, max_len: int = MAX_TEXT) -> str:
        try:
            return clean_text(content.get(field), label, required=required, max_len=max_len)
        except ApiError as exc:
            problems.append(exc.message)
            return ""

    title = text("title", "título", max_len=MAX_SHORT)
    purpose = text("purpose", "propósito")
    evidence = text("expectedEvidence", "evidencia esperada")

    fragment_ids = {f["id"] for f in module["fragments"]}
    fragments_by_id = {f["id"]: f for f in module["fragments"]}

    declared = {m.casefold() for m in context["materials"]}
    try:
        materials = normalize_materials(content.get("materials"))
    except ApiError as exc:
        problems.append(exc.message)
        materials = []
    extra = [m for m in materials if m.casefold() not in declared]
    if extra:
        problems.append("Hay materiales que no declaraste: %s." % ", ".join(extra))

    activities_in = content.get("activities")
    activities: List[Dict[str, Any]] = []
    if not isinstance(activities_in, list) or not activities_in:
        problems.append("La sesión necesita al menos una actividad.")
    elif len(activities_in) > MAX_ACTIVITIES:
        problems.append("La sesión admite como máximo %d actividades." % MAX_ACTIVITIES)
    else:
        used_ids = set()
        for index, raw in enumerate(activities_in, start=1):
            label = "Actividad %d" % index
            if not isinstance(raw, dict):
                problems.append("%s no tiene formato válido." % label)
                continue
            minutes = raw.get("minutes")
            if isinstance(minutes, str) and minutes.strip().isdigit():
                minutes = int(minutes.strip())
            if not _is_int(minutes) or minutes <= 0:
                problems.append("%s: los minutos deben ser un entero mayor que 0." % label)
                minutes = 0
            try:
                act_title = clean_text(raw.get("title"), label + " (título)", required=True, max_len=MAX_SHORT)
                act_desc = clean_text(raw.get("description"), label + " (descripción)", required=True)
            except ApiError as exc:
                problems.append(exc.message)
                act_title = act_desc = ""
            refs_in = raw.get("references", [])
            refs: List[str] = []
            if not isinstance(refs_in, list):
                problems.append("%s: las referencias deben ser una lista." % label)
            else:
                for ref in refs_in:
                    if ref not in fragment_ids:
                        problems.append("%s cita una referencia que no existe: %s." % (label, ref))
                    elif ref not in refs:
                        refs.append(ref)
            act_id = raw.get("id") if isinstance(raw.get("id"), str) and raw.get("id") else "a%d" % index
            if act_id in used_ids:
                act_id = "a%d" % index
            used_ids.add(act_id)
            activities.append(
                {"id": act_id, "title": act_title, "minutes": minutes, "description": act_desc, "references": refs}
            )
        total = sum(a["minutes"] for a in activities)
        if total != context["durationMinutes"]:
            problems.append(
                "Los tiempos suman %d min y la clase dura %d min." % (total, context["durationMinutes"])
            )

    if problems:
        raise ApiError(422, "invalid_lesson", "La sesión no es válida: " + " ".join(problems), problems)

    used_refs: List[str] = []
    for activity in activities:
        for ref in activity["references"]:
            if ref not in used_refs:
                used_refs.append(ref)
    sources = [
        {"id": ref, "text": fragments_by_id[ref]["text"], "moduleId": module["id"], "moduleVersion": module["version"]}
        for ref in sorted(used_refs)
    ]
    return {
        "title": title,
        "purpose": purpose,
        "grade": context["grade"],
        "durationMinutes": context["durationMinutes"],
        "materials": materials,
        "activities": activities,
        "expectedEvidence": evidence,
        "sources": sources,
        "moduleSourceLabel": module["sourceLabel"],
    }


def parse_declared_date(value: Any) -> str:
    if not isinstance(value, str):
        raise ApiError(422, "invalid_date", "Indica la fecha en formato AAAA-MM-DD.", {"field": "declaredDate"})
    try:
        parsed = date.fromisoformat(value.strip())
    except ValueError:
        raise ApiError(422, "invalid_date", "Indica una fecha válida en formato AAAA-MM-DD.", {"field": "declaredDate"})
    return parsed.isoformat()


def validate_user_id(value: Optional[str]) -> str:
    if value is None or not USER_ID_RE.match(value):
        raise ApiError(400, "invalid_user", "Identificador de usuario de demostración no válido.")
    return value


def deep_copy(value: Any) -> Any:
    return copy.deepcopy(value)
