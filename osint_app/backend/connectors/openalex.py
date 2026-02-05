from __future__ import annotations

from datetime import datetime
from typing import List

import httpx

from ..models import OSINTItem


async def search_openalex(query: str) -> List[OSINTItem]:
    if not query:
        return []
    url = "https://api.openalex.org/works"
    params = {"search": query, "per-page": 5}
    headers = {"User-Agent": "OSINT-Dossier/1.0"}
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()

    timestamp = datetime.utcnow().isoformat()
    items: List[OSINTItem] = []
    for work in payload.get("results", [])[:5]:
        title = work.get("display_name")
        if not title:
            continue
        items.append(
            OSINTItem(
                source="OpenAlex",
                timestamp=timestamp,
                reliability_score=0.76,
                label="feit",
                summary=title,
                url=work.get("id", "https://openalex.org"),
                query=query,
                metadata={
                    "publication_year": work.get("publication_year"),
                    "cited_by_count": work.get("cited_by_count"),
                },
            )
        )
    return items
