from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "output"

DATE_PATTERNS = [
    re.compile(r"(\d{4}-\d{2}-\d{2})"),
    re.compile(r"(\d{2}-\d{2}-\d{4})"),
    re.compile(r"(\d{2}/\d{2}/\d{4})"),
]

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".html",
    ".json",
    ".csv",
    ".log",
    ".xml",
    ".yml",
    ".yaml",
    ".py",
    ".js",
    ".ts",
    ".css",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_text_preview(path: Path, limit: int = 500) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    preview = content.strip().replace("\n", " ")
    return preview[:limit]


def read_pdf_preview(path: Path) -> str:
    return f"PDF-document ({path.stat().st_size} bytes)"


def read_image_info(path: Path) -> str:
    return f"Afbeelding ({path.stat().st_size} bytes)"


def detect_category(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in TEXT_EXTENSIONS:
        return "text"
    if suffix in {".eml", ".msg"}:
        return "email"
    return "binary"


def legal_relevance(text: str, path: Path) -> str:
    keywords = ["bewijs", "proces", "klacht", "zaak", "dossier", "forensisch", "rapport"]
    hit = any(keyword in text.lower() for keyword in keywords)
    if hit or path.suffix.lower() in {".pdf", ".docx"}:
        return "hoog"
    if path.suffix.lower() in {".json", ".html", ".log"}:
        return "middel"
    return "laag"


def extract_dates(text: str) -> List[str]:
    dates: List[str] = []
    for pattern in DATE_PATTERNS:
        dates.extend(pattern.findall(text))
    return dates


def parse_date(value: str) -> datetime | None:
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def scan_repository() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    evidence: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []
    evidence_counter = 1

    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            if path.name in {".git", "node_modules", "output", ".venv"}:
                continue
            continue
        if "output" in path.parts:
            continue
        category = detect_category(path)
        sha = sha256_file(path)
        stat = path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        preview = ""
        if category == "text":
            preview = read_text_preview(path)
        elif category == "pdf":
            preview = read_pdf_preview(path)
        elif category == "image":
            preview = read_image_info(path)

        evidence_id = f"EV-{evidence_counter:06d}"
        evidence_counter += 1

        evidence_item = {
            "id": evidence_id,
            "path": str(path.relative_to(REPO_ROOT)),
            "category": category,
            "sha256": sha,
            "modified": mtime.isoformat(),
            "size": stat.st_size,
            "preview": preview,
            "legal_relevance": legal_relevance(preview, path),
        }
        evidence.append(evidence_item)

        timeline.append(
            {
                "timestamp": mtime.isoformat(),
                "event": "Bestand gewijzigd",
                "evidence_ids": [evidence_id],
                "source": str(path.relative_to(REPO_ROOT)),
            }
        )

        for date_value in extract_dates(preview):
            parsed = parse_date(date_value)
            if parsed:
                timeline.append(
                    {
                        "timestamp": parsed.isoformat(),
                        "event": f"Datum genoemd in inhoud: {date_value}",
                        "evidence_ids": [evidence_id],
                        "source": str(path.relative_to(REPO_ROOT)),
                    }
                )

    timeline.sort(key=lambda item: item["timestamp"])
    return evidence, timeline


def label_sentences(text: str) -> List[Dict[str, str]]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    labeled: List[Dict[str, str]] = []
    for sentence in [s.strip() for s in sentences if s.strip()]:
        lowered = sentence.lower()
        if any(word in lowered for word in ["volgens", "lijkt", "vermoed", "mogelijk"]):
            label = "[INTERPRETATIE]"
        elif any(word in lowered for word in ["niet", "nooit", "geen"]):
            label = "[NUANCERING]"
        elif any(word in lowered for word in ["bewijst", "feit", "is vastgesteld"]):
            label = "[FEIT]"
        else:
            label = "[FEIT]"
        labeled.append({"label": label, "sentence": sentence})
    return labeled


def detect_inconsistencies(sentences: List[Dict[str, str]]) -> List[str]:
    inconsistencies: List[str] = []
    statements = [item["sentence"] for item in sentences]
    for statement in statements:
        lowered = statement.lower()
        if "niet" in lowered:
            for other in statements:
                if other == statement:
                    continue
                token = statement.split()[0]
                if token in other and "niet" not in other.lower():
                    inconsistencies.append(f"Mogelijke inconsistentie tussen: '{statement}' en '{other}'")
                    break
    return list(dict.fromkeys(inconsistencies))


def build_analysis(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    analysis: Dict[str, Any] = {"items": [], "inconsistencies": []}
    for item in evidence:
        if item["category"] not in {"text", "pdf"}:
            continue
        labeled = label_sentences(item["preview"])
        analysis["items"].append({"evidence_id": item["id"], "labeled": labeled})
        analysis["inconsistencies"].extend(detect_inconsistencies(labeled))
    analysis["inconsistencies"] = list(dict.fromkeys(analysis["inconsistencies"]))
    return analysis


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_simple_pdf(path: Path, title: str, lines: List[str]) -> None:
    width, height = 595, 842
    content_lines = [f"{title}"] + lines[:2000]
    text_stream = "BT /F1 12 Tf 40 800 Td "
    y_offset = 0
    for line in content_lines:
        sanitized = line.replace("(", "[").replace(")", "]")
        if y_offset:
            text_stream += f"0 -14 Td ({sanitized[:140]}) Tj "
        else:
            text_stream += f"({sanitized[:140]}) Tj "
        y_offset += 1
    text_stream += "ET"

    objects: List[bytes] = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj")
    objects.append(
        f"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj".encode()
    )
    stream_bytes = text_stream.encode("latin-1", errors="replace")
    objects.append(f"4 0 obj << /Length {len(stream_bytes)} >> stream\n".encode() + stream_bytes + b"\nendstream endobj")
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj")

    offsets: List[int] = []
    pdf = b"%PDF-1.4\n"
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj + b"\n"
    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += b"trailer << /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    pdf += f"startxref\n{xref_start}\n%%EOF".encode()

    path.write_bytes(pdf)


def write_docx(path: Path, title: str, sections: List[Tuple[str, List[str]]]) -> None:
    document_xml_lines = ["<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"]
    document_xml_lines.append(
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
    )
    document_xml_lines.append("<w:body>")
    document_xml_lines.append(f"<w:p><w:r><w:t>{title}</w:t></w:r></w:p>")
    for heading, lines in sections:
        document_xml_lines.append(f"<w:p><w:r><w:t>{heading}</w:t></w:r></w:p>")
        for line in lines:
            document_xml_lines.append(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>")
    document_xml_lines.append("</w:body></w:document>")

    content_types = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>
  <Default Extension=\"xml\" ContentType=\"application/xml\"/>
  <Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>
</Types>
"""
    rels = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>
</Relationships>
"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/document.xml", "\n".join(document_xml_lines))


def build_reports(evidence: List[Dict[str, Any]], timeline: List[Dict[str, Any]], analysis: Dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    evidence_lines = [
        f"{item['id']} | {item['category']} | {item['path']} | {item['sha256']} | {item['legal_relevance']}"
        for item in evidence
    ]
    timeline_lines = [
        f"{item['timestamp']} | {item['event']} | {','.join(item['evidence_ids'])}"
        for item in timeline
    ]

    write_json(OUTPUT_DIR / "evidence_index.json", evidence)
    write_json(OUTPUT_DIR / "timeline.json", timeline)
    write_json(OUTPUT_DIR / "analysis.json", analysis)

    write_simple_pdf(OUTPUT_DIR / "evidence_index.pdf", "Bewijsindex", evidence_lines)
    write_simple_pdf(OUTPUT_DIR / "timeline.pdf", "Chronologische tijdlijn", timeline_lines)

    summary = [
        f"Aantal bewijsstukken: {len(evidence)}",
        f"Aantal tijdlijnitems: {len(timeline)}",
        f"Inconsistenties gevonden: {len(analysis['inconsistencies'])}",
    ]
    facts = [
        f"{item['id']} | {item['path']} | {item['legal_relevance']}" for item in evidence
    ]
    matrix = [
        f"{item['id']} | {item['category']} | {item['sha256']}" for item in evidence
    ]
    timeline_report = timeline_lines[:200]
    analysis_lines = []
    for item in analysis["items"]:
        analysis_lines.append(f"{item['evidence_id']}")
        for line in item["labeled"]:
            analysis_lines.append(f"{line['label']} {line['sentence']}")
    inconsistencies = analysis["inconsistencies"] or ["Geen inconsistenties gedetecteerd op basis van beschikbare previews."]

    report_sections = [
        ("Samenvatting", summary),
        ("Feitenrelaas", facts),
        ("Bewijsmatrix", matrix),
        ("Tijdlijn", timeline_report),
        ("Analyse", analysis_lines),
        ("Inconsistenties & Verdraaiingen", inconsistencies),
        ("Conclusie", [
            "De bewijsindex en tijdlijn zijn opgesteld op basis van alle aangetroffen bestanden in de repository.",
            "Het dossier bevat een gestructureerde matrix met hashes en juridische relevantie voor herleidbaarheid.",
        ]),
    ]

    write_docx(OUTPUT_DIR / "eindrapport.docx", "Juridisch Eindrapport (Advocaat + GBA)", report_sections)

    pdf_lines = [line for _, lines in report_sections for line in lines]
    write_simple_pdf(OUTPUT_DIR / "eindrapport.pdf", "Juridisch Eindrapport (Advocaat + GBA)", pdf_lines)


def main() -> None:
    evidence, timeline = scan_repository()
    analysis = build_analysis(evidence)
    build_reports(evidence, timeline, analysis)


if __name__ == "__main__":
    main()
