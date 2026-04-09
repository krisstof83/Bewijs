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


class ForensicEvidenceIndexItem(BaseModel):
    evidence_id: str
    file_path: str
    file_type: str
    created_at: str
    modified_at: str
    sha256: str
    short_description: str
    legal_relevance: str
    evidentiary_weight: str


class LabeledStatement(BaseModel):
    person: str
    statement: str
    label: str
    source_evidence_id: str


class PersonProfile(BaseModel):
    person: str
    facts: list[str] = Field(default_factory=list)
    statements: list[str] = Field(default_factory=list)
    behavior_changes: list[str] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)
    motives: list[str] = Field(default_factory=list)
    possible_interests: list[str] = Field(default_factory=list)
    medical_context: list[str] = Field(default_factory=list)


class TimelineGap(BaseModel):
    after_timestamp: str
    before_timestamp: str
    note: str


class CounterpartyScenario(BaseModel):
    scenario: str
    likely_action: str
    legal_strategy: str
    risk_level: str
    counter_argument: str


class PrivacyAssessment(BaseModel):
    personal_data_detected: list[str] = Field(default_factory=list)
    processing_basis: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    safeguards: list[str] = Field(default_factory=list)


class ForensicReport(BaseModel):
    generated_at: str
    command: str
    dossier_overview: str
    evidence_index: list[ForensicEvidenceIndexItem] = Field(default_factory=list)
    chronology: list[TimelineEvent] = Field(default_factory=list)
    timeline_gaps: list[TimelineGap] = Field(default_factory=list)
    labeled_statements: list[LabeledStatement] = Field(default_factory=list)
    profiles: list[PersonProfile] = Field(default_factory=list)
    scenarios: list[CounterpartyScenario] = Field(default_factory=list)
    legal_relevance: list[str] = Field(default_factory=list)
    framing_risks: list[str] = Field(default_factory=list)
    lawyer_summary: str
    active_status: str
    privacy_assessment: PrivacyAssessment


class ForensicCommandRequest(BaseModel):
    command: str = Field(description="Ondersteunt: ANALYSE STARTEN, SCENARIO'S TONEN, EINDRAPPORT")
    root_path: str | None = Field(default=None, description="Optioneel pad voor analyse")
