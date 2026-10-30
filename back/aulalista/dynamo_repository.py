"""Persistencia en DynamoDB (tabla `ItemsTable` del template). Mismos métodos que `Repository` (SQLite).

Diseño de tabla única para la demo: `pk` = tipo de entidad, `sk` = id, `doc` = JSON del registro.
Cada listado consulta (Query) una sola partición y pagina con LastEvaluatedKey; nunca se queda en la
primera página. Las lecturas son consistentes (ConsistentRead) para que lo recién
guardado se recupere de inmediato. Con volumen real habría que añadir índices por dueño y por sesión.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

SESSION = "SESSION"
VERSION = "VERSION"
RECORD = "RECORD"
EXPERIENCE = "EXPERIENCE"
RATING = "RATING"
COMMENT = "COMMENT"
PREFERENCES = "PREFERENCES"
ITEM = "ITEM"
JOB = "JOB"


class DynamoRepository:
    def __init__(self, table: Any):
        self.table = table

    @classmethod
    def from_table_name(cls, table_name: str) -> "DynamoRepository":
        if not table_name:
            raise RuntimeError("Falta la variable TABLE_NAME para usar DynamoDB.")
        import boto3  # disponible en el runtime de Lambda

        return cls(boto3.resource("dynamodb").Table(table_name))

    def close(self) -> None:
        pass

    # ---- utilidades -------------------------------------------------
    def _put(self, kind: str, key: str, doc: Dict[str, Any], **extra: Any) -> None:
        item = {"pk": kind, "sk": key, "doc": json.dumps(doc, ensure_ascii=False)}
        item.update(extra)
        self.table.put_item(Item=item)

    def _get(self, kind: str, key: str) -> Optional[Dict[str, Any]]:
        found = self.table.get_item(Key={"pk": kind, "sk": key}, ConsistentRead=True).get("Item")
        return json.loads(found["doc"]) if found else None

    def _all(self, kind: str) -> List[Dict[str, Any]]:
        docs: List[Dict[str, Any]] = []
        args: Dict[str, Any] = {
            "KeyConditionExpression": "pk = :pk",
            "ExpressionAttributeValues": {":pk": kind},
            # Lectura consistente: lo recién guardado aparece en la siguiente lectura (guardar → recuperar).
            "ConsistentRead": True,
        }
        while True:
            page = self.table.query(**args)
            docs.extend(json.loads(item["doc"]) for item in page.get("Items", []))
            last = page.get("LastEvaluatedKey")
            if not last:
                return docs
            args["ExclusiveStartKey"] = last

    # ---- sesiones y versiones --------------------------------------
    def create_session(self, session: Dict[str, Any], version: Dict[str, Any]) -> None:
        # Primero la versión: si falla la sesión, no queda una sesión sin versión.
        self._put(VERSION, version["id"], version)
        self._put(SESSION, session["id"], {**session, "currentVersionId": version["id"]})

    def add_version(self, version: Dict[str, Any], title: str, updated_at: str) -> None:
        self._put(VERSION, version["id"], version)
        session = self._get(SESSION, version["sessionId"])
        if session is None:
            raise RuntimeError("La sesión no existe.")
        session.update({"currentVersionId": version["id"], "title": title, "updatedAt": updated_at})
        self._put(SESSION, session["id"], session)

    def set_review_status(self, version_id: str, status: str) -> None:
        version = self._get(VERSION, version_id)
        if version is not None:
            version["reviewStatus"] = status
            self._put(VERSION, version_id, version)

    def touch_session(self, session_id: str, updated_at: str) -> None:
        session = self._get(SESSION, session_id)
        if session is not None:
            session["updatedAt"] = updated_at
            self._put(SESSION, session_id, session)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._get(SESSION, session_id)

    def list_sessions(self, owner_id: str) -> List[Dict[str, Any]]:
        mine = [s for s in self._all(SESSION) if s["ownerId"] == owner_id]
        mine.sort(key=lambda s: s["id"])
        mine.sort(key=lambda s: s["updatedAt"], reverse=True)
        return mine

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        return self._all(SESSION)

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        return self._get(VERSION, version_id)

    def list_versions(self, session_id: str) -> List[Dict[str, Any]]:
        return sorted((v for v in self._all(VERSION) if v["sessionId"] == session_id), key=lambda v: v["number"])

    # ---- registros de aplicación -----------------------------------
    def add_record(self, record: Dict[str, Any]) -> None:
        self._put(RECORD, record["id"], {**record, "nextAdjustment": record.get("nextAdjustment") or ""})

    def list_records(self, session_id: str) -> List[Dict[str, Any]]:
        rows = [r for r in self._all(RECORD) if r["sessionId"] == session_id]
        return sorted(rows, key=lambda r: (r["createdAt"], r["id"]))

    # ---- experiencias ------------------------------------------------
    def add_experience(self, e: Dict[str, Any]) -> None:
        doc = {**e, "versionId": e["id"], "observation": e.get("observation") or "",
               "improvement": e.get("improvement") or ""}
        self._put(EXPERIENCE, e["id"], doc)

    def get_experience(self, experience_id: str) -> Optional[Dict[str, Any]]:
        return self._get(EXPERIENCE, experience_id)

    def find_experience_by_source(self, author_id: str, source_version_id: str) -> Optional[Dict[str, Any]]:
        return next((e for e in self._all(EXPERIENCE)
                     if e["authorId"] == author_id and e.get("sourceVersionId") == source_version_id), None)

    def list_experiences(self) -> List[Dict[str, Any]]:
        return sorted(self._all(EXPERIENCE), key=lambda e: (e["createdAt"], e["id"]))

    # ---- valoraciones y comentarios ---------------------------------
    def upsert_rating(self, rating: Dict[str, Any]) -> bool:
        """La clave es versión#revisor: una sola valoración activa por persona y versión."""
        key = "%s#%s" % (rating["versionId"], rating["reviewerId"])
        existing = self._get(RATING, key)
        if existing:
            existing.update({k: rating[k] for k in ("clarity", "feasibility", "coherence", "observation",
                                                    "context", "whatToKeep", "whatToChange", "updatedAt")})
            self._put(RATING, key, existing)
            return False
        self._put(RATING, key, dict(rating))
        return True

    def list_ratings(self, version_id: str) -> List[Dict[str, Any]]:
        rows = [r for r in self._all(RATING) if r["versionId"] == version_id]
        return sorted(rows, key=lambda r: (r["createdAt"], r["id"]))

    def add_comment(self, comment: Dict[str, Any]) -> None:
        self._put(COMMENT, comment["id"], comment)

    def list_comments(self, version_id: str) -> List[Dict[str, Any]]:
        rows = [c for c in self._all(COMMENT) if c["versionId"] == version_id]
        return sorted(rows, key=lambda c: (c["createdAt"], c["id"]))

    # ---- preferencias ------------------------------------------------
    def get_preferences(self, owner_id: str) -> Optional[Dict[str, Any]]:
        return self._get(PREFERENCES, owner_id)

    def set_preferences(self, owner_id: str, data: Dict[str, Any]) -> None:
        self._put(PREFERENCES, owner_id, data)

    # ---- contratos de insignias --------------------------------------
    def add_item(self, item_id: str, value: str, created_at: str) -> None:
        self._put(ITEM, item_id, {"id": item_id, "value": value, "createdAt": created_at})

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self._get(ITEM, item_id)

    def list_items(self) -> List[Dict[str, Any]]:
        return sorted(self._all(ITEM), key=lambda i: (i["createdAt"], i["id"]))

    def add_job(self, job_id: str, input_value: str, now: str) -> None:
        self._put(JOB, job_id, {"jobId": job_id, "input": input_value, "status": "queued", "output": None,
                                "error": None, "createdAt": now, "updatedAt": now})

    def update_job(self, job_id: str, status: str, now: str, output: Optional[str] = None,
                   error: Optional[str] = None) -> None:
        job = self._get(JOB, job_id) or {"jobId": job_id, "input": "", "createdAt": now}
        job.update({"status": status, "output": output, "error": error, "updatedAt": now})
        self._put(JOB, job_id, job)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._get(JOB, job_id)
