from __future__ import annotations

from typing import Any, Optional


class ApiError(Exception):
    """Error de negocio con código HTTP y mensaje comprensible para el docente."""

    def __init__(self, status: int, code: str, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details

    def to_body(self) -> dict:
        body = {"code": self.code, "message": self.message}
        if self.details is not None:
            body["details"] = self.details
        return {"error": body}


class VersionConflict(Exception):
    """La versión de partida dejó de ser la vigente o el número de versión ya existe (escritura concurrente)."""


class AlreadyExists(Exception):
    """Una escritura condicional encontró el registro ya creado (p. ej. la misma versión compartida dos veces)."""


VERSION_CONFLICT_MESSAGE = (
    "Mientras editabas se guardó otra versión de esta sesión. Tu edición sigue aquí: "
    "abre la versión nueva para revisarla o guarda tu trabajo como una sesión nueva."
)


def version_conflict() -> ApiError:
    return ApiError(409, "version_conflict", VERSION_CONFLICT_MESSAGE)
