from __future__ import annotations

from datetime import datetime

import httpx

from ..models.models import OSINTItem


async def search(query: str) -> list[OSINTItem]:
    if not query:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search", "srsearch": query, "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json().get("query", {}).get("search", [])[:5]
    except Exception:
        return []

    ts = datetime.utcnow().isoformat()
    return [
        OSINTItem(
            source="wikipedia",
            title=item.get("title", "Wikipedia result"),
            summary=item.get("snippet", ""),
            url=f"https://en.wikipedia.org/wiki/{item.get('title','').replace(' ', '_')}",
            query=query,
            timestamp=ts,
            reliability_score=0.75,
        )
        for item in data
    ]
