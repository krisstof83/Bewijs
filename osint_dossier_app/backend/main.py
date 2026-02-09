from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    domain: Optional[str] = None
    date_from: Optional[str] = Field(default=None, description="ISO date")
    date_to: Optional[str] = Field(default=None, description="ISO date")


class SearchRequest(BaseModel):
    query: str
    filters: SearchFilters


class SearchResult(BaseModel):
    source: str
    timestamp: str
    reliability_score: float
    relevance_score: float
    label: str
    summary: str
    url: Optional[str] = None
    query: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: List[SearchResult]
    errors: List[str]
    dossier_saved: List[str]


app = FastAPI(title="OSINT Dossieronderzoek API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = Path(__file__).resolve().parent.parent
DOSSIER_DIR = BASE_DIR / "dossiers"
IMPORTS_DIR = BASE_DIR / "imports"


SOURCE_SCORES = {
    "Bing Web Search": 0.7,
    "DuckDuckGo": 0.6,
    "Wikipedia": 0.8,
    "GitHub": 0.6,
    "Certificate Transparency": 0.75,
    "OpenAlex": 0.7,
    "Reddit": 0.5,
}
LABELS = {
    "Wikipedia": "feit",
    "Certificate Transparency": "feit",
    "OpenAlex": "feit",
    "DuckDuckGo": "bron",
    "GitHub": "bron",
    "Bing Web Search": "bron",
    "Reddit": "claim",
}

IMPORT_SCAN_INTERVAL = 30


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relevance_from_text(query: str, text: str, boost: float = 0.0) -> float:
    if not text:
        return boost
    query_lower = query.lower()
    text_lower = text.lower()
    tokens = [token for token in query_lower.split() if token]
    if not tokens:
        return boost
    hits = sum(1 for token in tokens if token in text_lower)
    ratio = hits / max(len(tokens), 1)
    return min(1.0, boost + ratio)


def build_query(base_query: str, filters: SearchFilters) -> str:
    parts = [base_query]
    for value in [filters.name, filters.email, filters.phone, filters.domain]:
        if value:
            parts.append(value)
    return " ".join(part for part in parts if part).strip()


def slugify(value: str) -> str:
    return "".join(ch for ch in value.lower().strip().replace(" ", "_") if ch.isalnum() or ch == "_") or "onbekend"


def ensure_dirs() -> None:
    for path in [
        DOSSIER_DIR / "personen",
        DOSSIER_DIR / "zaken",
        DOSSIER_DIR / "bewijs" / "pdf",
        DOSSIER_DIR / "bewijs" / "emails",
        DOSSIER_DIR / "bewijs" / "screenshots",
        IMPORTS_DIR / "pdf",
        IMPORTS_DIR / "gmail",
        IMPORTS_DIR / "drive",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def load_processed_hashes() -> Dict[str, str]:
    index_path = DOSSIER_DIR / "bewijs" / "processed.json"
    if not index_path.exists():
        return {}
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_processed_hashes(index: Dict[str, str]) -> None:
    index_path = DOSSIER_DIR / "bewijs" / "processed.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            import pdfplumber
        except ImportError:
            return ""
        text_chunks: List[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text_chunks.append(page.extract_text() or "")
        return "\n".join(text_chunks).strip()
    if path.suffix.lower() in {".txt", ".eml"}:
        return path.read_text(encoding="utf-8", errors="ignore").strip()
    return ""


def detect_person_context(filename: str) -> Tuple[str, str]:
    known_persons = [p.name for p in (DOSSIER_DIR / "personen").iterdir() if p.is_dir()]
    known_cases = [p.name for p in (DOSSIER_DIR / "zaken").iterdir() if p.is_dir()]
    lowered = filename.lower()
    for person in known_persons:
        if person.lower() in lowered:
            return person, known_cases[0] if known_cases else person
    for case in known_cases:
        if case.lower() in lowered:
            return known_persons[0] if known_persons else case, case
    return "onbekend", "onbekend"


def save_evidence(source: str, path: Path, content: str, content_hash: str) -> str:
    timestamp = utc_now()
    evidence_payload = {
        "source": source,
        "timestamp": timestamp,
        "hash": content_hash,
        "original_path": str(path),
        "content": content,
    }
    evidence_path = DOSSIER_DIR / "bewijs" / f"bewijs_{slugify(path.stem)}_{content_hash[:10]}.json"
    evidence_path.write_text(json.dumps(evidence_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(evidence_path)


async def scan_imports_loop() -> None:
    while True:
        ensure_dirs()
        processed = load_processed_hashes()
        for import_dir, label in [
            (IMPORTS_DIR / "pdf", "pdf"),
            (IMPORTS_DIR / "gmail", "emails"),
            (IMPORTS_DIR / "drive", "drive"),
        ]:
            for file_path in import_dir.glob("*"):
                if not file_path.is_file():
                    continue
                try:
                    content = file_path.read_bytes()
                    content_hash = compute_hash(content)
                    if processed.get(str(file_path)) == content_hash:
                        continue
                    text = extract_text(file_path)
                    person, case = detect_person_context(file_path.name)
                    person_dir = DOSSIER_DIR / "personen" / slugify(person)
                    case_dir = DOSSIER_DIR / "zaken" / slugify(case)
                    person_dir.mkdir(parents=True, exist_ok=True)
                    case_dir.mkdir(parents=True, exist_ok=True)
                    evidence_path = save_evidence(label, file_path, text, content_hash)
                    report_path = case_dir / f"rapport_{slugify(file_path.stem)}_{content_hash[:8]}.txt"
                    report_path.write_text(
                        f"Bron: {label}\nDatum: {utc_now()}\nHash: {content_hash}\nBewijs: {evidence_path}\n",
                        encoding="utf-8",
                    )
                    processed[str(file_path)] = content_hash
                except OSError:
                    continue
        save_processed_hashes(processed)
        await asyncio.sleep(IMPORT_SCAN_INTERVAL)


async def fetch_duckduckgo(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
    response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    results: List[SearchResult] = []
    timestamp = utc_now()

    abstract_text = payload.get("AbstractText")
    abstract_url = payload.get("AbstractURL")
    if abstract_text:
        results.append(
            SearchResult(
                source="DuckDuckGo",
                timestamp=timestamp,
                reliability_score=SOURCE_SCORES["DuckDuckGo"],
                relevance_score=relevance_from_text(query, abstract_text, 0.2),
                label=LABELS["DuckDuckGo"],
                summary=abstract_text,
                url=abstract_url,
                query=query,
                metadata={"type": "abstract"},
            )
        )

    related_topics = payload.get("RelatedTopics", [])
    for item in related_topics:
        if isinstance(item, dict) and item.get("Text"):
            results.append(
                SearchResult(
                source="DuckDuckGo",
                timestamp=timestamp,
                reliability_score=SOURCE_SCORES["DuckDuckGo"],
                relevance_score=relevance_from_text(query, item["Text"], 0.1),
                label=LABELS["DuckDuckGo"],
                    summary=item["Text"],
                    url=item.get("FirstURL"),
                    query=query,
                    metadata={"type": "related"},
                )
            )
    return results


async def fetch_wikipedia(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    url = f"https://nl.wikipedia.org/api/rest_v1/page/summary/{quote(query)}"
    response = await client.get(url)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    payload = response.json()
    if not payload.get("extract"):
        return []
    return [
        SearchResult(
            source="Wikipedia",
            timestamp=utc_now(),
            reliability_score=SOURCE_SCORES["Wikipedia"],
            relevance_score=relevance_from_text(query, payload["extract"], 0.3),
            label=LABELS["Wikipedia"],
            summary=payload["extract"],
            url=payload.get("content_urls", {}).get("desktop", {}).get("page"),
            query=query,
            metadata={"type": payload.get("type"), "title": payload.get("title")},
        )
    ]


async def fetch_github(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    url = "https://api.github.com/search/users"
    params = {"q": query}
    response = await client.get(url, params=params)
    if response.status_code == 403:
        return []
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items", [])
    results: List[SearchResult] = []
    timestamp = utc_now()
    for item in items[:10]:
        summary = f"Publiek GitHub-profiel: {item.get('login')}"
        results.append(
            SearchResult(
                source="GitHub",
                timestamp=timestamp,
                reliability_score=SOURCE_SCORES["GitHub"],
                relevance_score=relevance_from_text(query, summary, 0.2),
                label=LABELS["GitHub"],
                summary=summary,
                url=item.get("html_url"),
                query=query,
                metadata={"type": "profile", "score": item.get("score")},
            )
        )
    return results


async def fetch_crtsh(client: httpx.AsyncClient, domain: str, query: str) -> List[SearchResult]:
    url = "https://crt.sh/"
    params = {"q": domain, "output": "json"}
    response = await client.get(url, params=params)
    if response.status_code == 502:
        return []
    response.raise_for_status()
    payload = response.json()
    results: List[SearchResult] = []
    for item in payload[:10]:
        name_value = item.get("name_value")
        if not name_value:
            continue
        summary = f"Certificaat gevonden voor {name_value}"
        results.append(
            SearchResult(
                source="Certificate Transparency",
                timestamp=utc_now(),
                reliability_score=SOURCE_SCORES["Certificate Transparency"],
                relevance_score=relevance_from_text(query, name_value, 0.4),
                label=LABELS["Certificate Transparency"],
                summary=summary,
                url=f"https://crt.sh/?id={item.get('id')}",
                query=query,
                metadata={"issuer": item.get("issuer_name"), "entry_timestamp": item.get("entry_timestamp")},
            )
        )
    return results


async def fetch_openalex(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    url = "https://api.openalex.org/authors"
    params = {"search": query, "per-page": 5}
    response = await client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    results: List[SearchResult] = []
    timestamp = utc_now()
    for item in payload.get("results", []):
        display_name = item.get("display_name")
        if not display_name:
            continue
        summary = f"Auteur/profiel in OpenAlex: {display_name}"
        results.append(
            SearchResult(
                source="OpenAlex",
                timestamp=timestamp,
                reliability_score=SOURCE_SCORES["OpenAlex"],
                relevance_score=relevance_from_text(query, display_name, 0.2),
                label=LABELS["OpenAlex"],
                summary=summary,
                url=item.get("id"),
                query=query,
                metadata={"works_count": item.get("works_count"), "cited_by_count": item.get("cited_by_count")},
            )
        )
    return results


async def fetch_bing(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    api_key = os.getenv("BING_API_KEY")
    if not api_key:
        return []
    url = "https://api.bing.microsoft.com/v7.0/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": 10, "mkt": "nl-NL"}
    response = await client.get(url, headers=headers, params=params)
    response.raise_for_status()
    payload = response.json()
    results: List[SearchResult] = []
    timestamp = utc_now()
    for item in payload.get("webPages", {}).get("value", []):
        snippet = item.get("snippet")
        if not snippet:
            continue
        results.append(
            SearchResult(
                source="Bing Web Search",
                timestamp=timestamp,
                reliability_score=SOURCE_SCORES["Bing Web Search"],
                relevance_score=relevance_from_text(query, snippet, 0.3),
                label=LABELS["Bing Web Search"],
                summary=snippet,
                url=item.get("url"),
                query=query,
                metadata={"title": item.get("name")},
            )
        )
    return results


async def fetch_reddit(client: httpx.AsyncClient, query: str) -> List[SearchResult]:
    url = "https://www.reddit.com/search.json"
    params = {"q": query, "limit": 10, "sort": "relevance"}
    headers = {"User-Agent": "osint-dossier-app/1.0"}
    response = await client.get(url, params=params, headers=headers)
    if response.status_code in {403, 429}:
        return []
    response.raise_for_status()
    payload = response.json()
    results: List[SearchResult] = []
    timestamp = utc_now()
    for item in payload.get("data", {}).get("children", []):
        data = item.get("data", {})
        title = data.get("title")
        if not title:
            continue
        summary = f"Reddit-post: {title}"
        results.append(
            SearchResult(
                source="Reddit",
                timestamp=timestamp,
                reliability_score=SOURCE_SCORES["Reddit"],
                relevance_score=relevance_from_text(query, title, 0.1),
                label=LABELS["Reddit"],
                summary=summary,
                url=f"https://www.reddit.com{data.get('permalink')}",
                query=query,
                metadata={"subreddit": data.get("subreddit"), "score": data.get("score")},
            )
        )
    return results


def dedupe_results(results: List[SearchResult]) -> List[SearchResult]:
    seen: set[str] = set()
    deduped: List[SearchResult] = []
    for item in results:
        key = (item.url or item.summary or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def save_search_dossier(base_query: str, filters: SearchFilters, results: List[SearchResult]) -> List[str]:
    ensure_dirs()
    person = slugify(filters.name or base_query)
    case = slugify(base_query)
    person_dir = DOSSIER_DIR / "personen" / person
    case_dir = DOSSIER_DIR / "zaken" / case
    person_dir.mkdir(parents=True, exist_ok=True)
    case_dir.mkdir(parents=True, exist_ok=True)
    timestamp = utc_now()

    raw_payload = {
        "query": base_query,
        "filters": filters.model_dump(),
        "timestamp": timestamp,
        "results": [result.model_dump() for result in results],
    }
    raw_path = case_dir / f"dossier_{case}_{slugify(timestamp)}.json"
    raw_path.write_text(json.dumps(raw_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_lines = [
        f"Zaak: {case}",
        f"Persoon: {person}",
        f"Tijdstip: {timestamp}",
        f"Aantal resultaten: {len(results)}",
        "",
    ]
    for result in results:
        summary_lines.append(f"- {result.source} | {result.label} | {result.summary}")
    report_path = case_dir / f"rapport_{case}_{slugify(timestamp)}.txt"
    report_path.write_text("\n".join(summary_lines), encoding="utf-8")

    return [str(raw_path), str(report_path)]


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event() -> None:
    ensure_dirs()
    asyncio.create_task(scan_imports_loop())


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    base_query = request.query.strip()
    if not base_query:
        return SearchResponse(results=[], errors=["Lege zoekopdracht."], dossier_saved=[])

    query = build_query(base_query, request.filters)

    errors: List[str] = []
    results: List[SearchResult] = []

    async with httpx.AsyncClient(timeout=12.0) as client:
        tasks = [
            fetch_duckduckgo(client, query),
            fetch_wikipedia(client, query),
            fetch_github(client, query),
            fetch_openalex(client, query),
            fetch_bing(client, query),
            fetch_reddit(client, query),
        ]

        if request.filters.domain:
            tasks.append(fetch_crtsh(client, request.filters.domain, query))

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in task_results:
        if isinstance(result, Exception):
            errors.append(str(result))
            continue
        results.extend(result)

    results = dedupe_results(results)
    results.sort(key=lambda item: (item.relevance_score, item.reliability_score), reverse=True)

    if not os.getenv("BING_API_KEY"):
        errors.append("Bing API key ontbreekt (BING_API_KEY).")

    if request.filters.date_from or request.filters.date_to:
        errors.append("Datumfilters zijn geregistreerd maar niet afdwingbaar in publieke APIs.")

    dossier_paths = save_search_dossier(base_query, request.filters, results)

    return SearchResponse(results=results, errors=errors, dossier_saved=dossier_paths)
