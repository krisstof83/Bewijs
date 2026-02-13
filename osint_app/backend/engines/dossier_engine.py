from __future__ import annotations

from collections import defaultdict

from ..models.models import EvidenceItem, PersonDossier


def build_person_reports(evidence: list[EvidenceItem]) -> list[PersonDossier]:
    grouped: dict[tuple[str, str], list[EvidenceItem]] = defaultdict(list)
    for item in evidence:
        grouped[(item.detected_person, item.detected_case)].append(item)

    dossiers: list[PersonDossier] = []
    for (person, case), items in grouped.items():
        facts: list[str] = []
        assumptions: list[str] = []
        inconsistencies: list[str] = []
        ids: list[str] = []

        for item in items:
            facts.extend(item.analysis.facts)
            assumptions.extend(item.analysis.assumptions)
            inconsistencies.extend(item.analysis.inconsistencies)
            ids.append(item.evidence_id)

        dossiers.append(
            PersonDossier(
                person_name=person,
                case_name=case,
                facts=facts[:80],
                assumptions=assumptions[:80],
                inconsistencies=inconsistencies[:40],
                evidence_ids=ids,
            )
        )
    return dossiers
