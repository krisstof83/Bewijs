from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    domain: Optional[str] = None
    date_from: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    date_to: Optional[str] = Field(default=None, description="YYYY-MM-DD")


class SearchRequest(BaseModel):
    query: Optional[str] = None
    filters: SearchFilters = Field(default_factory=SearchFilters)


class OSINTItem(BaseModel):
    source: str
    timestamp: str
    reliability_score: float
    label: str
    summary: str
    url: str
    query: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Dossier(BaseModel):
    dossier_id: str
    created_at: str
    query: str
    filters: SearchFilters
    results: List[OSINTItem]
