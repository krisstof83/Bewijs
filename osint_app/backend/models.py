from __future__ import annotations

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


class EvidenceItem(BaseModel):
    evidence_id: str
    source: str
    file_path: str
    detected_person: str
    detected_case: str
    imported_at: str
    content_hash: str
    extracted_text: str


class PersonDossier(BaseModel):
    person_name: str
    case_name: str
    facts: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    inconsistencies: List[str] = Field(default_factory=list)


class Dossier(BaseModel):
    dossier_id: str
    created_at: str
    query: str
    filters: SearchFilters
    results: List[OSINTItem]
    facts: List[OSINTItem] = Field(default_factory=list)
    assumptions: List[OSINTItem] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    reports: List[PersonDossier] = Field(default_factory=list)
