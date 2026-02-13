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
                "https://www.reddit.com/search.json",
                params={"q": query, "limit": 5, "sort": "relevance"},
                headers={"User-Agent": "AutoForensicOSINT/1.0"},
            )
            resp.raise_for_status()
            children = resp.json().get("data", {}).get("children", [])
    except Exception:
        return []

    ts = datetime.utcnow().isoformat()
    items: list[OSINTItem] = []
    for child in children[:5]:
        data = child.get("data", {})
        items.append(
            OSINTItem(
                source="reddit",
                title=data.get("title", "Reddit post"),
                summary=data.get("selftext", "")[:250],
                url=f"https://reddit.com{data.get('permalink', '')}",
                query=query,
                timestamp=ts,
                reliability_score=0.45,
            )
        )
    return items
