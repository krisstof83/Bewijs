from __future__ import annotations

from ..core.logging import get_logger
from ..models.models import DashboardSummary, EvidenceItem, PersonDossier, TimelineEvent
from ..services.dashboard_service import generate_dashboard_summary
from ..services.storage_service import dossiers_path, evidence_path, load_models, save_models, timeline_path
from .dossier_engine import build_person_reports
from .import_engine import process_imports
from .timeline_engine import build_auto_timeline

logger = get_logger(__name__)


def run_full_auto_pipeline() -> DashboardSummary:
    existing_evidence = load_models(evidence_path(), EvidenceItem)
    imported = process_imports()
    all_evidence = existing_evidence + imported
    unique = {item.evidence_id: item for item in all_evidence}
    evidence = list(unique.values())
    save_models(evidence_path(), evidence)

    dossiers = build_person_reports(evidence)
    save_models(dossiers_path(), dossiers)

    timeline = build_auto_timeline(evidence)
    save_models(timeline_path(), timeline)

    summary = generate_dashboard_summary(evidence, dossiers, timeline)
    logger.info(
        "pipeline finished evidence=%s dossiers=%s events=%s",
        len(evidence),
        len(dossiers),
        len(timeline),
    )
    return summary


def get_current_state() -> tuple[list[EvidenceItem], list[PersonDossier], list[TimelineEvent]]:
    return (
        load_models(evidence_path(), EvidenceItem),
        load_models(dossiers_path(), PersonDossier),
        load_models(timeline_path(), TimelineEvent),
    )
