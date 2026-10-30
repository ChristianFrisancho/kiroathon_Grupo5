"""Configuración por variables de entorno. Sin secretos en el código."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACK_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACK_DIR.parent

DEFAULT_TEAM_ID = "T005"
DEFAULT_MODEL_ID = "us.amazon.nova-lite-v1:0"


@dataclass(frozen=True)
class Settings:
    db_path: str
    front_dir: str
    demo_mode: bool
    generator: str          # "local" (plantilla) | "bedrock"
    host: str
    port: int
    team_id: str = DEFAULT_TEAM_ID
    store: str = "sqlite"   # "sqlite" (local) | "dynamodb" (Lambda)
    table_name: str = ""
    model_id: str = DEFAULT_MODEL_ID
    job_mode: str = "thread"  # "thread" (servidor local) | "lambda" (worker Lambda asíncrono)
    mock_data: bool = False   # siembra los datos simulados de matemática (mockdata/); activo en la demo


def load_settings(env=None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        db_path=env.get("AULALISTA_DB", str(BACK_DIR / "data" / "aulalista.db")),
        front_dir=env.get("AULALISTA_FRONT_DIR", str(ROOT_DIR / "front")),
        demo_mode=env.get("AULALISTA_DEMO_MODE", "true").lower() != "false",
        generator=env.get("AULALISTA_GENERATOR", "local"),
        host=env.get("AULALISTA_HOST", "127.0.0.1"),
        port=int(env.get("AULALISTA_PORT", "8000")),
        team_id=env.get("TEAM_ID", DEFAULT_TEAM_ID),
        store=env.get("AULALISTA_STORE", "sqlite"),
        table_name=env.get("TABLE_NAME", ""),
        model_id=env.get("MODEL_ID", DEFAULT_MODEL_ID),
        job_mode=env.get("AULALISTA_JOB_MODE", "thread"),
        mock_data=env.get("AULALISTA_MOCK_DATA", "true").lower() != "false",
    )
