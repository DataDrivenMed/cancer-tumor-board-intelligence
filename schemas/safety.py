from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SafetyEvidenceType(str, Enum):
    CONTRAINDICATION = "contraindication"
    WARNING = "warning"
    TOXICITY = "toxicity"
    INTERACTION = "interaction"
    MONITORING = "monitoring"
    DOSE_CONSIDERATION = "dose_consideration"


class SafetySeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyEvidenceRecord(BaseModel):
    evidence_id: str
    source_id: str
    source_title: str
    source_locator: str
    source_excerpt: str
    source_verified: bool = False
    human_verified: bool = False
    synthetic: bool = False

    therapy_terms: list[str] = Field(default_factory=list)
    disease_terms: list[str] = Field(default_factory=list)
    # Optional patient-context terms that must be represented before a conditional
    # warning/contraindication is treated as applicable to the case.
    trigger_terms: list[str] = Field(default_factory=list)
    evidence_type: SafetyEvidenceType
    severity: SafetySeverity
    safety_issue: str
    required_parameters: list[str] = Field(default_factory=list)
    contraindication: bool = False


class SafetyEvidenceStore(BaseModel):
    records: list[SafetyEvidenceRecord] = Field(default_factory=list)


class SafetyFinding(BaseModel):
    evidence_id: str
    evidence_type: SafetyEvidenceType
    severity: SafetySeverity
    therapy_terms_matched: list[str] = Field(default_factory=list)
    trigger_terms_matched: list[str] = Field(default_factory=list)
    safety_issue: str
    source_title: str
    source_locator: str
    source_excerpt: str
    required_parameters: list[str] = Field(default_factory=list)
    unresolved_parameters: list[str] = Field(default_factory=list)
    contraindication: bool = False
    recommendation_blocking: bool = False


class SafetyReport(BaseModel):
    agent_id: str = "safety"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal[
        "completed",
        "completed_with_limitations",
        "no_evidence_found",
        "source_unavailable",
        "abstain_domain",
    ]
    findings: list[SafetyFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    summary: str
    can_support_safety_claim: bool = False
    recommendation_blocking: bool = False
