from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from docx import Document
from PyPDF2 import PdfReader

from ..models import AuditLog, Evidence, TimelineEvent, db

SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg', '.json', '.csv', '.html'}
DATE_PATTERN = re.compile(r'(20\d{2}-\d{2}-\d{2})')


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _read_txt(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='ignore')


def _read_docx(path: Path) -> str:
    doc = Document(path)
    return '\n'.join(p.text for p in doc.paragraphs)


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages[:10]:
        pages.append(page.extract_text() or '')
    return '\n'.join(pages)


def _read_json(path: Path) -> str:
    with path.open('r', encoding='utf-8', errors='ignore') as f:
        obj = json.load(f)
    return json.dumps(obj, ensure_ascii=False)


def _read_csv(path: Path) -> str:
    rows = []
    with path.open('r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            rows.append(', '.join(row))
            if idx >= 100:
                break
    return '\n'.join(rows)


def _read_html(path: Path) -> str:
    text = path.read_text(encoding='utf-8', errors='ignore')
    return re.sub(r'<[^>]+>', ' ', text)


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    try:
        if suffix == '.txt':
            return _read_txt(path)[:5000]
        if suffix == '.docx':
            return _read_docx(path)[:5000]
        if suffix == '.pdf':
            return _read_pdf(path)[:5000]
        if suffix == '.json':
            return _read_json(path)[:5000]
        if suffix == '.csv':
            return _read_csv(path)[:5000]
        if suffix == '.html':
            return _read_html(path)[:5000]
    except Exception:
        return ''
    return ''


def classify_type(path: Path) -> str:
    lower_name = path.name.lower()
    suffix = path.suffix.lower()
    if 'chat' in lower_name or 'whatsapp' in lower_name:
        return 'chat_export'
    if suffix in {'.pdf', '.docx', '.txt', '.html'}:
        return 'document'
    if suffix in {'.jpg', '.jpeg', '.png'}:
        return 'image'
    return 'data'


def score_relevance(snippet: str) -> tuple[str, str, bool]:
    text = snippet.lower()
    legal_hits = sum(token in text for token in ['overeenkomst', 'aansprakelijk', 'bewijs', 'schade', 'ondertekend'])
    personal_data = any(token in text for token in ['@', 'bsn', 'geboorte', 'telefoon'])
    if legal_hits >= 3:
        return 'high', 'high', personal_data
    if legal_hits >= 1:
        return 'medium', 'medium', personal_data
    return 'low', 'low', personal_data


def walk_files(root: Path) -> Iterable[Path]:
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            candidate = Path(dirpath) / filename
            if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield candidate


def _extract_event_time(file_path: Path, snippet: str) -> datetime:
    date_match = DATE_PATTERN.search(snippet)
    if date_match:
        try:
            return datetime.strptime(date_match.group(1), '%Y-%m-%d')
        except ValueError:
            pass
    return datetime.utcfromtimestamp(file_path.stat().st_mtime)


def scan_directory(root: str, source: str = 'local') -> dict:
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f'{root} bestaat niet')

    indexed = 0
    duplicates = 0
    evidence_count = Evidence.query.count()
    known_hashes: set[str] = {e.sha256 for e in Evidence.query.all()}

    for file_path in walk_files(root_path):
        file_hash = sha256sum(file_path)
        if file_hash in known_hashes:
            duplicates += 1
            continue

        snippet = extract_text(file_path)
        created = _extract_event_time(file_path, snippet)
        legal_relevance, evidence_strength, has_pii = score_relevance(snippet)
        evidence_count += 1
        evidence_id = f'EV-{created.strftime("%Y%m%d")}-{evidence_count:06d}'

        evidence = Evidence(
            evidence_id=evidence_id,
            filename=file_path.name,
            path=str(file_path),
            sha256=file_hash,
            file_type=classify_type(file_path),
            source=source,
            created_at=created,
            description=snippet[:500],
            legal_relevance=legal_relevance,
            confidence='high' if snippet else 'low',
            evidence_strength=evidence_strength,
            contains_personal_data=has_pii,
        )
        db.session.add(evidence)
        known_hashes.add(file_hash)
        indexed += 1

        db.session.add(
            TimelineEvent(
                event_time=created,
                event_type='file_discovered',
                title=f'Bestand geïndexeerd: {file_path.name}',
                details=f'bron={source}; type={evidence.file_type}; sterkte={evidence_strength}',
                evidence_id=evidence_id,
            )
        )

    db.session.add(AuditLog(action='scan_completed', payload=f'root={root}; indexed={indexed}; duplicates={duplicates}'))
    db.session.commit()
    return {'indexed': indexed, 'duplicates': duplicates}
