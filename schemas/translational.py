from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class TranslationalEvidenceTier(str, Enum):
    T1_HUMAN_TRANSLATIONAL = "t1_human_translational"
    T2_IN_VIVO_PRECLINICAL = "t2_in_vivo_preclinical"
    T3_IN_VITRO_PRECLINICAL = "t3_in_vitro_preclinical"
    HYPOTHESIS_ONLY = "hypothesis_only"


class TranslationalDirection(str, Enum):
    SUPPORTS_MECHANISM = "supports_mechanism"
    SUPPORTS_SENSITIVITY = "supports_sensitivity"
    SUPPORTS_RESISTANCE = "supports_resistance"
    CONTRADICTS = "contradicts"
    MIXED = "mixed"
    UNCLEAR = "unclear"


class TranslationalEvidenceRecord(BaseModel):
    evidence_id: str
    source_id: str
    gene: str | None = None
    alteration_terms: list[str] = Field(default_factory=list)
    disease_terms: list[str] = Field(default_factory=list)
    model_system: str
    evidence_tier: TranslationalEvidenceTier
    direction: TranslationalDirection
    mechanism: str
    intervention: str | None = None
    source_excerpt: str
    source_locator: str
    source_verified: bool = False
    human_verified: bool = False
    synthetic: bool = False


class TranslationalEvidenceStore(BaseModel):
    records: list[TranslationalEvidenceRecord] = Field(default_factory=list)


class TranslationalFinding(BaseModel):
    subject: str
    matched_evidence_ids: list[str] = Field(default_factory=list)
    evidence_tiers: list[TranslationalEvidenceTier] = Field(default_factory=list)
    directions: list[TranslationalDirection] = Field(default_factory=list)
    mechanisms: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    strongest_tier: TranslationalEvidenceTier | None = None
    human_translational_support: bool = False
    clinical_actionability_claim: bool = False
    limitations: list[str] = Field(default_factory=list)


class TranslationalReport(BaseModel):
    agent_id: str = "translational"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal[
        "completed",
        "completed_with_limitations",
        "no_evidence_found",
        "source_unavailable",
        "abstain_domain",
    ]
    findings: list[TranslationalFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    summary: str
    can_support_mechanistic_claim: bool = False
    can_support_clinical_actionability_claim: bool = False
