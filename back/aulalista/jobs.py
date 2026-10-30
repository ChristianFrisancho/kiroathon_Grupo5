"""Procesamiento de trabajos de /jobs, compartido por el worker Lambda y el worker local (hilo del servidor).

`process_job` es idempotente: si el trabajo ya está en «done» no lo repite, así una entrega duplicada del
evento asíncrono de Lambda no cambia el resultado.
"""
from __future__ import annotations

from typing import Any, Callable, Optional


def compute_output(value: str) -> str:
    """Contrato de la insignia: la entrada invertida carácter por carácter."""
    return value[::-1]


def process_job(repo: Any, job_id: str, now: Callable[[], str]) -> Optional[str]:
    job = repo.get_job(job_id)
    if job is None:
        return None
    if job["status"] == "done":
        return "done"
    try:
        repo.update_job(job_id, "running", now())
        repo.update_job(job_id, "done", now(), output=compute_output(job["input"]))
        return "done"
    except Exception as exc:  # noqa: BLE001 - se persiste el fallo para que GET no quede en «queued»
        repo.update_job(job_id, "failed", now(), error=type(exc).__name__)
        return "failed"
