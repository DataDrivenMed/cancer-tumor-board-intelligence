from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class MolecularEvidenceTier(str, Enum):
    REGULATORY = "regulatory"
    GUIDELINE = "guideline"
    CLINICAL = "clinical"
    CONSENSUS = "consensus"
    PRECLINICAL = "preclinical"
    SYNTHETIC = "synthetic"


class MolecularEvidenceDirection(str, Enum):
    SUPPORTS_SENSITIVITY = "supports_sensitivity"
    SUPPORTS_RESISTANCE = "supports_resistance"
    PROGNOSTIC = "prognostic"
    DIAGNOSTIC = "diagnostic"
    BIOLOGIC = "biologic"
    UNCLEAR = "unclear"


class ClinicalActionability(str, Enum):
    ESTABLISHED = "established"
    EMERGING = "emerging"
    INVESTIGATIONAL = "investigational"
    NOT_ESTABLISHED = "not_established"
    UNKNOWN = "unknown"


class MolecularEvidenceRecord(BaseModel):
    evidence_id: str = Field(min_length=3)
    source_id: str = Field(min_length=3)
    source_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    source_type: MolecularEvidenceTier
    jurisdiction: str = "US"
    publication_date: date | None = None
    accessed_date: date
    disease_terms: list[str] = Field(default_factory=list)
    gene: str = Field(min_length=1)
    alteration_terms: list[str] = Field(default_factory=list)
    direction: MolecularEvidenceDirection = MolecularEvidenceDirection.UNCLEAR
    actionability: ClinicalActionability = ClinicalActionability.UNKNOWN
    therapy: str | None = None
    evidence_summary: str = Field(min_length=1)
    source_excerpt: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    source_verified: bool = False
    human_verified: bool = False
    synthetic: bool = False


class MolecularFindingInterpretation(BaseModel):
    gene: str
    alteration: str | None = None
    matched_evidence_ids: list[str] = Field(default_factory=list)
    evidence_directions: list[MolecularEvidenceDirection] = Field(default_factory=list)
    therapies: list[str] = Field(default_factory=list)
    biologic_relevance: Literal["supported", "uncertain", "not_assessed"] = "not_assessed"
    clinical_actionability: ClinicalActionability = ClinicalActionability.UNKNOWN
    resistance_signal: bool = False
    diagnostic_signal: bool = False
    prognostic_signal: bool = False
    limitations: list[str] = Field(default_factory=list)
    can_support_clinical_actionability_claim: bool = False


class MolecularReport(BaseModel):
    agent_id: str = "molecular"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal[
        "completed",
        "completed_with_limitations",
        "no_evidence_found",
        "source_unavailable",
        "abstain_domain",
        "verification_failed",
    ]
    interpretations: list[MolecularFindingInterpretation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    summary: str
    can_support_clinical_actionability_claim: bool = False


class MolecularEvidenceStore(BaseModel):
    records: list[MolecularEvidenceRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_ids(self):
        ids = [r.evidence_id for r in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("Molecular evidence_id values must be unique")
        return self
