from __future__ import annotations

import asyncio

from ..connectors import duckduckgo, github_search, openalex, reddit, wikipedia
from ..models.models import OSINTItem, SearchRequest
from ..services.storage_service import load_models, osint_path, save_models


async def search_osint(request: SearchRequest) -> list[OSINTItem]:
    query = " ".join(
        part
        for part in [
            request.query,
            request.filters.name,
            request.filters.email,
            request.filters.phone,
            request.filters.domain,
            request.filters.date_from,
            request.filters.date_to,
        ]
        if part
    ).strip()

    if not query:
        return []

    tasks = [
        duckduckgo.search(query),
        wikipedia.search(query),
        reddit.search(query),
        github_search.search(query),
        openalex.search(query),
    ]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    results: list[OSINTItem] = []
    for response in responses:
        if isinstance(response, Exception):
            continue
        results.extend(response)

    dedup: dict[str, OSINTItem] = {}
    for item in results:
        dedup[f"{item.source}|{item.url}"] = item

    final = sorted(dedup.values(), key=lambda i: i.reliability_score, reverse=True)
    historical = load_models(osint_path(), OSINTItem)
    save_models(osint_path(), (historical + final)[-500:])
    return final
