from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List
from uuid import uuid4

from .models import (
    DashboardSummary,
    DocumentAnalysis,
    Dossier,
    EvidenceItem,
    OSINTItem,
    PersonDossier,
    SearchFilters,
    TimelineEvent,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORT_DIR = DATA_DIR / "reports"
EVIDENCE_DIR = DATA_DIR / "evidence"
EVIDENCE_INDEX_PATH = DATA_DIR / "evidence_index.json"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


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
        f"Bewijsstukken: {len(dossier.evidence)}",
        f"Tijdlijngebeurtenissen: {len(dossier.timeline)}",
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
    if dossier.timeline:
        lines.append("Tijdlijn:")
        for event in dossier.timeline[:30]:
            lines.append(f"  • {event.timestamp} — {event.title} ({event.confidence})")
    return "\n".join(lines)


def _load_json_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json_list(path: Path, payload: list[dict]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def list_evidence() -> List[EvidenceItem]:
    ensure_data_dir()
    rows = _load_json_list(EVIDENCE_INDEX_PATH)
    return [EvidenceItem(**row) for row in rows]


def save_evidence(item: EvidenceItem) -> None:
    ensure_data_dir()
    rows = _load_json_list(EVIDENCE_INDEX_PATH)
    rows = [row for row in rows if row.get("evidence_id") != item.evidence_id]
    rows.append(item.model_dump())
    _save_json_list(EVIDENCE_INDEX_PATH, rows)


def get_evidence(evidence_id: str) -> EvidenceItem:
    for item in list_evidence():
        if item.evidence_id == evidence_id:
            return item
    raise FileNotFoundError(evidence_id)


def save_dossier(
    query: str,
    filters: SearchFilters,
    results: List[OSINTItem],
    facts: List[OSINTItem],
    assumptions: List[OSINTItem],
    evidence: List[EvidenceItem],
    reports: List[PersonDossier],
    analyses: dict[str, DocumentAnalysis],
    timeline: List[TimelineEvent],
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
        analyses=analyses,
        timeline=timeline,
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


def list_dossiers() -> List[Dossier]:
    ensure_data_dir()
    items: List[Dossier] = []
    for path in DATA_DIR.glob("*.json"):
        if path.name == EVIDENCE_INDEX_PATH.name:
            continue
        try:
            items.append(Dossier(**json.loads(path.read_text(encoding="utf-8"))))
        except Exception:
            continue
    return sorted(items, key=lambda d: d.created_at, reverse=True)


def dashboard_summary() -> DashboardSummary:
    evidence = list_evidence()
    dossiers = list_dossiers()
    latest_events = sorted(
        [event for dossier in dossiers for event in dossier.timeline],
        key=lambda event: event.timestamp,
        reverse=True,
    )[:10]
    high_relevance = sum(1 for item in evidence if item.legal_relevance.lower() in {"hoog", "critical"})
    open_risks = sum(
        1
        for dossier in dossiers
        for analysis in dossier.analyses.values()
        if analysis.detected_risks
    )
    return DashboardSummary(
        total_evidence=len(evidence),
        total_dossiers=len(dossiers),
        high_relevance_evidence=high_relevance,
        open_risk_flags=open_risks,
        latest_events=latest_events,
    )
