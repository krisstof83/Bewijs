from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from ..core.config import DATA_DIR, DOSSIERS_FILE, EVIDENCE_FILE, OSINT_FILE, TIMELINE_FILE

T = TypeVar("T", bound=BaseModel)


def _load_json(path: Path, default: list | dict) -> list | dict:
    try:
        if not path.exists():
            return default
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return default
        return json.loads(raw)
    except Exception:
        return default


def _save_json(path: Path, payload: list | dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    versioned = {"saved_at": datetime.utcnow().isoformat(), "payload": payload}
    path.write_text(json.dumps(versioned, indent=2, ensure_ascii=False), encoding="utf-8")


def _unwrap(data: list | dict) -> list | dict:
    if isinstance(data, dict) and "payload" in data:
        payload = data.get("payload")
        if isinstance(payload, (list, dict)):
            return payload
    return data


def load_models(path: Path, model: type[T]) -> list[T]:
    raw = _unwrap(_load_json(path, []))
    if not isinstance(raw, list):
        return []
    items: list[T] = []
    for entry in raw:
        try:
            items.append(model.model_validate(entry))
        except Exception:
            continue
    return items


def save_models(path: Path, items: list[BaseModel]) -> None:
    _save_json(path, [item.model_dump() for item in items])


def load_evidence_raw_state(path: Path) -> dict[str, str]:
    raw = _unwrap(_load_json(path, {}))
    return raw if isinstance(raw, dict) else {}


def save_state(path: Path, state: dict[str, str]) -> None:
    _save_json(path, state)


def evidence_path() -> Path:
    return EVIDENCE_FILE


def dossiers_path() -> Path:
    return DOSSIERS_FILE


def timeline_path() -> Path:
    return TIMELINE_FILE


def osint_path() -> Path:
    return OSINT_FILE
