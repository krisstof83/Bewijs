from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .connectors import (
    search_duckduckgo,
    search_github,
    search_reddit,
    search_wikipedia,
)
from .import_engine import build_person_reports, process_imports
from .models import Dossier, EvidenceItem, OSINTItem, SearchRequest
from .storage import dossier_path, load_dossier, report_path, save_dossier

app = FastAPI(title="OSINT Dossier API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMPORT_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "import_state.json"
IMPORT_EVIDENCE: List[EvidenceItem] = []


def build_query(request: SearchRequest) -> str:
    parts = [request.query or ""]
    filters = request.filters
    if filters.name:
        parts.append(filters.name)
    if filters.email:
        parts.append(filters.email)
    if filters.phone:
        parts.append(filters.phone)
    if filters.domain:
        parts.append(filters.domain)
    if filters.date_from or filters.date_to:
        parts.append(f"{filters.date_from or ''}..{filters.date_to or ''}")
    return " ".join(part for part in parts if part).strip()


def dedupe_results(results: List[OSINTItem]) -> List[OSINTItem]:
    seen: set[str] = set()
    deduped: List[OSINTItem] = []
    for item in results:
        key = f"{item.source}|{item.url}|{item.summary[:140].lower()}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def split_fact_assumptions(results: List[OSINTItem]) -> tuple[List[OSINTItem], List[OSINTItem]]:
    facts: List[OSINTItem] = []
    assumptions: List[OSINTItem] = []
    for item in results:
        if item.label == "claim":
            assumptions.append(item)
            continue
        lowered = item.summary.lower()
        if any(marker in lowered for marker in ["mogelijk", "waarschijnlijk", "onbevestigd", "vermoed"]):
            assumptions.append(item)
        else:
            facts.append(item)
    return facts, assumptions


def sort_results(results: List[OSINTItem]) -> List[OSINTItem]:
    def score(item: OSINTItem) -> tuple[float, str]:
        return (item.reliability_score, item.timestamp)

    return sorted(results, key=score, reverse=True)


async def _scan_imports_loop() -> None:
    while True:
        try:
            items = process_imports(IMPORT_STATE_FILE)
            if items:
                IMPORT_EVIDENCE.extend(items)
        except Exception:
            pass
        await asyncio.sleep(10)


@app.on_event("startup")
async def startup() -> None:
    IMPORT_EVIDENCE.extend(process_imports(IMPORT_STATE_FILE))
    asyncio.create_task(_scan_imports_loop())


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "imported_evidence": len(IMPORT_EVIDENCE),
    }


@app.post("/search", response_model=List[OSINTItem])
async def search(request: SearchRequest) -> List[OSINTItem]:
    query = build_query(request)
    if not query:
        raise HTTPException(status_code=400, detail="Geen zoekterm opgegeven.")
    tasks = [
        search_duckduckgo(query),
        search_wikipedia(query),
        search_reddit(query),
        search_github(query),
    ]
    results: List[OSINTItem] = []
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for response in responses:
        if isinstance(response, Exception):
            continue
        results.extend(response)
    return sort_results(dedupe_results(results))


@app.post("/dossiers", response_model=Dossier)
async def create_dossier(request: SearchRequest) -> Dossier:
    query = build_query(request)
    if not query:
        raise HTTPException(status_code=400, detail="Geen zoekterm opgegeven.")
    results = await search(request)
    facts, assumptions = split_fact_assumptions(results)
    reports = build_person_reports(IMPORT_EVIDENCE)
    dossier = save_dossier(
        query=query,
        filters=request.filters,
        results=results,
        facts=facts,
        assumptions=assumptions,
        evidence=IMPORT_EVIDENCE,
        reports=reports,
    )
    return dossier


@app.get("/dossiers/{dossier_id}", response_model=Dossier)
async def get_dossier(dossier_id: str) -> Dossier:
    try:
        return load_dossier(dossier_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dossier niet gevonden.") from exc


@app.get("/dossiers/{dossier_id}/export/json")
async def export_json(dossier_id: str):
    try:
        load_dossier(dossier_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dossier niet gevonden.") from exc
    path = dossier_path(dossier_id)
    return FileResponse(path=path, filename=path.name, media_type="application/json")


@app.get("/dossiers/{dossier_id}/export/report")
async def export_report(dossier_id: str):
    try:
        load_dossier(dossier_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dossier niet gevonden.") from exc
    path = report_path(dossier_id)
    return FileResponse(path=path, filename=path.name, media_type="text/plain")


@app.get("/dossiers/{dossier_id}/export/pdf")
async def export_pdf(dossier_id: str):
    try:
        dossier = load_dossier(dossier_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Dossier niet gevonden.") from exc

    filename = f"dossier_{dossier_id}.pdf"
    output_path = f"/tmp/{filename}"
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("OSINT Dossier", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Dossier ID: {dossier.dossier_id}", styles["Normal"]),
        Paragraph(f"Zoekterm: {dossier.query}", styles["Normal"]),
        Paragraph(f"Gegenereerd: {datetime.utcnow().isoformat()}", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"Feiten: {len(dossier.facts)}", styles["Normal"]),
        Paragraph(f"Aannames: {len(dossier.assumptions)}", styles["Normal"]),
        Paragraph(f"Bewijsstukken: {len(dossier.evidence)}", styles["Normal"]),
        Spacer(1, 12),
    ]
    for item in dossier.results:
        story.append(
            Paragraph(
                f"<b>{item.source}</b> · {item.timestamp} · {item.label} · score {item.reliability_score}",
                styles["Normal"],
            )
        )
        story.append(Paragraph(item.summary, styles["BodyText"]))
        story.append(Paragraph(item.url, styles["BodyText"]))
        story.append(Spacer(1, 10))
    doc.build(story)
    return FileResponse(path=output_path, filename=filename, media_type="application/pdf")
