from __future__ import annotations

from ..models.models import DashboardSummary, EvidenceItem, PersonDossier, TimelineEvent


def generate_dashboard_summary(
    evidence: list[EvidenceItem], dossiers: list[PersonDossier], timeline: list[TimelineEvent]
) -> DashboardSummary:
    high = sum(1 for item in evidence if item.legal_relevance.lower() == "hoog")
    return DashboardSummary(
        total_evidence=len(evidence),
        total_dossiers=len(dossiers),
        high_relevance_evidence=high,
        latest_events=timeline[-10:],
    )
