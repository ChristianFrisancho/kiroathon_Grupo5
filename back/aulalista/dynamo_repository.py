"""Persistencia en DynamoDB (tabla `ItemsTable`, claves `pk`/`sk`, atributo `doc` con el JSON del registro).

Patrones de acceso (sin índices secundarios, lecturas consistentes donde guardar → recuperar lo necesita):

| Dato | pk | sk |
|---|---|---|
| Sesión (con resumen) | SESSION#<id> | META |
| Versión | SESSION#<id> | VERSION#<versionId> |
| Número de versión (unicidad) | SESSION#<id> | VNUM#<000002> |
| Registro de aplicación | SESSION#<id> | RECORD#<createdAt>#<id> |
| Sesiones de un docente | USER#<owner> | SESSION#<id> (copia del resumen) |
| Borrador emitido por el servidor | DRAFT#<id> | META (atributo `ttl`) |
| Clave de operación | OP#<owner> | <clave> |
| Experiencia (feed) | EXPERIENCE | <id> |
| Versión ya compartida (unicidad) | SHARED#<autor> | <versionId> |
| Adaptación de una experiencia | ADAPTED#<experienceId> | <sessionId> |
| Valoración | RATINGS#<experienceId> | <revisor> |
| Comentario | COMMENTS#<experienceId> | <createdAt>#<id> |
| Preferencias | PREFERENCES | <owner> |
| Ítem / índice temporal | ITEM / ITEMS_BY_TIME | <id> / <createdAt>#<id> |
| Trabajo | JOB | <jobId> |

Escrituras que deben ser atómicas usan TransactWriteItems. El resumen de la sesión (META) solo se reemplaza con
la condición `doc = <valor leído>`, así dos guardados concurrentes no producen versiones [1, 2, 2] y una
actualización de fecha no restaura una versión vigente antigua.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .errors import AlreadyExists, VersionConflict

MIGRATION_KEY = ("MIGRATION", "layout-v2")
OPTIMISTIC_RETRIES = 4


def _s(value: str) -> Dict[str, str]:
    return {"S": value}


def transaction_item(pk: str, sk: str, doc: Any, **extra: Dict[str, str]) -> Dict[str, Any]:
    item = {"pk": _s(pk), "sk": _s(sk), "doc": _s(json.dumps(doc, ensure_ascii=False))}
    item.update(extra)
    return item


def _error_code(exc: BaseException) -> str:
    response = getattr(exc, "response", None)
    return str(response.get("Error", {}).get("Code", "")) if isinstance(response, dict) else ""


def _cancel_codes(exc: BaseException) -> List[str]:
    response = getattr(exc, "response", None) or {}
    reasons = response.get("CancellationReasons") or []
    return [str(r.get("Code", "None")) for r in reasons]


def _is_condition_failure(exc: BaseException) -> bool:
    code = _error_code(exc)
    if code == "ConditionalCheckFailedException":
        return True
    return code == "TransactionCanceledException" and "ConditionalCheckFailed" in _cancel_codes(exc)


def _summary(session: Dict[str, Any]) -> Dict[str, Any]:
    keys = ("id", "ownerId", "title", "moduleId", "moduleVersion", "provenance", "currentVersionId", "createdAt",
            "updatedAt", "currentVersionNumber", "reviewStatus", "versionCount", "recordCount", "documentedVersions")
    return {k: session.get(k) for k in keys}


def _documents(version: Dict[str, Any]) -> int:
    return 1 if version["number"] > 1 and len((version.get("reason") or "").strip()) >= 10 else 0


class DynamoRepository:
    def __init__(self, client: Any, table_name: str, now_epoch=time.time):
        self.client = client
        self.table = table_name
        self._now_epoch = now_epoch

    @classmethod
    def from_table_name(cls, table_name: str) -> "DynamoRepository":
        if not table_name:
            raise RuntimeError("Falta la variable TABLE_NAME para usar DynamoDB.")
        import boto3  # disponible en el runtime de Lambda

        return cls(boto3.client("dynamodb"), table_name)

    def close(self) -> None:
        pass

    # ---- utilidades -------------------------------------------------------
    def _get_raw(self, pk: str, sk: str) -> Optional[str]:
        found = self.client.get_item(TableName=self.table, Key={"pk": _s(pk), "sk": _s(sk)},
                                     ConsistentRead=True).get("Item")
        return found["doc"]["S"] if found else None

    def _get(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        raw = self._get_raw(pk, sk)
        return json.loads(raw) if raw is not None else None

    def _put(self, pk: str, sk: str, doc: Any, if_new: bool = False, **extra: Dict[str, str]) -> None:
        args: Dict[str, Any] = {"TableName": self.table, "Item": transaction_item(pk, sk, doc, **extra)}
        if if_new:
            args["ConditionExpression"] = "attribute_not_exists(pk)"
        self.client.put_item(**args)

    def _query(self, pk: str, prefix: Optional[str] = None, newest_first: bool = False,
               limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Consulta una sola partición y pagina con LastEvaluatedKey hasta `limit` (o todas las páginas)."""
        args: Dict[str, Any] = {
            "TableName": self.table, "ConsistentRead": True, "ScanIndexForward": not newest_first,
            "KeyConditionExpression": "pk = :pk",
            "ExpressionAttributeValues": {":pk": _s(pk)},
        }
        if prefix is not None:
            args["KeyConditionExpression"] = "pk = :pk AND begins_with(sk, :prefix)"
            args["ExpressionAttributeValues"][":prefix"] = _s(prefix)
        docs: List[Dict[str, Any]] = []
        while True:
            if limit is not None:
                args["Limit"] = limit - len(docs)
            page = self.client.query(**args)
            docs.extend(json.loads(item["doc"]["S"]) for item in page.get("Items", []))
            last = page.get("LastEvaluatedKey")
            if not last or (limit is not None and len(docs) >= limit):
                return docs
            args["ExclusiveStartKey"] = last

    def _put_action(self, pk: str, sk: str, doc: Any, condition: Optional[Tuple[str, Dict[str, Any]]] = None,
                    **extra: Dict[str, str]) -> Dict[str, Any]:
        put: Dict[str, Any] = {"TableName": self.table, "Item": transaction_item(pk, sk, doc, **extra)}
        if condition == "new":
            put["ConditionExpression"] = "attribute_not_exists(pk)"
        elif condition is not None:
            put["ConditionExpression"] = "#doc = :expected"
            put["ExpressionAttributeNames"] = {"#doc": "doc"}
            put["ExpressionAttributeValues"] = {":expected": _s(condition)}
        return {"Put": put}

    def _transact(self, actions: List[Dict[str, Any]]) -> None:
        self.client.transact_write_items(TransactItems=actions)

    def _session_actions(self, session: Dict[str, Any], expected_raw: Optional[str]) -> List[Dict[str, Any]]:
        sid = session["id"]
        return [
            self._put_action("SESSION#" + sid, "META", session, "new" if expected_raw is None else expected_raw),
            self._put_action("USER#" + session["ownerId"], "SESSION#" + sid, _summary(session)),
        ]

    # ---- sesiones y versiones ---------------------------------------------
    def create_session(self, session: Dict[str, Any], version: Dict[str, Any]) -> None:
        sid = session["id"]
        doc = {**session, "currentVersionId": version["id"], "currentVersionNumber": version["number"],
               "reviewStatus": version["reviewStatus"], "versionCount": 1, "recordCount": 0,
               "documentedVersions": 0}
        actions = [
            self._put_action("SESSION#" + sid, "VERSION#" + version["id"], version, "new"),
            self._put_action("SESSION#" + sid, "VNUM#%06d" % version["number"], {"versionId": version["id"]}, "new"),
            *self._session_actions(doc, None),
        ]
        experience_id = (session.get("provenance") or {}).get("experienceId")
        if experience_id:
            actions.append(self._put_action("ADAPTED#" + experience_id, sid, {"ownerId": session["ownerId"]}))
        self._transact(actions)

    def add_version(self, version: Dict[str, Any], title: str, updated_at: str, expected_parent_id: str) -> None:
        sid = version["sessionId"]
        raw = self._get_raw("SESSION#" + sid, "META")
        if raw is None:
            raise VersionConflict()
        session = json.loads(raw)
        if session["currentVersionId"] != expected_parent_id:
            raise VersionConflict()
        next_session = {
            **session, "currentVersionId": version["id"], "title": title, "updatedAt": updated_at,
            "currentVersionNumber": version["number"], "reviewStatus": version["reviewStatus"],
            "versionCount": session.get("versionCount", 0) + 1,
            "documentedVersions": session.get("documentedVersions", 0) + _documents(version),
        }
        try:
            self._transact([
                self._put_action("SESSION#" + sid, "VERSION#" + version["id"], version, "new"),
                self._put_action("SESSION#" + sid, "VNUM#%06d" % version["number"], {"versionId": version["id"]}, "new"),
                *self._session_actions(next_session, raw),
            ])
        except Exception as exc:  # noqa: BLE001
            if _is_condition_failure(exc):
                raise VersionConflict()
            raise

    def _update_session(self, sid: str, mutate, extra_actions) -> None:
        """Lectura → cambio → escritura condicionada al valor leído, con reintentos si otro la cambió antes."""
        for _ in range(OPTIMISTIC_RETRIES):
            raw = self._get_raw("SESSION#" + sid, "META")
            if raw is None:
                raise KeyError(sid)
            session = mutate(json.loads(raw))
            actions = extra_actions(session) + self._session_actions(session, raw)
            try:
                self._transact(actions)
                return
            except Exception as exc:  # noqa: BLE001
                if not _is_condition_failure(exc):
                    raise
        raise VersionConflict()

    def set_review_status(self, session_id: str, version_id: str, status: str, updated_at: str) -> None:
        def mutate(session):
            session["updatedAt"] = updated_at
            if session["currentVersionId"] == version_id:
                session["reviewStatus"] = status
            return session

        def extra(_session):
            raw_version = self._get_raw("SESSION#" + session_id, "VERSION#" + version_id)
            version = json.loads(raw_version)
            version["reviewStatus"] = status
            return [self._put_action("SESSION#" + session_id, "VERSION#" + version_id, version, raw_version)]

        self._update_session(session_id, mutate, extra)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._get("SESSION#" + session_id, "META")

    def list_sessions(self, owner_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Una consulta a la partición del docente; el resumen ya trae versión vigente y conteos."""
        rows = self._query("USER#" + owner_id, prefix="SESSION#")
        rows.sort(key=lambda s: s["id"])
        rows.sort(key=lambda s: s["updatedAt"], reverse=True)
        return rows[:limit] if limit is not None else rows

    def count_sessions(self, owner_id: str) -> int:
        return len(self._query("USER#" + owner_id, prefix="SESSION#"))

    def count_adaptations(self, experience_ids: Iterable[str], exclude_owner: str) -> int:
        return sum(1 for eid in experience_ids for m in self._query("ADAPTED#" + eid)
                   if m.get("ownerId") != exclude_owner)

    def get_version(self, session_id: str, version_id: str) -> Optional[Dict[str, Any]]:
        return self._get("SESSION#" + session_id, "VERSION#" + version_id)

    def list_versions(self, session_id: str) -> List[Dict[str, Any]]:
        return sorted(self._query("SESSION#" + session_id, prefix="VERSION#"), key=lambda v: v["number"])

    # ---- registros de aplicación --------------------------------------------
    def add_record(self, record: Dict[str, Any]) -> None:
        doc = {**record, "nextAdjustment": record.get("nextAdjustment") or ""}
        sid = record["sessionId"]

        def mutate(session):
            session["recordCount"] = session.get("recordCount", 0) + 1
            session["updatedAt"] = record["createdAt"]
            return session

        self._update_session(sid, mutate, lambda _s: [
            self._put_action("SESSION#" + sid, "RECORD#%s#%s" % (record["createdAt"], record["id"]), doc, "new")])

    def list_records(self, session_id: str) -> List[Dict[str, Any]]:
        return self._query("SESSION#" + session_id, prefix="RECORD#")

    # ---- borradores emitidos por el servidor ----------------------------------
    def put_draft(self, draft: Dict[str, Any]) -> None:
        # `ttl` permite que DynamoDB los elimine; la caducidad también se valida al leer (Service).
        self._put("DRAFT#" + draft["id"], "META", draft, if_new=True,
                  ttl={"N": str(int(draft.get("expiresEpoch") or self._now_epoch() + 86400))})

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        return self._get("DRAFT#" + draft_id, "META")

    # ---- claves de operación (idempotencia) --------------------------------------
    def reserve_operation(self, owner_id: str, key: str, digest: str, now: str) -> Optional[Dict[str, Any]]:
        try:
            self._put("OP#" + owner_id, key, {"digest": digest, "status": "pending", "result": None, "createdAt": now},
                      if_new=True, ttl={"N": str(int(self._now_epoch() + 7 * 86400))})
            return None
        except Exception as exc:  # noqa: BLE001
            if not _is_condition_failure(exc):
                raise
        return self._get("OP#" + owner_id, key)

    def complete_operation(self, owner_id: str, key: str, result: Any) -> None:
        current = self._get("OP#" + owner_id, key) or {}
        self._put("OP#" + owner_id, key, {**current, "status": "done", "result": result},
                  ttl={"N": str(int(self._now_epoch() + 7 * 86400))})

    def release_operation(self, owner_id: str, key: str) -> None:
        self.client.delete_item(TableName=self.table, Key={"pk": _s("OP#" + owner_id), "sk": _s(key)})

    # ---- experiencias -------------------------------------------------------------
    def add_experience(self, e: Dict[str, Any]) -> None:
        doc = {**e, "versionId": e["id"], "observation": e.get("observation") or "",
               "improvement": e.get("improvement") or ""}
        actions = [self._put_action("EXPERIENCE", e["id"], doc, "new")]
        if e.get("sourceVersionId"):
            actions.append(self._put_action("SHARED#" + e["authorId"], e["sourceVersionId"],
                                            {"experienceId": e["id"], "sessionId": e.get("sourceSessionId")}, "new"))
        try:
            self._transact(actions)
        except Exception as exc:  # noqa: BLE001
            if _is_condition_failure(exc):
                raise AlreadyExists()
            raise

    def get_experience(self, experience_id: str) -> Optional[Dict[str, Any]]:
        return self._get("EXPERIENCE", experience_id)

    def list_experiences(self) -> List[Dict[str, Any]]:
        return sorted(self._query("EXPERIENCE"), key=lambda e: (e["createdAt"], e["id"]))

    # ---- valoraciones y comentarios ---------------------------------------------
    def upsert_rating(self, rating: Dict[str, Any]) -> bool:
        """Clave revisor dentro de la experiencia: una sola valoración activa por persona y versión."""
        pk, sk = "RATINGS#" + rating["versionId"], rating["reviewerId"]
        for _ in range(OPTIMISTIC_RETRIES):
            raw = self._get_raw(pk, sk)
            if raw is None:
                try:
                    self._put(pk, sk, dict(rating), if_new=True)
                    return True
                except Exception as exc:  # noqa: BLE001
                    if not _is_condition_failure(exc):
                        raise
                    continue
            existing = json.loads(raw)
            existing.update({k: rating[k] for k in ("clarity", "feasibility", "coherence", "observation",
                                                    "context", "whatToKeep", "whatToChange", "updatedAt")})
            try:
                self._transact([self._put_action(pk, sk, existing, raw)])
                return False
            except Exception as exc:  # noqa: BLE001
                if not _is_condition_failure(exc):
                    raise
        raise VersionConflict()

    def list_ratings(self, version_id: str) -> List[Dict[str, Any]]:
        return sorted(self._query("RATINGS#" + version_id), key=lambda r: (r["createdAt"], r["id"]))

    def add_comment(self, comment: Dict[str, Any]) -> None:
        try:
            self._put("COMMENTS#" + comment["versionId"], "%s#%s" % (comment["createdAt"], comment["id"]), comment,
                      if_new=True)
        except Exception as exc:  # noqa: BLE001
            if not _is_condition_failure(exc):  # el mismo comentario (semilla) ya existe
                raise

    def list_comments(self, version_id: str) -> List[Dict[str, Any]]:
        return self._query("COMMENTS#" + version_id)

    # ---- preferencias -------------------------------------------------------------
    def get_preferences(self, owner_id: str) -> Optional[Dict[str, Any]]:
        return self._get("PREFERENCES", owner_id)

    def set_preferences(self, owner_id: str, data: Dict[str, Any]) -> None:
        self._put("PREFERENCES", owner_id, data)

    # ---- contratos de insignias -----------------------------------------------------
    def add_item(self, item_id: str, value: str, created_at: str) -> None:
        doc = {"id": item_id, "value": value, "createdAt": created_at}
        self._transact([
            self._put_action("ITEM", item_id, doc, "new"),
            self._put_action("ITEMS_BY_TIME", "%s#%s" % (created_at, item_id), doc, "new"),
        ])

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self._get("ITEM", item_id)

    def list_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Los más recientes primero, acotado por la propia consulta (Limit), sin leer toda la partición."""
        return self._query("ITEMS_BY_TIME", newest_first=True, limit=limit)

    def add_job(self, job_id: str, input_value: str, now: str) -> None:
        self._put("JOB", job_id, {"jobId": job_id, "input": input_value, "status": "queued", "output": None,
                                  "error": None, "createdAt": now, "updatedAt": now}, if_new=True)

    def update_job(self, job_id: str, status: str, now: str, output: Optional[str] = None,
                   error: Optional[str] = None) -> None:
        job = self._get("JOB", job_id) or {"jobId": job_id, "input": "", "createdAt": now}
        job.update({"status": status, "output": output, "error": error, "updatedAt": now})
        self._put("JOB", job_id, job)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._get("JOB", job_id)

    # ---- migración compatible del esquema anterior (pk = tipo, sk = id) ---------------
    def migrate_legacy(self) -> bool:
        """Copia los datos del esquema anterior al actual sin borrar nada. Idempotente. True si migró algo."""
        if self._get(*MIGRATION_KEY) is not None:
            return False
        legacy_sessions = self._query("SESSION")
        legacy_versions = self._query("VERSION")
        legacy_records = self._query("RECORD")
        for session in legacy_sessions:
            if "ownerId" not in session or self.get_session(session["id"]) is not None:
                continue
            versions = sorted((v for v in legacy_versions if v.get("sessionId") == session["id"]),
                              key=lambda v: v["number"])
            records = [r for r in legacy_records if r.get("sessionId") == session["id"]]
            current = next((v for v in versions if v["id"] == session.get("currentVersionId")), None)
            if current is None:
                continue  # versión huérfana del esquema anterior: no se presenta como sesión válida
            doc = {**session, "currentVersionNumber": current["number"], "reviewStatus": current["reviewStatus"],
                   "versionCount": len(versions), "recordCount": len(records),
                   "documentedVersions": sum(_documents(v) for v in versions)}
            for version in versions:
                self._put_ignore("SESSION#" + session["id"], "VERSION#" + version["id"], version)
                self._put_ignore("SESSION#" + session["id"], "VNUM#%06d" % version["number"], {"versionId": version["id"]})
            for record in records:
                self._put_ignore("SESSION#" + session["id"], "RECORD#%s#%s" % (record["createdAt"], record["id"]), record)
            experience_id = (session.get("provenance") or {}).get("experienceId")
            if experience_id:
                self._put_ignore("ADAPTED#" + experience_id, session["id"], {"ownerId": session["ownerId"]})
            self._put_ignore("USER#" + session["ownerId"], "SESSION#" + session["id"], _summary(doc))
            self._put_ignore("SESSION#" + session["id"], "META", doc)
        for rating in self._query("RATING"):
            self._put_ignore("RATINGS#" + rating["versionId"], rating["reviewerId"], rating)
        for comment in self._query("COMMENT"):
            self._put_ignore("COMMENTS#" + comment["versionId"], "%s#%s" % (comment["createdAt"], comment["id"]), comment)
        for experience in self._query("EXPERIENCE"):
            if experience.get("sourceVersionId"):
                self._put_ignore("SHARED#" + experience["authorId"], experience["sourceVersionId"],
                                 {"experienceId": experience["id"], "sessionId": experience.get("sourceSessionId")})
        for item in self._query("ITEM"):
            self._put_ignore("ITEMS_BY_TIME", "%s#%s" % (item["createdAt"], item["id"]), item)
        self._put(*MIGRATION_KEY, {"migratedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        return True

    def _put_ignore(self, pk: str, sk: str, doc: Any) -> None:
        try:
            self._put(pk, sk, doc, if_new=True)
        except Exception as exc:  # noqa: BLE001
            if not _is_condition_failure(exc):
                raise
