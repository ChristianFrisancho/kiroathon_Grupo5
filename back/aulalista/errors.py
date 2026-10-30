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
