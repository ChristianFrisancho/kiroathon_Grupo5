"""Configuración por variables de entorno. Sin secretos en el código."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACK_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACK_DIR.parent

TEAM_ID = "T005"


@dataclass(frozen=True)
class Settings:
    db_path: str
    front_dir: str
    demo_mode: bool
    generator: str
    host: str
    port: int


def load_settings(env=None) -> Settings:
    env = os.environ if env is None else env
    return Settings(
        db_path=env.get("AULALISTA_DB", str(BACK_DIR / "data" / "aulalista.db")),
        front_dir=env.get("AULALISTA_FRONT_DIR", str(ROOT_DIR / "front")),
        demo_mode=env.get("AULALISTA_DEMO_MODE", "true").lower() != "false",
        generator=env.get("AULALISTA_GENERATOR", "local"),
        host=env.get("AULALISTA_HOST", "127.0.0.1"),
        port=int(env.get("AULALISTA_PORT", "8000")),
    )
