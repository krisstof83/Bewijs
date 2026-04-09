from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from .models.models import (
    CounterpartyScenario,
    ForensicEvidenceIndexItem,
    ForensicReport,
    LabeledStatement,
    PersonProfile,
    PrivacyAssessment,
    TimelineEvent,
    TimelineGap,
)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".html", ".json", ".csv", ".png", ".jpg", ".jpeg"}
PERSONS = ["Kristof Huibers", "Anneke Coenen", "Yolanda Dello"]
DATE_REGEX = r"\b(20\d{2}-\d{2}-\d{2})\b"
SUPPORTED_COMMANDS = {"ANALYSE STARTEN", "SCENARIO'S TONEN", "EINDRAPPORT"}

LABEL_PATTERNS = {
    "[FEIT]": ["volgens", "bevestigd", "proces-verbaal", "bijlage", "bewijs"],
    "[INTERPRETATIE]": ["lijkt", "inschatting", "vermoed", "interpretatie"],
    "[VERDRAAIING]": ["altijd", "nooit", "iedereen weet", "feitelijk onjuist"],
    "[NUANCERING]": ["context", "voor zover", "gedeeltelijk", "met kanttekening"],
}


@dataclass
class FileScan:
    item: ForensicEvidenceIndexItem
    extracted_text: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_pdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def _read_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
        return re.sub(r"<[^>]+>", " ", xml)
    except Exception:
        return ""


def _read_textual(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(path)
    if suffix == ".docx":
        return _read_docx(path)
    if suffix in {".txt", ".html", ".json"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".csv":
        rows: list[str] = []
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for row in csv.reader(handle):
                rows.append(" ".join(row))
        return "\n".join(rows)
    return ""


def _legal_relevance(text: str) -> tuple[str, str]:
    lowered = text.lower()
    if any(token in lowered for token in ["vonnis", "dagvaarding", "proces-verbaal", "bewijsstuk"]):
        return "Hoog", "hoog"
    if any(token in lowered for token in ["verklaring", "incident", "correspondentie", "tijdlijn"]):
        return "Middel", "middel"
    return "Laag", "laag"


def _statement_label(sentence: str) -> str:
    lowered = sentence.lower()
    for label, markers in LABEL_PATTERNS.items():
        if any(marker in lowered for marker in markers):
            return label
    return "[FEIT]"


def scan_repository(root_path: Path) -> list[FileScan]:
    scans: list[FileScan] = []
    for path in root_path.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        stat = path.stat()
        extracted = _read_textual(path)
        relevance, weight = _legal_relevance(extracted)
        summary = " ".join(extracted.split())[:180] if extracted else f"Binaire bron: {path.name}"
        scans.append(
            FileScan(
                item=ForensicEvidenceIndexItem(
                    evidence_id=f"EV-{_sha256(path)[:12]}",
                    file_path=str(path),
                    file_type=path.suffix.lower().lstrip("."),
                    created_at=datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    sha256=_sha256(path),
                    short_description=summary,
                    legal_relevance=relevance,
                    evidentiary_weight=weight,
                ),
                extracted_text=extracted,
            )
        )
    return scans




def extract_timeline_events(text: str, evidence_id: str) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    matches = re.findall(DATE_REGEX, text)
    for index, date in enumerate(matches[:5]):
        events.append(
            TimelineEvent(
                event_id=f"{evidence_id}-{index}",
                timestamp=f"{date}T00:00:00",
                title="Gedetecteerde datum",
                description=(" ".join(text.split())[:200] or "Datum gedetecteerd in broninhoud."),
                related_evidence_ids=[evidence_id],
                confidence="medium",
            )
        )
    return events

def _build_timeline(scans: list[FileScan]) -> tuple[list[TimelineEvent], list[TimelineGap]]:
    events: list[TimelineEvent] = []
    for scan in scans:
        events.append(
            TimelineEvent(
                event_id=scan.item.evidence_id,
                timestamp=scan.item.modified_at,
                title=f"Bestand geanalyseerd: {Path(scan.item.file_path).name}",
                description=scan.item.short_description,
                related_evidence_ids=[scan.item.evidence_id],
                confidence="high",
            )
        )
        events.extend(extract_timeline_events(scan.extracted_text, scan.item.evidence_id))

    events.sort(key=lambda event: event.timestamp)

    gaps: list[TimelineGap] = []
    for previous, current in zip(events, events[1:]):
        start = datetime.fromisoformat(previous.timestamp)
        end = datetime.fromisoformat(current.timestamp)
        delta_days = (end - start).days
        if delta_days > 30:
            gaps.append(
                TimelineGap(
                    after_timestamp=previous.timestamp,
                    before_timestamp=current.timestamp,
                    note=f"Tijdlijnhiaat van {delta_days} dagen tussen bewijsmomenten.",
                )
            )
    return events, gaps


def _build_profiles(scans: list[FileScan]) -> tuple[list[PersonProfile], list[LabeledStatement]]:
    profiles = {person: PersonProfile(person=person) for person in PERSONS}
    labeled: list[LabeledStatement] = []

    for scan in scans:
        sentences = re.split(r"(?<=[.!?])\s+", scan.extracted_text)
        for sentence in sentences[:60]:
            cleaned = " ".join(sentence.split())
            if len(cleaned) < 20:
                continue
            label = _statement_label(cleaned)
            target_people = [person for person in PERSONS if person.lower().split()[0] in cleaned.lower()]
            if not target_people:
                continue
            for person in target_people:
                profile = profiles[person]
                profile.statements.append(cleaned)
                if label == "[FEIT]":
                    profile.facts.append(cleaned)
                if label == "[VERDRAAIING]":
                    profile.inconsistencies.append(cleaned)
                if "verand" in cleaned.lower() or "ineens" in cleaned.lower():
                    profile.behavior_changes.append(cleaned)
                if "belang" in cleaned.lower() or "motief" in cleaned.lower():
                    profile.motives.append(cleaned)
                    profile.possible_interests.append(cleaned)
                if any(token in cleaned.lower() for token in ["medisch", "diagnose", "arts", "ziekte"]):
                    profile.medical_context.append(cleaned)
                labeled.append(
                    LabeledStatement(
                        person=person,
                        statement=cleaned,
                        label=label,
                        source_evidence_id=scan.item.evidence_id,
                    )
                )

    return list(profiles.values()), labeled


def _build_scenarios() -> list[CounterpartyScenario]:
    return [
        CounterpartyScenario(
            scenario="Betwisting authenticiteit bewijs",
            likely_action="Stellen dat bestanden gemanipuleerd zijn of context missen.",
            legal_strategy="Uitsluiting op basis van betrouwbaarheid en herkomstketen.",
            risk_level="hoog",
            counter_argument="Toon SHA-256 hashes, metadata en chain-of-custody per bewijs-ID.",
        ),
        CounterpartyScenario(
            scenario="Framing als conflict buiten juridische kern",
            likely_action="Verleggen van focus naar relationele/emotionele discussie.",
            legal_strategy="Ondergraven van proportionaliteit en relevantie.",
            risk_level="middel",
            counter_argument="Houd argumentatie bij verifieerbare feiten, tijdlijn en processtukken.",
        ),
        CounterpartyScenario(
            scenario="AVG-bezwaar tegen verwerking",
            likely_action="Aanvoeren dat persoonsgegevens onrechtmatig verwerkt zijn.",
            legal_strategy="Niet-ontvankelijkheid of bewijsuitsluiting.",
            risk_level="middel",
            counter_argument="Onderbouw gerechtvaardigd belang, minimale verwerking en beveiligingsmaatregelen.",
        ),
    ]


def _privacy_assessment(scans: list[FileScan]) -> PrivacyAssessment:
    corpus = "\n".join(scan.extracted_text[:2000] for scan in scans).lower()
    detected: list[str] = []
    if re.search(r"\b\d{8,}\b", corpus):
        detected.append("Unieke nummers/identificatoren")
    if "@" in corpus:
        detected.append("E-mailadressen")
    if re.search(r"\b\+?\d{9,}\b", corpus):
        detected.append("Telefoonnummers")
    return PrivacyAssessment(
        personal_data_detected=detected,
        processing_basis=[
            "Gerechtvaardigd belang: juridische verdediging en bewijsveiligstelling",
            "Noodzakelijk voor instelling, uitoefening of onderbouwing van rechtsvorderingen",
        ],
        risks=[
            "Onbedoelde oververwerking van irrelevante persoonsgegevens",
            "Onvoldoende afscherming bij delen van rapportages",
        ],
        safeguards=[
            "Hashing en integriteitscontrole per bestand",
            "Dataminimalisatie bij exports en rolgebaseerde toegang",
        ],
    )


def build_forensic_report(command: str, root_path: Path) -> ForensicReport:
    normalized_command = command.strip().upper()
    if normalized_command not in SUPPORTED_COMMANDS:
        normalized_command = "ANALYSE STARTEN"

    scans = scan_repository(root_path)
    chronology, gaps = _build_timeline(scans)
    profiles, labeled = _build_profiles(scans)
    scenarios = _build_scenarios()
    privacy = _privacy_assessment(scans)

    if normalized_command == "SCENARIO'S TONEN":
        chronology = []
        gaps = []
        labeled = []
        profiles = []
    elif normalized_command == "EINDRAPPORT":
        pass

    return ForensicReport(
        generated_at=datetime.utcnow().isoformat(),
        command=normalized_command,
        dossier_overview=f"Volledige scan uitgevoerd over {len(scans)} potentiële bewijsbestanden.",
        evidence_index=[scan.item for scan in scans],
        chronology=chronology,
        timeline_gaps=gaps,
        labeled_statements=labeled,
        profiles=profiles,
        scenarios=scenarios,
        legal_relevance=[
            "Documenten met verwijzingen naar processtukken en verklaringen prioriteren voor productie.",
            "Inconsistenties en narratiefwijzigingen expliciet relateren aan tijdlijngebeurtenissen.",
        ],
        framing_risks=[
            "Selectieve citatie zonder context kan bewijswaarde verlagen.",
            "Medische context mag uitsluitend feitelijk en proportioneel worden gebruikt.",
        ],
        lawyer_summary=(
            "Rapport bundelt bewijsindex, tijdlijn, gelabelde uitspraken en scenarioanalyse. "
            "Gebruik de evidence_id + hash-combinatie als primaire authenticiteitsreferentie in processtukken."
        ),
        active_status="Actief dossier: scan en juridische analyse bijgewerkt.",
        privacy_assessment=privacy,
    )


def write_report_artifacts(report: ForensicReport, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / "forensic_report.json"
    output.write_text(json.dumps(report.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def render_legal_markdown(report: ForensicReport) -> str:
    lines: list[str] = []
    lines.append("# Forensisch-juridisch eindrapport")
    lines.append("")
    lines.append("## Dossieroverzicht")
    lines.append(report.dossier_overview)
    lines.append("")
    lines.append("## Personen & Rollen")
    for profile in report.profiles:
        lines.append(f"- **{profile.person}**: primair geprofileerd op basis van bronuitspraken en dossierinhoud.")
    if not report.profiles:
        lines.append("- Geen persoonsprofielen opgenomen voor dit commando.")
    lines.append("")
    lines.append("## Chronologie")
    for event in report.chronology[:50]:
        lines.append(f"- {event.timestamp}: {event.title} ({', '.join(event.related_evidence_ids)})")
    if not report.chronology:
        lines.append("- Niet van toepassing voor dit commando.")
    lines.append("")
    lines.append("## Feiten vs Meningen")
    for statement in report.labeled_statements[:120]:
        lines.append(f"- {statement.label} {statement.person}: {statement.statement} [bron: {statement.source_evidence_id}]")
    if not report.labeled_statements:
        lines.append("- Niet van toepassing voor dit commando.")
    lines.append("")
    lines.append("## Gedragsanalyse per persoon")
    for profile in report.profiles:
        lines.append(f"### {profile.person}")
        lines.append(f"- Feiten: {len(profile.facts)}")
        lines.append(f"- Gedragsveranderingen: {len(profile.behavior_changes)}")
        lines.append(f"- Inconsistenties: {len(profile.inconsistencies)}")
        lines.append(f"- Motieven: {len(profile.motives)}")
        lines.append(f"- Mogelijke belangen: {len(profile.possible_interests)}")
        lines.append(f"- Medische context: {len(profile.medical_context)}")
    if not report.profiles:
        lines.append("- Niet van toepassing voor dit commando.")
    lines.append("")
    lines.append("## Inconsistenties & Verdraaiingen")
    inconsistencies = [s for s in report.labeled_statements if s.label == "[VERDRAAIING]"][:80]
    for item in inconsistencies:
        lines.append(f"- {item.person}: {item.statement} [bron: {item.source_evidence_id}]")
    if not inconsistencies:
        lines.append("- Geen expliciet gelabelde [VERDRAAIING] gedetecteerd binnen scanbeperkingen.")
    lines.append("")
    lines.append("## Juridische relevantie")
    for item in report.legal_relevance:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Risico’s bij framing of misbruik")
    for item in report.framing_risks:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Samenvatting voor advocaat / rechter")
    lines.append(report.lawyer_summary)
    lines.append("")
    lines.append("## Actieve dossierstatus")
    lines.append(report.active_status)
    lines.append("")
    lines.append("## Bewijsindex (samenvatting)")
    for evidence in report.evidence_index[:120]:
        lines.append(
            f"- {evidence.evidence_id} | {evidence.file_type} | {evidence.legal_relevance}/{evidence.evidentiary_weight} | {evidence.file_path}"
        )
    lines.append("")
    lines.append("## AVG / GBA-toets")
    lines.append(f"- Persoonsgegevens: {', '.join(report.privacy_assessment.personal_data_detected) or 'geen patroon gedetecteerd'}")
    for basis in report.privacy_assessment.processing_basis:
        lines.append(f"- Rechtsgrond: {basis}")
    for risk in report.privacy_assessment.risks:
        lines.append(f"- Risico: {risk}")
    for safeguard in report.privacy_assessment.safeguards:
        lines.append(f"- Maatregel: {safeguard}")
    lines.append("")
    return "\n".join(lines)


def write_markdown_report(report: ForensicReport, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / "forensic_report.md"
    output.write_text(render_legal_markdown(report), encoding="utf-8")
    return output
