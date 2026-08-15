from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GuidanceSourceType(str, Enum):
    FORMAL_GUIDELINE = "formal_guideline"
    CONSENSUS_GUIDELINE = "consensus_guideline"
    AUTHORITATIVE_EVIDENCE_SUMMARY = "authoritative_evidence_summary"
    REGULATORY = "regulatory"
    INSTITUTIONAL_POLICY = "institutional_policy"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


class GuidanceStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    LIMITED = "limited"
    NOT_STATED = "not_stated"


class GuidanceSource(BaseModel):
    source_id: str
    title: str
    organization: str
    source_type: GuidanceSourceType
    jurisdiction: str = "US"
    url: str | None = None
    version: str | None = None
    publication_date: date | None = None
    updated_date: date | None = None
    review_due_date: date | None = None
    accessed_date: date | None = None
    license_status: Literal["public", "licensed", "institution_authorized", "synthetic", "unknown"] = "unknown"
    verified: bool = False
    content_hash: str | None = None


class GuidanceRecommendation(BaseModel):
    recommendation_id: str
    source_id: str
    disease_terms: list[str] = Field(default_factory=list)
    disease_states: list[str] = Field(default_factory=list)
    question_domains: list[str] = Field(default_factory=list)
    recommendation_text: str
    source_excerpt: str
    source_locator: str | None = None
    strength: GuidanceStrength = GuidanceStrength.NOT_STATED
    evidence_level: str | None = None
    conditions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    effective_from: date | None = None
    effective_to: date | None = None
    source_verified: bool = False

    @model_validator(mode="after")
    def _verified_claim_requires_excerpt(self):
        if self.source_verified and not self.source_excerpt.strip():
            raise ValueError("Verified guidance recommendation requires a non-empty source_excerpt.")
        return self


class GuidanceMatch(BaseModel):
    recommendation_id: str
    source_id: str
    source_title: str
    organization: str
    source_type: GuidanceSourceType
    jurisdiction: str
    recommendation_text: str
    source_excerpt: str
    source_locator: str | None = None
    strength: GuidanceStrength
    evidence_level: str | None = None
    match_dimensions: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    epistemic_label: Literal[
        "guideline_supported",
        "consensus_supported",
        "authoritative_evidence_summary",
        "regulatory_supported",
        "institutional_policy_supported",
        "synthetic_fixture",
    ]
    current_on: date


class GuidelineReport(BaseModel):
    agent_id: str = "guideline"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal[
        "completed",
        "completed_with_limitations",
        "no_evidence_found",
        "source_unavailable",
        "verification_failed",
        "abstain_domain",
    ]
    matched_guidance: list[GuidanceMatch] = Field(default_factory=list)
    sources_considered: int = 0
    verified_sources_considered: int = 0
    recommendations_considered: int = 0
    verified_recommendations_considered: int = 0
    formal_guideline_matches: int = 0
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str
    can_support_guideline_claim: bool = False
