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
    tags: List[str] = Field(default_factory=list)
    legal_relevance: str = "Onbekend"
    chain_of_custody: List[str] = Field(default_factory=list)


class EvidenceUploadResponse(BaseModel):
    evidence: EvidenceItem
    analysis: "DocumentAnalysis"


class PersonDossier(BaseModel):
    person_name: str
    case_name: str
    facts: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    inconsistencies: List[str] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    event_id: str
    timestamp: str
    title: str
    description: str
    related_evidence_ids: List[str] = Field(default_factory=list)
    confidence: str = "medium"


class DocumentAnalysis(BaseModel):
    summary: str
    legal_entities: List[str] = Field(default_factory=list)
    detected_risks: List[str] = Field(default_factory=list)
    behavior_signals: List[str] = Field(default_factory=list)
    timeline_events: List[TimelineEvent] = Field(default_factory=list)


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
    analyses: Dict[str, DocumentAnalysis] = Field(default_factory=dict)
    timeline: List[TimelineEvent] = Field(default_factory=list)


class DossierBuilderRequest(BaseModel):
    query: Optional[str] = ""
    filters: SearchFilters = Field(default_factory=SearchFilters)
    selected_evidence_ids: List[str] = Field(default_factory=list)


class DashboardSummary(BaseModel):
    total_evidence: int
    total_dossiers: int
    high_relevance_evidence: int
    open_risk_flags: int
    latest_events: List[TimelineEvent] = Field(default_factory=list)


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
    facts: List[str] = Field(default_factory=list)
    statements: List[str] = Field(default_factory=list)
    behavior_changes: List[str] = Field(default_factory=list)
    inconsistencies: List[str] = Field(default_factory=list)
    motives: List[str] = Field(default_factory=list)
    possible_interests: List[str] = Field(default_factory=list)
    medical_context: List[str] = Field(default_factory=list)


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
    personal_data_detected: List[str] = Field(default_factory=list)
    processing_basis: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    safeguards: List[str] = Field(default_factory=list)


class ForensicReport(BaseModel):
    generated_at: str
    command: str
    dossier_overview: str
    evidence_index: List[ForensicEvidenceIndexItem] = Field(default_factory=list)
    chronology: List[TimelineEvent] = Field(default_factory=list)
    timeline_gaps: List[TimelineGap] = Field(default_factory=list)
    labeled_statements: List[LabeledStatement] = Field(default_factory=list)
    profiles: List[PersonProfile] = Field(default_factory=list)
    scenarios: List[CounterpartyScenario] = Field(default_factory=list)
    legal_relevance: List[str] = Field(default_factory=list)
    framing_risks: List[str] = Field(default_factory=list)
    lawyer_summary: str
    active_status: str
    privacy_assessment: PrivacyAssessment


class ForensicCommandRequest(BaseModel):
    command: str = Field(description="Ondersteunt: ANALYSE STARTEN, SCENARIO'S TONEN, EINDRAPPORT")
    root_path: Optional[str] = Field(default=None, description="Optioneel pad voor analyse")
