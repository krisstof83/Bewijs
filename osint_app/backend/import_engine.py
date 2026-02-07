from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .models import EvidenceItem, PersonDossier

TARGET_NAMES = ("Annike Koopman", "Jolanda Christoff")
IMPORT_FOLDERS = (
    Path("imports/pdf"),
    Path("imports/gmail"),
    Path("imports/drive"),
)


def _safe_read_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix in {".txt", ".md", ".json", ".html", ".eml", ".csv"}:
        return file_path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(file_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except Exception:
            return file_path.read_bytes()[:15000].decode("utf-8", errors="replace")

    return file_path.read_bytes()[:15000].decode("utf-8", errors="replace")


def _file_hash(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 64)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def classify_person(text: str) -> str:
    lowered = text.lower()
    for name in TARGET_NAMES:
        if name.lower() in lowered:
            return name
    return "Onbekend"


def classify_case(file_path: Path, text: str) -> str:
    base = f"{file_path.parent.name}:{file_path.stem}".lower()
    if "zaak" in text.lower():
        return "Algemene Zaak"
    return base.replace(" ", "_")


def split_facts_assumptions(text: str) -> tuple[List[str], List[str]]:
    facts: List[str] = []
    assumptions: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(line) < 12:
            continue
        lowered = line.lower()
        if any(marker in lowered for marker in ["ik denk", "vermoed", "waarschijnlijk", "misschien", "mening"]):
            assumptions.append(line)
        else:
            facts.append(line)
    return facts[:20], assumptions[:20]


def detect_inconsistencies(facts: List[str], assumptions: List[str]) -> List[str]:
    mismatches: List[str] = []
    for assumption in assumptions:
        al = assumption.lower()
        for fact in facts:
            fl = fact.lower()
            if any(token in al for token in ["niet", "geen"]) and not any(token in fl for token in ["niet", "geen"]):
                if any(word in fl for word in al.split()[:3]):
                    mismatches.append(f"Aannname mogelijk in strijd met feit: '{assumption[:80]}'")
                    break
    return mismatches[:10]


def process_imports(state_file: Path) -> List[EvidenceItem]:
    state: Dict[str, str] = {}
    if state_file.exists():
        state = json.loads(state_file.read_text(encoding="utf-8"))

    evidence_items: List[EvidenceItem] = []
    for folder in IMPORT_FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        for file_path in sorted(folder.iterdir()):
            if not file_path.is_file():
                continue
            file_hash = _file_hash(file_path)
            if state.get(str(file_path)) == file_hash:
                continue
            text = _safe_read_text(file_path)
            evidence_items.append(
                EvidenceItem(
                    evidence_id=hashlib.md5(f"{file_path}-{file_hash}".encode("utf-8")).hexdigest(),
                    source=folder.name,
                    file_path=str(file_path),
                    detected_person=classify_person(text),
                    detected_case=classify_case(file_path, text),
                    imported_at=datetime.utcnow().isoformat(),
                    content_hash=file_hash,
                    extracted_text=text[:5000],
                )
            )
            state[str(file_path)] = file_hash

    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return evidence_items


def build_person_reports(evidence: List[EvidenceItem]) -> List[PersonDossier]:
    grouped: Dict[tuple[str, str], List[EvidenceItem]] = {}
    for item in evidence:
        key = (item.detected_person, item.detected_case)
        grouped.setdefault(key, []).append(item)

    reports: List[PersonDossier] = []
    for (person_name, case_name), items in grouped.items():
        combined = "\n".join(item.extracted_text for item in items)
        facts, assumptions = split_facts_assumptions(combined)
        inconsistencies = detect_inconsistencies(facts, assumptions)
        reports.append(
            PersonDossier(
                person_name=person_name,
                case_name=case_name,
                facts=facts,
                assumptions=assumptions,
                inconsistencies=inconsistencies,
            )
        )
    return reports
