from __future__ import annotations

import asyncio
from contextlib import suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from osint_app.backend.engines.auto_engine import get_current_state, run_full_auto_pipeline
    from osint_app.backend.forensic import build_forensic_report, write_markdown_report, write_report_artifacts
    from osint_app.backend.models.models import (
        DashboardSummary,
        EvidenceItem,
        ForensicCommandRequest,
        ForensicReport,
        OSINTItem,
        SearchRequest,
        TimelineEvent,
    )
    from osint_app.backend.services.dashboard_service import generate_dashboard_summary
    from osint_app.backend.services.osint_service import search_osint
else:
    from .engines.auto_engine import get_current_state, run_full_auto_pipeline
    from .forensic import build_forensic_report, write_markdown_report, write_report_artifacts
    from .models.models import (
        DashboardSummary,
        EvidenceItem,
        ForensicCommandRequest,
        ForensicReport,
        OSINTItem,
        SearchRequest,
        TimelineEvent,
    )
    from .services.dashboard_service import generate_dashboard_summary
    from .services.osint_service import search_osint
from pathlib import Path

app = FastAPI(title="Auto Forensic OSINT Dossier Platform", version="4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_autoscan_task: asyncio.Task | None = None


async def _autoscan_loop() -> None:
    while True:
        run_full_auto_pipeline()
        await asyncio.sleep(60)


@app.on_event("startup")
async def auto_bootstrap() -> None:
    global _autoscan_task
    run_full_auto_pipeline()
    _autoscan_task = asyncio.create_task(_autoscan_loop())


@app.on_event("shutdown")
async def stop_autoscan() -> None:
    if _autoscan_task:
        _autoscan_task.cancel()
        with suppress(asyncio.CancelledError):
            await _autoscan_task


@app.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary() -> DashboardSummary:
    evidence, dossiers, timeline = get_current_state()
    return generate_dashboard_summary(evidence, dossiers, timeline)


@app.get("/evidence/list", response_model=list[EvidenceItem])
async def evidence_list() -> list[EvidenceItem]:
    evidence, _, _ = get_current_state()
    return evidence


@app.get("/timeline", response_model=list[TimelineEvent])
async def timeline() -> list[TimelineEvent]:
    _, _, events = get_current_state()
    return events


@app.post("/osint/search", response_model=list[OSINTItem])
async def osint_search(request: SearchRequest) -> list[OSINTItem]:
    return await search_osint(request)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/forensic/command", response_model=ForensicReport)
async def forensic_command(request: ForensicCommandRequest) -> ForensicReport:
    root_path = Path(request.root_path).resolve() if request.root_path else Path.cwd().resolve()
    report = build_forensic_report(request.command, root_path)
    artifacts_dir = root_path / "dossiers" / "reports"
    write_report_artifacts(report, artifacts_dir)
    write_markdown_report(report, artifacts_dir)
    return report
