from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from .models import Dossier, OSINTItem, SearchFilters

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def dossier_path(dossier_id: str) -> Path:
    return DATA_DIR / f"{dossier_id}.json"


def save_dossier(query: str, filters: SearchFilters, results: List[OSINTItem]) -> Dossier:
    ensure_data_dir()
    dossier_id = uuid4().hex
    dossier = Dossier(
        dossier_id=dossier_id,
        created_at=datetime.utcnow().isoformat(),
        query=query,
        filters=filters,
        results=results,
    )
    path = dossier_path(dossier_id)
    path.write_text(dossier.model_dump_json(indent=2), encoding="utf-8")
    return dossier


def load_dossier(dossier_id: str) -> Dossier:
    path = dossier_path(dossier_id)
    if not path.exists():
        raise FileNotFoundError(dossier_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    return Dossier(**data)
