from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AppraisalStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


class RiskOfBiasJudgement(str, Enum):
    LOW = "low"
    SOME_CONCERNS = "some_concerns"
    HIGH = "high"
    UNCLEAR = "unclear"
    NOT_APPLICABLE = "not_applicable"


class ApplicabilityJudgement(str, Enum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNCLEAR = "unclear"


class FullTextFindingCode(str, Enum):
    FULL_TEXT_EMPTY = "full_text_empty"
    FULL_TEXT_HASH_MISMATCH = "full_text_hash_mismatch"
    PMID_MISMATCH = "pmid_mismatch"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    PICO_INCOMPLETE = "pico_incomplete"
    PICO_EXCERPT_NOT_EXACT = "pico_excerpt_not_exact"
    ENDPOINT_MISSING = "endpoint_missing"
    ENDPOINT_EXCERPT_NOT_EXACT = "endpoint_excerpt_not_exact"
    EFFECT_ESTIMATE_MISSING = "effect_estimate_missing"
    EFFECT_EXCERPT_NOT_EXACT = "effect_excerpt_not_exact"
    RISK_OF_BIAS_INCOMPLETE = "risk_of_bias_incomplete"
    APPLICABILITY_INCOMPLETE = "applicability_incomplete"
    CLAIM_NOT_FULL_TEXT_VERIFIED = "claim_not_full_text_verified"


class FullTextSourceSnapshot(BaseModel):
    pmid: str = Field(min_length=1)
    title: str = Field(min_length=1)
    full_text: str = Field(min_length=1)
    full_text_sha256: str = Field(min_length=64, max_length=64)
    source_url: str | None = None
    source_type: Literal["pmc_full_text", "publisher_full_text", "institution_authorized", "synthetic_fixture"]
    source_verified: bool = False

    @model_validator(mode="after")
    def _hash_shape(self):
        value = self.full_text_sha256.lower().strip()
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("full_text_sha256 must be a 64-character hexadecimal SHA-256 digest")
        self.full_text_sha256 = value
        return self


class PICOField(BaseModel):
    value: str = Field(min_length=1)
    source_excerpt: str = Field(min_length=1)
    source_locator: str | None = None


class StructuredPICO(BaseModel):
    population: PICOField
    intervention: PICOField | None = None
    comparator: PICOField | None = None
    outcome: PICOField


class EndpointRecord(BaseModel):
    name: str = Field(min_length=1)
    endpoint_type: Literal["primary", "secondary", "exploratory", "safety", "other"] = "other"
    source_excerpt: str = Field(min_length=1)
    source_locator: str | None = None


class EffectEstimate(BaseModel):
    endpoint_name: str = Field(min_length=1)
    effect_measure: str = Field(min_length=1)
    effect_value: str = Field(min_length=1)
    confidence_interval: str | None = None
    p_value: str | None = None
    absolute_effect: str | None = None
    source_excerpt: str = Field(min_length=1)
    source_locator: str | None = None


class RiskOfBiasAssessment(BaseModel):
    randomization: RiskOfBiasJudgement = RiskOfBiasJudgement.UNCLEAR
    deviations_from_intervention: RiskOfBiasJudgement = RiskOfBiasJudgement.UNCLEAR
    missing_outcome_data: RiskOfBiasJudgement = RiskOfBiasJudgement.UNCLEAR
    outcome_measurement: RiskOfBiasJudgement = RiskOfBiasJudgement.UNCLEAR
    selective_reporting: RiskOfBiasJudgement = RiskOfBiasJudgement.UNCLEAR
    overall: RiskOfBiasJudgement = RiskOfBiasJudgement.UNCLEAR
    reviewer_rationale: str = Field(min_length=1)
    human_verified: bool = False


class ApplicabilityAssessment(BaseModel):
    judgement: ApplicabilityJudgement = ApplicabilityJudgement.UNCLEAR
    disease_match: str = Field(min_length=1)
    disease_state_match: str = Field(min_length=1)
    population_match: str = Field(min_length=1)
    treatment_context_match: str = Field(min_length=1)
    molecular_context_match: str | None = None
    reviewer_rationale: str = Field(min_length=1)
    human_verified: bool = False


class FullTextAppraisalCandidate(BaseModel):
    appraisal_id: str = Field(min_length=3)
    pmid: str = Field(min_length=1)
    study_design: str = Field(min_length=1)
    pico: StructuredPICO
    endpoints: list[EndpointRecord] = Field(min_length=1)
    effect_estimates: list[EffectEstimate] = Field(default_factory=list)
    risk_of_bias: RiskOfBiasAssessment
    applicability: ApplicabilityAssessment
    linked_claim_ids: list[str] = Field(default_factory=list)
    human_verified: bool = False
    reviewer_note: str | None = None


class FullTextAppraisalFinding(BaseModel):
    code: FullTextFindingCode
    severity: Literal["warning", "error"]
    message: str
    field_path: str | None = None


class FullTextAppraisalReport(BaseModel):
    appraiser_version: str = "1.0.0"
    appraisal_id: str
    pmid: str
    status: AppraisalStatus
    findings: list[FullTextAppraisalFinding] = Field(default_factory=list)
    pico_verified: bool = False
    endpoints_verified: int = 0
    effect_estimates_verified: int = 0
    risk_of_bias_verified: bool = False
    applicability_verified: bool = False
    linked_claims_verified_for_full_text: list[str] = Field(default_factory=list)
    can_influence_synthesis: bool = False
    limitations: list[str] = Field(default_factory=list)
    summary: str
