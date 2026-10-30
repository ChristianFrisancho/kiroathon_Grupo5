"""Arma el servicio según la configuración: local (SQLite + plantilla) o AWS (DynamoDB + Bedrock)."""
from __future__ import annotations

from typing import Callable, Optional

from .config import Settings
from .generator import build_generator
from .service import Service


def build_repository(settings: Settings):
    if settings.store == "dynamodb":
        from .dynamo_repository import DynamoRepository

        return DynamoRepository.from_table_name(settings.table_name)
    from .repository import Repository

    return Repository(settings.db_path)


def build_service(settings: Settings, dispatcher: Optional[Callable[[str], None]] = None) -> Service:
    return Service(build_repository(settings), build_generator(settings.generator, settings.model_id), settings,
                   dispatcher=dispatcher)
