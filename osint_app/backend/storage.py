from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from .models import Dossier, EvidenceItem, OSINTItem, PersonDossier, SearchFilters

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORT_DIR = DATA_DIR / "reports"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def dossier_path(dossier_id: str) -> Path:
    return DATA_DIR / f"{dossier_id}.json"


def report_path(dossier_id: str) -> Path:
    return REPORT_DIR / f"{dossier_id}.txt"


def _render_readable_report(dossier: Dossier) -> str:
    lines = [
        "Forensisch Dossieroverzicht",
        f"Dossier ID: {dossier.dossier_id}",
        f"Aangemaakt: {dossier.created_at}",
        f"Zoekterm: {dossier.query}",
        "",
        f"Feiten (OSINT): {len(dossier.facts)}",
        f"Aannames/claims (OSINT): {len(dossier.assumptions)}",
        f"Bewijsstukken (imports): {len(dossier.evidence)}",
        "",
    ]
    for report in dossier.reports:
        lines.append(f"Persoon: {report.person_name}")
        lines.append(f"Zaak: {report.case_name}")
        lines.append("- Feiten:")
        lines.extend([f"  • {item}" for item in report.facts[:8]] or ["  • (geen)"])
        lines.append("- Aannames:")
        lines.extend([f"  • {item}" for item in report.assumptions[:8]] or ["  • (geen)"])
        lines.append("- Inconsistenties:")
        lines.extend([f"  • {item}" for item in report.inconsistencies[:8]] or ["  • (geen)"])
        lines.append("")
    return "\n".join(lines)


def save_dossier(
    query: str,
    filters: SearchFilters,
    results: List[OSINTItem],
    facts: List[OSINTItem],
    assumptions: List[OSINTItem],
    evidence: List[EvidenceItem],
    reports: List[PersonDossier],
) -> Dossier:
    ensure_data_dir()
    dossier_id = uuid4().hex
    dossier = Dossier(
        dossier_id=dossier_id,
        created_at=datetime.utcnow().isoformat(),
        query=query,
        filters=filters,
        results=results,
        facts=facts,
        assumptions=assumptions,
        evidence=evidence,
        reports=reports,
    )
    path = dossier_path(dossier_id)
    path.write_text(dossier.model_dump_json(indent=2), encoding="utf-8")
    report_path(dossier_id).write_text(_render_readable_report(dossier), encoding="utf-8")
    return dossier


def load_dossier(dossier_id: str) -> Dossier:
    path = dossier_path(dossier_id)
    if not path.exists():
        raise FileNotFoundError(dossier_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    return Dossier(**data)
