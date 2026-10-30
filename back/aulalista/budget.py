"""Presupuesto de tiempo por petición.

El adaptador Lambda fija un plazo con `context.get_remaining_time_in_millis()` menos una reserva para validar,
guardar y responder. El generador de Bedrock lo consulta antes de cada intento. Fuera de Lambda no hay plazo
externo y el generador usa su presupuesto propio.
"""
from __future__ import annotations

import time
from contextvars import ContextVar
from typing import Optional

# Reserva para validar, persistir y serializar la respuesta después de llamar al modelo.
RESPONSE_RESERVE_SECONDS = 2.5

_deadline: ContextVar[Optional[float]] = ContextVar("aulalista_deadline", default=None)


def set_deadline_from_remaining_ms(remaining_ms: Optional[int], now: Optional[float] = None) -> None:
    if remaining_ms is None:
        _deadline.set(None)
        return
    start = time.monotonic() if now is None else now
    _deadline.set(start + remaining_ms / 1000.0 - RESPONSE_RESERVE_SECONDS)


def set_deadline(deadline: Optional[float]) -> None:
    _deadline.set(deadline)


def deadline() -> Optional[float]:
    return _deadline.get()
