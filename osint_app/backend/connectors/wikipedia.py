from __future__ import annotations

from datetime import datetime
from typing import List

import httpx

from ..models import OSINTItem


async def search_wikipedia(query: str) -> List[OSINTItem]:
    if not query:
        return []
    url = f"https://nl.wikipedia.org/api/rest_v1/page/summary/{query}"
    headers = {"User-Agent": "OSINT-Dossier/1.0"}
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        payload = response.json()

    if not payload.get("extract"):
        return []

    timestamp = datetime.utcnow().isoformat()
    return [
        OSINTItem(
            source="Wikipedia",
            timestamp=timestamp,
            reliability_score=0.7,
            label="bron",
            summary=payload["extract"],
            url=payload.get("content_urls", {})
            .get("desktop", {})
            .get("page", "https://nl.wikipedia.org/"),
            query=query,
            metadata={"type": payload.get("type", "summary")},
        )
    ]
