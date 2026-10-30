"""Datos simulados de demostración (mock data), separados del código de negocio.

`matematica.json` contiene módulos de matemática (geometría, álgebra y fracciones), docentes ficticios y
experiencias compartidas con valoraciones y comentarios. Todo está marcado como simulado; no hay datos
personales reales. El servicio solo los siembra si `Settings.mock_data` está activo (por defecto en la demo).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

DATA_FILE = Path(__file__).with_name("matematica.json")


@lru_cache(maxsize=1)
def load() -> Dict[str, Any]:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    modules = {m["id"]: m for m in data["modules"]}
    if len(modules) != len(data["modules"]):
        raise ValueError("Hay módulos simulados con id repetido.")
    return {"users": dict(data["users"]), "modules": modules, "experiences": list(data["experiences"])}


def users() -> Dict[str, str]:
    return load()["users"]
