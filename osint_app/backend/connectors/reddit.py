from __future__ import annotations

from datetime import datetime
from typing import List

import httpx

from ..models import OSINTItem


async def search_reddit(query: str) -> List[OSINTItem]:
    if not query:
        return []
    url = "https://www.reddit.com/search.json"
    params = {"q": query, "limit": 5, "sort": "relevance"}
    headers = {"User-Agent": "OSINT-Dossier/1.0"}
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(url, params=params, headers=headers)
        if response.status_code == 429:
            return []
        response.raise_for_status()
        payload = response.json()

    items: List[OSINTItem] = []
    timestamp = datetime.utcnow().isoformat()
    for child in payload.get("data", {}).get("children", []):
        data = child.get("data", {})
        title = data.get("title")
        if not title:
            continue
        permalink = data.get("permalink", "")
        items.append(
            OSINTItem(
                source="Reddit",
                timestamp=timestamp,
                reliability_score=0.42,
                label="claim",
                summary=title,
                url=f"https://www.reddit.com{permalink}",
                query=query,
                metadata={
                    "subreddit": data.get("subreddit"),
                    "score": data.get("score"),
                },
            )
        )
    return items
