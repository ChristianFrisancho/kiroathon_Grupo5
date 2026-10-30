"""Persistencia SQLite (servidor local). Mismo contrato que `DynamoRepository`.

Garantías equivalentes a DynamoDB:
- Crear sesión + primera versión y añadir versión + mover la vigente son transacciones.
- `add_version` solo confirma si la versión de partida sigue siendo la vigente; si no, `VersionConflict`.
- (sesión, número de versión) es único: nunca hay dos versiones 2.
- Compartir una versión es único por (autor, versión) mediante una restricción UNIQUE.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any, Dict, Iterable, List, Optional

from .errors import AlreadyExists, VersionConflict

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    module_id TEXT NOT NULL,
    module_version TEXT NOT NULL,
    provenance TEXT,
    current_version_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_owner ON sessions(owner_id, updated_at);
CREATE TABLE IF NOT EXISTS lesson_versions(
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    number INTEGER NOT NULL,
    parent_version_id TEXT,
    context TEXT NOT NULL,
    content TEXT NOT NULL,
    review_status TEXT NOT NULL,
    reason TEXT,
    generated_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(session_id, number)
);
CREATE TABLE IF NOT EXISTS application_records(
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    declared_date TEXT NOT NULL,
    activity TEXT NOT NULL,
    observation TEXT NOT NULL,
    next_adjustment TEXT,
    is_simulated INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS records_session ON application_records(session_id, created_at);
CREATE TABLE IF NOT EXISTS experiences(
    id TEXT PRIMARY KEY,
    author_id TEXT NOT NULL,
    source_session_id TEXT,
    source_version_id TEXT,
    title TEXT NOT NULL,
    purpose TEXT NOT NULL,
    grade TEXT NOT NULL,
    materials TEXT NOT NULL,
    description TEXT NOT NULL,
    observation TEXT,
    improvement TEXT,
    context TEXT NOT NULL,
    content TEXT NOT NULL,
    is_simulated INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(author_id, source_version_id)
);
CREATE TABLE IF NOT EXISTS ratings(
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    clarity INTEGER,
    feasibility INTEGER,
    coherence INTEGER,
    observation INTEGER,
    context TEXT,
    what_to_keep TEXT,
    what_to_change TEXT,
    is_simulated INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(version_id, reviewer_id)
);
CREATE TABLE IF NOT EXISTS comments(
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    text TEXT NOT NULL,
    is_simulated INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences(owner_id TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS items(id TEXT PRIMARY KEY, value TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS items_time ON items(created_at);
CREATE TABLE IF NOT EXISTS jobs(
    id TEXT PRIMARY KEY,
    input TEXT NOT NULL,
    status TEXT NOT NULL,
    output TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts(
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    data TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operations(
    owner_id TEXT NOT NULL,
    op_key TEXT NOT NULL,
    digest TEXT NOT NULL,
    status TEXT NOT NULL,
    result TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY(owner_id, op_key)
);
"""

# Columnas añadidas después de la primera versión del esquema (migración compatible, sin borrar datos).
ADDED_COLUMNS = {
    "sessions": [("provenance_experience_id", "TEXT")],
    "lesson_versions": [("edited_by_teacher", "INTEGER NOT NULL DEFAULT 0"), ("source_draft_id", "TEXT")],
}


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


class Repository:
    """Acceso a datos. Todas las operaciones se serializan con un cerrojo."""

    def __init__(self, path: str):
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(SCHEMA)
            for table, columns in ADDED_COLUMNS.items():
                existing = {r["name"] for r in self._conn.execute("PRAGMA table_info(%s)" % table)}
                for name, decl in columns:
                    if name not in existing:
                        self._conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, name, decl))
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- utilidades -------------------------------------------------
    def _one(self, sql: str, args: tuple = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, args).fetchone()

    def _all(self, sql: str, args: tuple = ()) -> List[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, args).fetchall()

    def _run(self, sql: str, args: tuple = ()) -> int:
        with self._lock:
            cursor = self._conn.execute(sql, args)
            self._conn.commit()
            return cursor.rowcount

    # ---- sesiones y versiones --------------------------------------
    def create_session(self, session: Dict[str, Any], version: Dict[str, Any]) -> None:
        """Crea sesión y primera versión en una transacción: nunca queda una sesión sin versión ni al revés."""
        provenance = session.get("provenance") or {}
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO sessions(id, owner_id, title, module_id, module_version, provenance,"
                    " provenance_experience_id, current_version_id, created_at, updated_at)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        session["id"], session["ownerId"], session["title"], session["moduleId"],
                        session["moduleVersion"], _dumps(session.get("provenance")),
                        provenance.get("experienceId"), version["id"], session["createdAt"], session["updatedAt"],
                    ),
                )
                self._insert_version(version)
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def _insert_version(self, v: Dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO lesson_versions(id, session_id, number, parent_version_id, context, content,"
            " review_status, reason, generated_by, created_at, edited_by_teacher, source_draft_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                v["id"], v["sessionId"], v["number"], v.get("parentVersionId"), _dumps(v["context"]),
                _dumps(v["content"]), v["reviewStatus"], v.get("reason"), _dumps(v["generatedBy"]),
                v["createdAt"], 1 if v.get("editedByTeacher") else 0, v.get("sourceDraftId"),
            ),
        )

    def add_version(self, version: Dict[str, Any], title: str, updated_at: str, expected_parent_id: str) -> None:
        """Inserta la versión y la hace vigente solo si `expected_parent_id` sigue siendo la vigente."""
        with self._lock:
            try:
                moved = self._conn.execute(
                    "UPDATE sessions SET current_version_id=?, title=?, updated_at=?"
                    " WHERE id=? AND current_version_id=?",
                    (version["id"], title, updated_at, version["sessionId"], expected_parent_id),
                ).rowcount
                if moved != 1:
                    raise VersionConflict()
                self._insert_version(version)
                self._conn.commit()
            except sqlite3.IntegrityError:
                self._conn.rollback()
                raise VersionConflict()
            except Exception:
                self._conn.rollback()
                raise

    def set_review_status(self, session_id: str, version_id: str, status: str, updated_at: str) -> None:
        with self._lock:
            try:
                self._conn.execute("UPDATE lesson_versions SET review_status=? WHERE id=? AND session_id=?",
                                   (status, version_id, session_id))
                self._conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (updated_at, session_id))
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    @staticmethod
    def _session(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"], "ownerId": row["owner_id"], "title": row["title"],
            "moduleId": row["module_id"], "moduleVersion": row["module_version"],
            "provenance": json.loads(row["provenance"]) if row["provenance"] else None,
            "currentVersionId": row["current_version_id"],
            "createdAt": row["created_at"], "updatedAt": row["updated_at"],
        }

    @staticmethod
    def _version(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"], "sessionId": row["session_id"], "number": row["number"],
            "parentVersionId": row["parent_version_id"], "context": json.loads(row["context"]),
            "content": json.loads(row["content"]), "reviewStatus": row["review_status"],
            "reason": row["reason"], "generatedBy": json.loads(row["generated_by"]),
            "editedByTeacher": bool(row["edited_by_teacher"]), "sourceDraftId": row["source_draft_id"],
            "createdAt": row["created_at"],
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("SELECT * FROM sessions WHERE id=?", (session_id,))
        return self._session(row) if row else None

    def list_sessions(self, owner_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Resumen por sesión en una sola consulta (sin leer versiones ni registros uno por uno)."""
        sql = (
            "SELECT s.*, v.number AS current_number, v.review_status AS current_review,"
            " (SELECT COUNT(*) FROM lesson_versions x WHERE x.session_id = s.id) AS version_count,"
            " (SELECT COUNT(*) FROM application_records r WHERE r.session_id = s.id) AS record_count,"
            " (SELECT COUNT(*) FROM lesson_versions d WHERE d.session_id = s.id AND d.number > 1"
            "   AND LENGTH(TRIM(COALESCE(d.reason, ''))) >= 10) AS documented_count"
            " FROM sessions s JOIN lesson_versions v ON v.id = s.current_version_id"
            " WHERE s.owner_id=? ORDER BY s.updated_at DESC, s.id"
        )
        args: tuple = (owner_id,)
        if limit is not None:
            sql += " LIMIT ?"
            args = (owner_id, int(limit))
        result = []
        for row in self._all(sql, args):
            summary = self._session(row)
            summary.update({
                "currentVersionNumber": row["current_number"], "reviewStatus": row["current_review"],
                "versionCount": row["version_count"], "recordCount": row["record_count"],
                "documentedVersions": row["documented_count"],
            })
            result.append(summary)
        return result

    def count_sessions(self, owner_id: str) -> int:
        return self._one("SELECT COUNT(*) AS n FROM sessions WHERE owner_id=?", (owner_id,))["n"]

    def count_adaptations(self, experience_ids: Iterable[str], exclude_owner: str) -> int:
        ids = list(experience_ids)
        if not ids:
            return 0
        marks = ",".join("?" for _ in ids)
        row = self._one(
            "SELECT COUNT(*) AS n FROM sessions WHERE owner_id != ? AND provenance_experience_id IN (%s)" % marks,
            (exclude_owner, *ids),
        )
        return row["n"]

    def get_version(self, session_id: str, version_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("SELECT * FROM lesson_versions WHERE id=? AND session_id=?", (version_id, session_id))
        return self._version(row) if row else None

    def list_versions(self, session_id: str) -> List[Dict[str, Any]]:
        rows = self._all("SELECT * FROM lesson_versions WHERE session_id=? ORDER BY number", (session_id,))
        return [self._version(r) for r in rows]

    # ---- registros de aplicación -----------------------------------
    def add_record(self, r: Dict[str, Any]) -> None:
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO application_records(id, session_id, version_id, declared_date, activity, observation,"
                    " next_adjustment, is_simulated, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        r["id"], r["sessionId"], r["versionId"], r["declaredDate"], r["activity"], r["observation"],
                        r.get("nextAdjustment") or "", 1 if r["isSimulated"] else 0, r["createdAt"],
                    ),
                )
                # Solo cambia la fecha: no puede restaurar una versión vigente antigua.
                self._conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (r["createdAt"], r["sessionId"]))
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def list_records(self, session_id: str) -> List[Dict[str, Any]]:
        rows = self._all(
            "SELECT * FROM application_records WHERE session_id=? ORDER BY created_at, id", (session_id,)
        )
        return [
            {
                "id": r["id"], "sessionId": r["session_id"], "versionId": r["version_id"],
                "declaredDate": r["declared_date"], "activity": r["activity"],
                "observation": r["observation"], "nextAdjustment": r["next_adjustment"],
                "isSimulated": bool(r["is_simulated"]), "createdAt": r["created_at"],
            }
            for r in rows
        ]

    # ---- borradores emitidos por el servidor ------------------------
    def put_draft(self, draft: Dict[str, Any]) -> None:
        self._run("INSERT INTO drafts(id, owner_id, data, expires_at) VALUES (?,?,?,?)",
                  (draft["id"], draft["ownerId"], _dumps(draft), draft["expiresAt"]))

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("SELECT data FROM drafts WHERE id=?", (draft_id,))
        return json.loads(row["data"]) if row else None

    # ---- claves de operación (idempotencia) ----------------------------
    def reserve_operation(self, owner_id: str, key: str, digest: str, now: str) -> Optional[Dict[str, Any]]:
        """Reserva la clave. Devuelve None si la reservó esta llamada, o el registro existente."""
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO operations(owner_id, op_key, digest, status, created_at) VALUES (?,?,?, 'pending', ?)",
                    (owner_id, key, digest, now),
                )
                self._conn.commit()
                return None
            except sqlite3.IntegrityError:
                self._conn.rollback()
                row = self._conn.execute(
                    "SELECT digest, status, result, created_at FROM operations WHERE owner_id=? AND op_key=?",
                    (owner_id, key),
                ).fetchone()
                return {"digest": row["digest"], "status": row["status"], "createdAt": row["created_at"],
                        "result": json.loads(row["result"]) if row["result"] else None}

    def complete_operation(self, owner_id: str, key: str, result: Any) -> None:
        self._run("UPDATE operations SET status='done', result=? WHERE owner_id=? AND op_key=?",
                  (_dumps(result), owner_id, key))

    def release_operation(self, owner_id: str, key: str) -> None:
        self._run("DELETE FROM operations WHERE owner_id=? AND op_key=? AND status='pending'", (owner_id, key))

    # ---- experiencias ------------------------------------------------
    def add_experience(self, e: Dict[str, Any]) -> None:
        try:
            self._run(
                "INSERT INTO experiences(id, author_id, source_session_id, source_version_id, title, purpose, grade,"
                " materials, description, observation, improvement, context, content, is_simulated, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    e["id"], e["authorId"], e.get("sourceSessionId"), e.get("sourceVersionId"), e["title"],
                    e["purpose"], e["grade"], _dumps(e["materials"]), e["description"], e.get("observation") or "",
                    e.get("improvement") or "", _dumps(e["context"]), _dumps(e["content"]),
                    1 if e["isSimulated"] else 0, e["createdAt"],
                ),
            )
        except sqlite3.IntegrityError:
            with self._lock:
                self._conn.rollback()
            raise AlreadyExists()

    @staticmethod
    def _experience(r: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": r["id"], "versionId": r["id"], "authorId": r["author_id"],
            "sourceSessionId": r["source_session_id"], "sourceVersionId": r["source_version_id"],
            "title": r["title"], "purpose": r["purpose"], "grade": r["grade"],
            "materials": json.loads(r["materials"]), "description": r["description"],
            "observation": r["observation"], "improvement": r["improvement"],
            "context": json.loads(r["context"]), "content": json.loads(r["content"]),
            "isSimulated": bool(r["is_simulated"]), "createdAt": r["created_at"],
        }

    def get_experience(self, experience_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("SELECT * FROM experiences WHERE id=?", (experience_id,))
        return self._experience(row) if row else None

    def list_experiences(self) -> List[Dict[str, Any]]:
        return [self._experience(r) for r in self._all("SELECT * FROM experiences ORDER BY created_at, id")]

    # ---- valoraciones y comentarios ---------------------------------
    def upsert_rating(self, rating: Dict[str, Any]) -> bool:
        """Una valoración activa por (versión, revisor). Devuelve True si se creó, False si se actualizó."""
        with self._lock:
            existing = self._conn.execute(
                "SELECT id FROM ratings WHERE version_id=? AND reviewer_id=?",
                (rating["versionId"], rating["reviewerId"]),
            ).fetchone()
            if existing:
                self._conn.execute(
                    "UPDATE ratings SET clarity=?, feasibility=?, coherence=?, observation=?, context=?,"
                    " what_to_keep=?, what_to_change=?, updated_at=? WHERE id=?",
                    (
                        rating["clarity"], rating["feasibility"], rating["coherence"], rating["observation"],
                        rating["context"], rating["whatToKeep"], rating["whatToChange"], rating["updatedAt"],
                        existing["id"],
                    ),
                )
                self._conn.commit()
                return False
            self._conn.execute(
                "INSERT INTO ratings(id, version_id, reviewer_id, clarity, feasibility, coherence, observation,"
                " context, what_to_keep, what_to_change, is_simulated, created_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    rating["id"], rating["versionId"], rating["reviewerId"], rating["clarity"],
                    rating["feasibility"], rating["coherence"], rating["observation"], rating["context"],
                    rating["whatToKeep"], rating["whatToChange"], 1 if rating["isSimulated"] else 0,
                    rating["createdAt"], rating["updatedAt"],
                ),
            )
            self._conn.commit()
            return True

    def list_ratings(self, version_id: str) -> List[Dict[str, Any]]:
        rows = self._all("SELECT * FROM ratings WHERE version_id=? ORDER BY created_at, id", (version_id,))
        return [
            {
                "id": r["id"], "versionId": r["version_id"], "reviewerId": r["reviewer_id"],
                "clarity": r["clarity"], "feasibility": r["feasibility"], "coherence": r["coherence"],
                "observation": r["observation"], "context": r["context"], "whatToKeep": r["what_to_keep"],
                "whatToChange": r["what_to_change"], "isSimulated": bool(r["is_simulated"]),
                "createdAt": r["created_at"], "updatedAt": r["updated_at"],
            }
            for r in rows
        ]

    def add_comment(self, c: Dict[str, Any]) -> None:
        self._run(
            "INSERT OR IGNORE INTO comments(id, version_id, author_id, text, is_simulated, created_at) VALUES (?,?,?,?,?,?)",
            (c["id"], c["versionId"], c["authorId"], c["text"], 1 if c["isSimulated"] else 0, c["createdAt"]),
        )

    def list_comments(self, version_id: str) -> List[Dict[str, Any]]:
        rows = self._all("SELECT * FROM comments WHERE version_id=? ORDER BY created_at, id", (version_id,))
        return [
            {
                "id": r["id"], "versionId": r["version_id"], "authorId": r["author_id"], "text": r["text"],
                "isSimulated": bool(r["is_simulated"]), "createdAt": r["created_at"],
            }
            for r in rows
        ]

    # ---- preferencias ------------------------------------------------
    def get_preferences(self, owner_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("SELECT data FROM preferences WHERE owner_id=?", (owner_id,))
        return json.loads(row["data"]) if row else None

    def set_preferences(self, owner_id: str, data: Dict[str, Any]) -> None:
        self._run(
            "INSERT INTO preferences(owner_id, data) VALUES (?,?)"
            " ON CONFLICT(owner_id) DO UPDATE SET data=excluded.data",
            (owner_id, _dumps(data)),
        )

    # ---- contratos de insignias --------------------------------------
    def add_item(self, item_id: str, value: str, created_at: str) -> None:
        self._run("INSERT INTO items(id, value, created_at) VALUES (?,?,?)", (item_id, value, created_at))

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("SELECT * FROM items WHERE id=?", (item_id,))
        return {"id": row["id"], "value": row["value"], "createdAt": row["created_at"]} if row else None

    def list_items(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Los más recientes primero, acotado en la consulta."""
        rows = self._all("SELECT * FROM items ORDER BY created_at DESC, id DESC LIMIT ?", (int(limit),))
        return [{"id": r["id"], "value": r["value"], "createdAt": r["created_at"]} for r in rows]

    def add_job(self, job_id: str, input_value: str, now: str) -> None:
        self._run(
            "INSERT INTO jobs(id, input, status, created_at, updated_at) VALUES (?,?, 'queued', ?, ?)",
            (job_id, input_value, now, now),
        )

    def update_job(self, job_id: str, status: str, now: str, output: Optional[str] = None,
                   error: Optional[str] = None) -> None:
        self._run(
            "UPDATE jobs SET status=?, output=?, error=?, updated_at=? WHERE id=?",
            (status, output, error, now, job_id),
        )

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        row = self._one("SELECT * FROM jobs WHERE id=?", (job_id,))
        if not row:
            return None
        return {
            "jobId": row["id"], "input": row["input"], "status": row["status"],
            "output": row["output"], "error": row["error"], "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
