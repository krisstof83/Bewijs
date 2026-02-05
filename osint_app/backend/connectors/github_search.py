from __future__ import annotations

from datetime import datetime
from typing import List

import httpx

from ..models import OSINTItem


async def search_github(query: str) -> List[OSINTItem]:
    if not query:
        return []
    url = "https://api.github.com/search/users"
    params = {"q": query, "per_page": 5}
    headers = {
        "User-Agent": "OSINT-Dossier/1.0",
        "Accept": "application/vnd.github+json",
    }
    async with httpx.AsyncClient(timeout=12.0) as client:
        response = await client.get(url, params=params, headers=headers)
        if response.status_code == 403:
            return []
        response.raise_for_status()
        payload = response.json()

    timestamp = datetime.utcnow().isoformat()
    items: List[OSINTItem] = []
    for user in payload.get("items", [])[:5]:
        items.append(
            OSINTItem(
                source="GitHub",
                timestamp=timestamp,
                reliability_score=0.58,
                label="bron",
                summary=f"Openbaar GitHub-profiel: {user.get('login')}",
                url=user.get("html_url", "https://github.com"),
                query=query,
                metadata={"score": user.get("score")},
            )
        )
    return items
