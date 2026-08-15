from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceClaimStatus(str, Enum):
    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    CONFLICTING = "conflicting"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


class EvidenceDirection(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    MIXED = "mixed"
    UNCLEAR = "unclear"


class EvidenceClaimType(str, Enum):
    EFFICACY = "efficacy"
    SAFETY = "safety"
    PROGNOSTIC = "prognostic"
    DIAGNOSTIC = "diagnostic"
    BIOMARKER = "biomarker"
    MECHANISTIC = "mechanistic"
    OTHER = "other"


class VerificationFindingCode(str, Enum):
    PMID_NOT_RETRIEVED = "pmid_not_retrieved"
    SOURCE_NOT_VERIFIED = "source_not_verified"
    ABSTRACT_UNAVAILABLE = "abstract_unavailable"
    ABSTRACT_HASH_MISSING = "abstract_hash_missing"
    ABSTRACT_HASH_MISMATCH = "abstract_hash_mismatch"
    SOURCE_EXCERPT_MISSING = "source_excerpt_missing"
    SOURCE_EXCERPT_NOT_EXACT = "source_excerpt_not_exact"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    STUDY_DESIGN_MISSING = "study_design_missing"
    POPULATION_MISSING = "population_missing"
    ENDPOINTS_MISSING = "endpoints_missing"
    NUMERIC_RESULTS_MISSING = "numeric_results_missing"
    APPLICABILITY_NOT_ASSESSED = "applicability_not_assessed"
    CONTRADICTION_PRESENT = "contradiction_present"


class EvidenceClaimCandidate(BaseModel):
    claim_id: str = Field(min_length=3)
    claim_text: str = Field(min_length=1)
    claim_type: EvidenceClaimType
    pmid: str = Field(min_length=1)
    abstract_sha256: str = Field(min_length=64, max_length=64)
    source_excerpt: str = Field(min_length=1)
    study_design: str | None = None
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    endpoints: list[str] = Field(default_factory=list)
    numeric_results: list[str] = Field(default_factory=list)
    applicability: str | None = None
    direction: EvidenceDirection = EvidenceDirection.UNCLEAR
    human_verified: bool = False
    reviewer_note: str | None = None

    @model_validator(mode="after")
    def _hash_shape(self):
        value = self.abstract_sha256.lower().strip()
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("abstract_sha256 must be a 64-character hexadecimal SHA-256 digest")
        self.abstract_sha256 = value
        return self


class EvidenceSourceSnapshot(BaseModel):
    pmid: str
    title: str
    abstract_text: str
    abstract_sha256: str
    source_verified: bool = True
    publication_types: list[str] = Field(default_factory=list)


class EvidenceVerificationFinding(BaseModel):
    code: VerificationFindingCode
    severity: Literal["warning", "error"]
    message: str


class VerifiedEvidenceClaim(BaseModel):
    claim_id: str
    claim_text: str
    claim_type: EvidenceClaimType
    pmid: str
    status: EvidenceClaimStatus
    direction: EvidenceDirection
    source_excerpt: str
    study_design: str | None = None
    population: str | None = None
    intervention: str | None = None
    comparator: str | None = None
    endpoints: list[str] = Field(default_factory=list)
    numeric_results: list[str] = Field(default_factory=list)
    applicability: str | None = None
    findings: list[EvidenceVerificationFinding] = Field(default_factory=list)
    can_influence_synthesis: bool = False


class EvidenceVerifierReport(BaseModel):
    verifier_version: str = "1.0.0"
    status: Literal["completed", "completed_with_limitations", "verification_failed"]
    claims: list[VerifiedEvidenceClaim] = Field(default_factory=list)
    verified_count: int = 0
    partially_verified_count: int = 0
    conflicting_count: int = 0
    rejected_count: int = 0
    unverified_count: int = 0
    can_support_clinical_synthesis: bool = False
    limitations: list[str] = Field(default_factory=list)
    summary: str
