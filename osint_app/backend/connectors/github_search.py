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
                "https://api.github.com/search/repositories",
                params={"q": query, "per_page": 5},
                headers={"Accept": "application/vnd.github+json", "User-Agent": "AutoForensicOSINT/1.0"},
            )
            resp.raise_for_status()
            repos = resp.json().get("items", [])[:5]
    except Exception:
        return []

    ts = datetime.utcnow().isoformat()
    return [
        OSINTItem(
            source="github",
            title=repo.get("full_name", "repo"),
            summary=repo.get("description") or "",
            url=repo.get("html_url", "https://github.com"),
            query=query,
            timestamp=ts,
            reliability_score=0.58,
            metadata={"stars": repo.get("stargazers_count", 0)},
        )
        for repo in repos
    ]
