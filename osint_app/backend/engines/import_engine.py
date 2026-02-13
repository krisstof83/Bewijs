from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

from ..core.config import DATE_REGEX, IMPORT_FOLDERS, STATE_FILE, SUPPORTED_EXTENSIONS
from ..models.models import DocumentAnalysis, EvidenceItem
from ..services.storage_service import load_evidence_raw_state, save_state

LEGAL_KEYWORDS = ("contract", "bewijs", "zaak", "advocaat", "rechtbank", "procedure", "klacht")
ASSUMPTION_MARKERS = ("ik denk", "vermoed", "misschien", "waarschijnlijk", "volgens mij")


def _safe_read_text(file_path: Path) -> str:
    if file_path.suffix.lower() in {".txt", ".json", ".html", ".eml", ".csv"}:
        return file_path.read_text(encoding="utf-8", errors="replace")
    if file_path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore

            return "\n".join((page.extract_text() or "") for page in PdfReader(str(file_path)).pages)
        except Exception:
            pass
    return file_path.read_bytes()[:20000].decode("utf-8", errors="replace")


def _file_hash(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _split_facts_assumptions(text: str) -> tuple[list[str], list[str]]:
    facts, assumptions = [], []
    for line in text.splitlines():
        cleaned = line.strip()
        if len(cleaned) < 12:
            continue
        lowered = cleaned.lower()
        if any(marker in lowered for marker in ASSUMPTION_MARKERS):
            assumptions.append(cleaned)
        else:
            facts.append(cleaned)
    return facts[:40], assumptions[:40]


def _detect_inconsistencies(facts: list[str], assumptions: list[str]) -> list[str]:
    findings: list[str] = []
    for assumption in assumptions:
        al = assumption.lower()
        if "niet" not in al:
            continue
        for fact in facts:
            fl = fact.lower()
            if "niet" not in fl and any(token in fl for token in al.split()[:4] if len(token) > 3):
                findings.append(f"Mogelijke tegenspraak: '{assumption[:120]}'")
                break
    return findings[:25]


def _legal_relevance(text: str) -> str:
    score = sum(1 for k in LEGAL_KEYWORDS if k in text.lower())
    if score >= 3:
        return "Hoog"
    if score == 2:
        return "Middel"
    return "Laag"


def _evidential_weight(text: str) -> str:
    length_score = min(len(text) // 1000, 3)
    date_score = 1 if re.search(DATE_REGEX, text) else 0
    total = length_score + date_score
    if total >= 3:
        return "hoog"
    if total == 2:
        return "middel"
    return "laag"


def _classify_person(text: str) -> str:
    for candidate in ("Kristof Huibers", "Anneke Coenen", "Yolanda Dello"):
        if candidate.lower() in text.lower():
            return candidate
    return "Onbekend"


def _classify_case(file_path: Path, text: str) -> str:
    if "zaak" in text.lower():
        return "algemene_zaak"
    return f"{file_path.parent.name}_{file_path.stem}".replace(" ", "_")


def process_imports() -> list[EvidenceItem]:
    state = load_evidence_raw_state(STATE_FILE)
    new_items: list[EvidenceItem] = []

    for folder in IMPORT_FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        for file_path in sorted(folder.iterdir()):
            if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            sha = _file_hash(file_path)
            key = str(file_path.resolve())
            if state.get(key) == sha:
                continue

            text = _safe_read_text(file_path)
            facts, assumptions = _split_facts_assumptions(text)
            analysis = DocumentAnalysis(
                facts=facts,
                assumptions=assumptions,
                inconsistencies=_detect_inconsistencies(facts, assumptions),
            )
            imported_at = datetime.utcnow().isoformat()
            evidence_id = hashlib.md5(f"{key}-{sha}".encode("utf-8")).hexdigest()
            item = EvidenceItem(
                evidence_id=evidence_id,
                source=folder.name,
                file_path=key,
                detected_person=_classify_person(text),
                detected_case=_classify_case(file_path, text),
                imported_at=imported_at,
                content_hash=sha,
                extracted_text=text[:10000],
                legal_relevance=_legal_relevance(text),
                evidential_weight=_evidential_weight(text),
                chain_of_custody=[f"{imported_at} import {file_path.name}"],
                analysis=analysis,
            )
            new_items.append(item)
            state[key] = sha

    save_state(STATE_FILE, state)
    return new_items
