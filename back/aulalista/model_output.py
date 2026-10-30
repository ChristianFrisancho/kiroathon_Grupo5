"""Validación de respuestas del modelo antes de normalizar.

Capas: entrada inválida del docente → 4xx sin llamar al modelo (validators.py); respuesta malformada o
incompleta del modelo → GeneratorError → 502 generation_failed, sin guardar nada (este módulo);
indisponibilidad temporal → respaldo local rotulado (bedrock.py); resultado válido → normalización
controlada y validación final del servidor (validators.validate_lesson_content).
Límites alineados con validators.py: títulos 200, textos 2000, entre 1 y 12 actividades.
"""
from typing import Any, Dict

from .generator import GeneratorError

TITLE_LIMIT = 200
TEXT_LIMIT = 2000
MAX_ACTIVITIES = 12


def _fail(message: str) -> None:
    raise GeneratorError("El modelo devolvió una respuesta inválida: " + message)


def _required_text(obj: Dict[str, Any], key: str, label: str, limit: int) -> str:
    value = obj.get(key)
    if not isinstance(value, str):
        _fail("%s debe ser texto." % label)
    text = value.strip()
    if not text:
        _fail("falta %s." % label)
    if len(text) > limit:
        _fail("%s excede el límite de longitud." % label)
    return text


def validate_model_payload(data: Any) -> Dict[str, Any]:
    """Rechaza estructura defectuosa; no inventa contenido faltante ni modifica la entrada."""
    if not isinstance(data, dict):
        _fail("se esperaba un objeto JSON.")
    _required_text(data, "title", "el título", TITLE_LIMIT)
    _required_text(data, "purpose", "el propósito", TEXT_LIMIT)
    _required_text(data, "expectedEvidence", "la evidencia esperada", TEXT_LIMIT)
    activities = data.get("activities")
    if not isinstance(activities, list):
        _fail("activities debe ser una lista.")
    if not 1 <= len(activities) <= MAX_ACTIVITIES:
        _fail("se requieren entre una y doce actividades.")
    for index, activity in enumerate(activities, start=1):
        label = "la actividad %d" % index
        if not isinstance(activity, dict):
            _fail("%s debe ser un objeto." % label)
        _required_text(activity, "title", "el título de %s" % label, TITLE_LIMIT)
        _required_text(activity, "description", "la descripción de %s" % label, TEXT_LIMIT)
        minutes = activity.get("minutes")
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
            _fail("los minutos de %s deben ser un entero positivo." % label)
        references = activity.get("references")
        if not isinstance(references, list):
            _fail("las referencias de %s deben ser una lista." % label)
        if any(not isinstance(ref, str) or not ref.strip() for ref in references):
            _fail("las referencias de %s deben contener identificadores." % label)
    return data


def converse_text(response: Any) -> str:
    """Extrae texto de una respuesta Converse con estructura válida y terminada normalmente."""
    if not isinstance(response, dict):
        _fail("Converse no devolvió un objeto.")
    reason = response.get("stopReason")
    if reason not in ("end_turn", "stop_sequence"):
        _fail("el modelo no terminó normalmente (stopReason=%s)." % reason)
    output = response.get("output")
    if not isinstance(output, dict):
        _fail("falta output en Converse.")
    message = output.get("message")
    if not isinstance(message, dict):
        _fail("falta el mensaje de Converse.")
    if message.get("role") != "assistant":
        _fail("el mensaje no corresponde al asistente.")
    blocks = message.get("content")
    if not isinstance(blocks, list) or not blocks:
        _fail("el mensaje no contiene bloques de respuesta.")
    pieces = []
    for block in blocks:
        if not isinstance(block, dict):
            _fail("hay un bloque de respuesta inválido.")
        if "text" in block:
            if not isinstance(block["text"], str):
                _fail("el contenido textual no es una cadena.")
            pieces.append(block["text"])
    text = "".join(pieces).strip()
    if not text:
        _fail("el modelo no devolvió texto.")
    return text
