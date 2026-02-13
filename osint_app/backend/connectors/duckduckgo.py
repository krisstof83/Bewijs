from __future__ import annotations

from datetime import datetime

import httpx

from ..models.models import OSINTItem


async def search(query: str) -> list[OSINTItem]:
    if not query:
        return []
    items: list[OSINTItem] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "no_redirect": 1},
                headers={"User-Agent": "AutoForensicOSINT/1.0"},
            )
            response.raise_for_status()
            payload = response.json()
        timestamp = datetime.utcnow().isoformat()
        if payload.get("AbstractText"):
            items.append(
                OSINTItem(
                    source="duckduckgo",
                    title="Instant Answer",
                    summary=payload["AbstractText"],
                    url=payload.get("AbstractURL") or "https://duckduckgo.com",
                    query=query,
                    timestamp=timestamp,
                    reliability_score=0.64,
                )
            )
    except Exception:
        return []
    return items
