"""Worker Lambda de /jobs (invocación asíncrona desde la API con {"jobId": ...}).

Solo construye el repositorio de DynamoDB: no inicializa el generador de Bedrock ni el servicio completo.
Es idempotente: si el trabajo ya está en «done», una entrega repetida no lo procesa de nuevo.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from aulalista.jobs import process_job
from aulalista.service import utc_now

_repo: Optional[Any] = None


def get_repo() -> Any:
    global _repo
    if _repo is None:
        from aulalista.dynamo_repository import DynamoRepository

        _repo = DynamoRepository.from_table_name(os.environ.get("TABLE_NAME", ""))
    return _repo


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    job_id = event.get("jobId") if isinstance(event, dict) else None
    if not isinstance(job_id, str) or not job_id:
        return {"status": "ignored", "reason": "missing jobId"}
    status = process_job(get_repo(), job_id, utc_now)
    return {"jobId": job_id, "status": status or "not_found"}
