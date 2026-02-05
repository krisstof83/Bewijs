from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
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


app = FastAPI(title="OSINT Dossieronderzoek API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SOURCE_SCORES = {
    "Bing Web Search": 0.7,
    "DuckDuckGo": 0.6,
    "Wikipedia": 0.8,
    "GitHub": 0.6,
    "Certificate Transparency": 0.75,
    "OpenAlex": 0.7,
}


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
                label="bron",
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
                    label="bron",
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
            label="bron",
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
                label="bron",
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
                label="feit",
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
                label="bron",
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
                label="bron",
                summary=snippet,
                url=item.get("url"),
                query=query,
                metadata={"title": item.get("name")},
            )
        )
    return results


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    base_query = request.query.strip()
    if not base_query:
        return SearchResponse(results=[], errors=["Lege zoekopdracht."])

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
        ]

        if request.filters.domain:
            tasks.append(fetch_crtsh(client, request.filters.domain, query))

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in task_results:
        if isinstance(result, Exception):
            errors.append(str(result))
            continue
        results.extend(result)

    results.sort(key=lambda item: (item.relevance_score, item.reliability_score), reverse=True)

    if not os.getenv("BING_API_KEY"):
        errors.append("Bing API key ontbreekt (BING_API_KEY).")

    if request.filters.date_from or request.filters.date_to:
        errors.append("Datumfilters zijn geregistreerd maar niet afdwingbaar in publieke APIs.")

    return SearchResponse(results=results, errors=errors)
