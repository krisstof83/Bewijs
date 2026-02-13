from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    domain: str | None = None
    date_from: str | None = None
    date_to: str | None = None


class SearchRequest(BaseModel):
    query: str = ""
    filters: SearchFilters = Field(default_factory=SearchFilters)


class OSINTItem(BaseModel):
    source: str
    title: str
    summary: str
    url: str
    query: str
    timestamp: str
    reliability_score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimelineEvent(BaseModel):
    event_id: str
    timestamp: str
    title: str
    description: str
    related_evidence_ids: list[str] = Field(default_factory=list)
    confidence: str = "medium"


class DocumentAnalysis(BaseModel):
    facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    evidence_id: str
    source: str
    file_path: str
    detected_person: str
    detected_case: str
    imported_at: str
    content_hash: str
    extracted_text: str
    legal_relevance: str
    evidential_weight: str
    chain_of_custody: list[str] = Field(default_factory=list)
    analysis: DocumentAnalysis = Field(default_factory=DocumentAnalysis)


class PersonDossier(BaseModel):
    person_name: str
    case_name: str
    facts: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class DashboardSummary(BaseModel):
    total_evidence: int
    total_dossiers: int
    high_relevance_evidence: int
    latest_events: list[TimelineEvent] = Field(default_factory=list)
