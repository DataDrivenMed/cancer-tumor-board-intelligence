from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

from schemas.guideline import GuidanceSourceType, GuidanceStrength


class EvidenceIngestionStatus(str, Enum):
    ACCEPTED = "accepted"
    ACCEPTED_WITH_LIMITATIONS = "accepted_with_limitations"
    REJECTED = "rejected"


class EvidenceVerificationCode(str, Enum):
    SOURCE_ID_INVALID = "source_id_invalid"
    SOURCE_URL_REQUIRED = "source_url_required"
    LICENSE_NOT_AUTHORIZED = "license_not_authorized"
    SOURCE_CONTENT_EMPTY = "source_content_empty"
    CONTENT_HASH_MISMATCH = "content_hash_mismatch"
    SOURCE_NOT_HUMAN_VERIFIED = "source_not_human_verified"
    SOURCE_TYPE_MISMATCH = "source_type_mismatch"
    RECOMMENDATION_SOURCE_MISMATCH = "recommendation_source_mismatch"
    RECOMMENDATION_EXCERPT_MISSING = "recommendation_excerpt_missing"
    RECOMMENDATION_EXCERPT_NOT_EXACT = "recommendation_excerpt_not_exact"
    SOURCE_LOCATOR_MISSING = "source_locator_missing"
    RECOMMENDATION_NOT_HUMAN_VERIFIED = "recommendation_not_human_verified"
    SYNTHETIC_SOURCE_PRODUCTION_BLOCK = "synthetic_source_production_block"


class EvidenceSourceManifest(BaseModel):
    source_id: str = Field(min_length=3)
    title: str = Field(min_length=1)
    organization: str = Field(min_length=1)
    source_type: GuidanceSourceType
    jurisdiction: str = "US"
    url: HttpUrl
    version: str | None = None
    publication_date: date | None = None
    updated_date: date | None = None
    review_due_date: date | None = None
    accessed_date: date
    license_status: Literal["public", "licensed", "institution_authorized", "synthetic", "unknown"]
    expected_content_sha256: str
    human_verified: bool = False
    verification_note: str | None = None

    @model_validator(mode="after")
    def _hash_shape(self):
        value = self.expected_content_sha256.lower().strip()
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("expected_content_sha256 must be a 64-character hexadecimal SHA-256 digest")
        self.expected_content_sha256 = value
        return self


class EvidenceRecommendationRecord(BaseModel):
    recommendation_id: str = Field(min_length=3)
    source_id: str = Field(min_length=3)
    disease_terms: list[str] = Field(default_factory=list)
    disease_states: list[str] = Field(default_factory=list)
    question_domains: list[str] = Field(default_factory=list)
    recommendation_text: str = Field(min_length=1)
    source_excerpt: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    strength: GuidanceStrength = GuidanceStrength.NOT_STATED
    evidence_level: str | None = None
    conditions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    effective_from: date | None = None
    effective_to: date | None = None
    human_verified: bool = False


class EvidenceIngestionPackage(BaseModel):
    manifest: EvidenceSourceManifest
    source_text: str
    recommendations: list[EvidenceRecommendationRecord] = Field(default_factory=list)
    package_created_utc: datetime | None = None
    package_note: str | None = None


class EvidenceVerificationFinding(BaseModel):
    code: EvidenceVerificationCode
    severity: Literal["warning", "error"]
    message: str
    recommendation_id: str | None = None


class EvidenceIngestionResult(BaseModel):
    gateway_version: str = "1.0.0"
    source_id: str
    status: EvidenceIngestionStatus
    content_sha256: str
    source_verified: bool
    accepted_recommendation_ids: list[str] = Field(default_factory=list)
    rejected_recommendation_ids: list[str] = Field(default_factory=list)
    findings: list[EvidenceVerificationFinding] = Field(default_factory=list)
    source_count: int = 0
    recommendation_count: int = 0
    can_enter_guideline_store: bool = False
