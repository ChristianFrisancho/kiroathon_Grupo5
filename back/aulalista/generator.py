"""Interfaz de generación de sesiones.

Fase 1: `LocalSimulatedGenerator` produce una plantilla determinista a partir del módulo. NO es Bedrock
y la API lo declara en cada respuesta (`generatedBy.isBedrock = false`).
`BedrockGenerator` (bedrock.py) implementa la misma interfaz con Amazon Bedrock (API Converse).
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

from .errors import ApiError


class GeneratorError(Exception):
    """El motor no pudo producir una sesión (servicio caído, tiempo agotado, salida ilegible)."""


def split_minutes(total: int, weights: Sequence[int]) -> List[int]:
    """Reparte `total` en enteros proporcionales a `weights` (método del mayor resto). La suma es exacta."""
    weight_sum = sum(weights)
    raw = [total * w / weight_sum for w in weights]
    base = [int(x) for x in raw]
    leftover = total - sum(base)
    order = sorted(range(len(weights)), key=lambda i: (raw[i] - base[i]), reverse=True)
    for i in order[:leftover]:
        base[i] += 1
    return base


class Generator:
    name = "base"
    is_bedrock = False
    label = ""

    def info(self) -> Dict[str, Any]:
        return {"engine": self.name, "isBedrock": self.is_bedrock, "label": self.label}

    def generate(self, module: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def adapt(
        self, module: Dict[str, Any], context: Dict[str, Any], experience: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def summarize(self, experience: Dict[str, Any], rating_summary: Dict[str, Any], ratings: List[Dict[str, Any]],
                  comments: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError


class LocalSimulatedGenerator(Generator):
    name = "local-simulado"
    is_bedrock = False
    label = "Salida de ejemplo generada localmente por una plantilla. No es Amazon Bedrock."

    _PLAN = (
        ("Presentación en tres pasos", ("M1",), 2),
        ("Hablar y escuchar por parejas", ("M1",), 3),
        ("Parafrasear y confirmar", ("M2",), 3),
        ("Preguntas de aclaración y cierre", ("M3",), 2),
    )

    def _fragment_ids(self, module: Dict[str, Any]) -> List[str]:
        return [f["id"] for f in module["fragments"]]

    def _plan(self, module: Dict[str, Any]) -> List[Any]:
        available = set(self._fragment_ids(module))
        plan = [(t, tuple(r for r in refs if r in available), w) for t, refs, w in self._PLAN]
        if all(refs for _, refs, _ in plan):
            return plan
        # Módulo distinto del ejemplo: una actividad por fragmento.
        return [("Actividad sobre %s" % f["id"], (f["id"],), 1) for f in module["fragments"]]

    def generate(self, module: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        plan = self._plan(module)
        minutes = split_minutes(context["durationMinutes"], [w for _, _, w in plan])
        materials = context["materials"]
        has_board = any(m.casefold() in ("pizarra", "pizarrón") for m in materials)
        has_paper = any(m.casefold() in ("papel", "hojas", "cuaderno") for m in materials)
        activities = []
        for index, ((title, refs, _), mins) in enumerate(zip(plan, minutes), start=1):
            if index == 1:
                how = (
                    "Escribir los tres pasos en la pizarra y mostrar un ejemplo con dos estudiantes."
                    if has_board
                    else "Explicar oralmente los tres pasos y mostrar un ejemplo con dos estudiantes."
                )
            elif index == 2:
                how = "Formar parejas; quien habla cuenta una experiencia breve y quien escucha no interrumpe. Luego se intercambian los papeles."
            elif index == 3:
                how = (
                    "Quien escucha anota en una hoja una palabra clave y dice con sus palabras lo entendido; después pregunta si es correcto."
                    if has_paper
                    else "Quien escucha dice con sus palabras lo entendido y pregunta si es correcto."
                )
            else:
                how = "Cada estudiante formula una pregunta de aclaración y explica una idea que escuchó, y cómo comprobó que la entendió."
            if index == 1 and context.get("notes"):
                how += " Indicación del docente considerada: «%s»." % context["notes"]
            activities.append(
                {
                    "id": "a%d" % index,
                    "title": title,
                    "minutes": mins,
                    "description": how,
                    "references": list(refs),
                }
            )
        return {
            "title": "%s: sesión de %d minutos" % (module["title"], context["durationMinutes"]),
            "purpose": "Practicar «%s» con %s, usando únicamente los materiales declarados."
            % (module["title"].lower(), context["grade"].lower()),
            "grade": context["grade"],
            "durationMinutes": context["durationMinutes"],
            "materials": list(materials),
            "activities": activities,
            "expectedEvidence": "Cada estudiante explica con sus palabras una idea que escuchó y cómo comprobó su comprensión.",
        }

    def adapt(
        self, module: Dict[str, Any], context: Dict[str, Any], experience: Dict[str, Any]
    ) -> Dict[str, Any]:
        source = experience["content"]
        old = [a["minutes"] for a in source["activities"]]
        minutes = split_minutes(context["durationMinutes"], old)
        activities = []
        for index, (act, mins) in enumerate(zip(source["activities"], minutes)):
            description = act["description"]
            if index == 0 and experience.get("improvement"):
                description += " Mejora incorporada desde la experiencia compartida: %s" % experience["improvement"]
            activities.append(
                {
                    "id": act["id"],
                    "title": act["title"],
                    "minutes": mins,
                    "description": description,
                    "references": list(act["references"]),
                }
            )
        title = source["title"]
        return {
            "title": "Adaptación de: %s" % title,
            "purpose": source["purpose"],
            "grade": context["grade"],
            "durationMinutes": context["durationMinutes"],
            "materials": list(context["materials"]),
            "activities": activities,
            "expectedEvidence": source["expectedEvidence"],
        }

    def summarize(self, experience, rating_summary, ratings, comments):
        lines: List[str] = []
        if rating_summary["completeCount"] == 0:
            lines.append("Todavía no hay valoraciones completas, así que no hay acuerdos que resumir.")
        else:
            means = {k: v for k, v in rating_summary["criteriaMeans"].items() if v is not None}
            best = max(means, key=means.get)
            worst = min(means, key=means.get)
            lines.append(
                "Con %d valoraciones completas, el criterio mejor valorado fue «%s» (%s) y el menor «%s» (%s)."
                % (
                    rating_summary["completeCount"],
                    _LABELS[best], _fmt(means[best]), _LABELS[worst], _fmt(means[worst]),
                )
            )
        improvements = [r["whatToChange"] for r in ratings if r.get("whatToChange")]
        if improvements:
            lines.append("Cambios sugeridos por quienes la usaron: " + " | ".join(improvements))
        if comments:
            lines.append("Comentarios de diseño de lectores: %d (no cuentan como valoraciones de uso)." % len(comments))
        lines.append("Resumen calculado localmente a partir de los registros; no es una opinión de Amazon Bedrock.")
        return {"text": "\n".join(lines), "generatedBy": self.info()}


_LABELS = {
    "clarity": "claridad",
    "feasibility": "viabilidad",
    "coherence": "coherencia",
    "observation": "observación del aprendizaje",
}


def _fmt(value: float) -> str:
    return ("%.1f" % value).replace(".", ",")




def build_generator(kind: str, model_id: str = "") -> Generator:
    if kind == "local":
        return LocalSimulatedGenerator()
    if kind == "bedrock":
        from .bedrock import BedrockGenerator  # Amazon Bedrock (API Converse)

        return BedrockGenerator(model_id=model_id)
    raise ApiError(500, "bad_config", "Generador no reconocido: %s" % kind)
