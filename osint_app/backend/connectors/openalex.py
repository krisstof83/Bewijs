from __future__ import annotations

from datetime import datetime

import httpx

from ..models.models import OSINTItem


async def search(query: str) -> list[OSINTItem]:
    if not query:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://api.openalex.org/works", params={"search": query, "per-page": 5})
            resp.raise_for_status()
            results = resp.json().get("results", [])[:5]
    except Exception:
        return []

    ts = datetime.utcnow().isoformat()
    items: list[OSINTItem] = []
    for result in results:
        items.append(
            OSINTItem(
                source="openalex",
                title=result.get("display_name", "openalex result"),
                summary=f"Citations: {result.get('cited_by_count', 0)}",
                url=result.get("id", "https://openalex.org"),
                query=query,
                timestamp=ts,
                reliability_score=0.67,
            )
        )
    return items
