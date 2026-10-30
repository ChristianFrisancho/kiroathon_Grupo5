"""Valoración de uso 1-5 por versión. Cálculo determinista, sin IA."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Optional

from .errors import ApiError

CRITERIA = ("clarity", "feasibility", "coherence", "observation")
CRITERIA_LABELS = {
    "clarity": "Claridad de instrucciones",
    "feasibility": "Viabilidad con tiempo y materiales declarados",
    "coherence": "Coherencia con el propósito",
    "observation": "Apoyo para observar la comprensión del grupo",
}
FEW_RATINGS_THRESHOLD = 5  # umbral de interfaz, no garantía estadística


def parse_values(payload: Dict[str, Any]) -> Dict[str, Optional[int]]:
    """Cada criterio es un entero 1-5 o None («No puedo valorarlo»). Un criterio ausente es None, nunca 0."""
    values: Dict[str, Optional[int]] = {}
    for name in CRITERIA:
        raw = payload.get(name)
        if raw is None:
            values[name] = None
            continue
        if isinstance(raw, bool) or not isinstance(raw, int) or not 1 <= raw <= 5:
            raise ApiError(
                422,
                "invalid_rating",
                "«%s» debe ser un número del 1 al 5 o «No puedo valorarlo»." % CRITERIA_LABELS[name],
                {"field": name},
            )
        values[name] = raw
    return values


def is_complete(values: Dict[str, Optional[int]]) -> bool:
    return all(values.get(name) is not None for name in CRITERIA)


def rating_mean(values: Dict[str, Optional[int]]) -> Optional[Fraction]:
    if not is_complete(values):
        return None
    return Fraction(sum(values[name] for name in CRITERIA), len(CRITERIA))  # type: ignore[misc]


def round_one_decimal(value: Fraction) -> float:
    decimal = Decimal(value.numerator) / Decimal(value.denominator)
    return float(decimal.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def summarize(ratings: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Media de medias de valoraciones completas. Las parciales se cuentan aparte y no entran en la media."""
    complete: List[Fraction] = []
    partial = 0
    latest = None
    contexts: List[str] = []
    per_criterion: Dict[str, List[int]] = {name: [] for name in CRITERIA}
    for rating in ratings:
        values = {name: rating.get(name) for name in CRITERIA}
        mean = rating_mean(values)
        if mean is None:
            partial += 1
        else:
            complete.append(mean)
            for name in CRITERIA:
                per_criterion[name].append(values[name])  # type: ignore[arg-type]
        stamp = rating.get("updatedAt") or rating.get("createdAt")
        if stamp and (latest is None or stamp > latest):
            latest = stamp
        context = rating.get("context")
        if context and context not in contexts:
            contexts.append(context)
    count = len(complete)
    if count == 0:
        average = None
        label = "Sin valoración general"
    else:
        average = round_one_decimal(sum(complete, Fraction(0)) / count)
        label = "Pocas valoraciones" if count < FEW_RATINGS_THRESHOLD else ""
    criteria_means = {
        name: (round_one_decimal(Fraction(sum(vals), len(vals))) if vals else None)
        for name, vals in per_criterion.items()
    }
    return {
        "average": average,
        "completeCount": count,
        "partialCount": partial,
        "label": label,
        "contexts": contexts,
        "lastRatedAt": latest,
        "criteriaMeans": criteria_means,
    }
