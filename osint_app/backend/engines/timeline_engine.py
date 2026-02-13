from __future__ import annotations

import re
from datetime import datetime

from ..core.config import DATE_REGEX
from ..models.models import EvidenceItem, TimelineEvent


def build_auto_timeline(evidence: list[EvidenceItem]) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for item in evidence:
        events.append(
            TimelineEvent(
                event_id=f"import-{item.evidence_id}",
                timestamp=item.imported_at,
                title="Bestand geïmporteerd",
                description=f"{item.source}: {item.file_path.split('/')[-1]}",
                related_evidence_ids=[item.evidence_id],
                confidence="high",
            )
        )
        dates = re.findall(DATE_REGEX, item.extracted_text)
        for index, date in enumerate(dates[:8]):
            events.append(
                TimelineEvent(
                    event_id=f"text-{item.evidence_id}-{index}",
                    timestamp=f"{date}T00:00:00",
                    title="Datum gedetecteerd",
                    description=item.extracted_text[:180] or "Datum uit inhoud geëxtraheerd.",
                    related_evidence_ids=[item.evidence_id],
                    confidence="medium",
                )
            )

    def as_dt(event: TimelineEvent) -> datetime:
        try:
            return datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    return sorted(events, key=as_dt)
