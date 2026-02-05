from __future__ import annotations

from datetime import datetime
from typing import List

import httpx

from ..models import OSINTItem


async def search_duckduckgo(query: str) -> List[OSINTItem]:
    if not query:
        return []
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1,
    }
    headers = {"User-Agent": "OSINT-Dossier/1.0"}
    items: List[OSINTItem] = []
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()

    timestamp = datetime.utcnow().isoformat()
    if payload.get("AbstractText"):
        items.append(
            OSINTItem(
                source="DuckDuckGo",
                timestamp=timestamp,
                reliability_score=0.62,
                label="bron",
                summary=payload["AbstractText"],
                url=payload.get("AbstractURL") or "https://duckduckgo.com/",
                query=query,
                metadata={"type": "instant_answer"},
            )
        )

    for topic in payload.get("RelatedTopics", [])[:5]:
        if isinstance(topic, dict) and topic.get("Text"):
            items.append(
                OSINTItem(
                    source="DuckDuckGo",
                    timestamp=timestamp,
                    reliability_score=0.55,
                    label="bron",
                    summary=topic["Text"],
                    url=topic.get("FirstURL", "https://duckduckgo.com/"),
                    query=query,
                    metadata={"type": "related_topic"},
                )
            )
    return items
