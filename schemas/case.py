from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class InformationType(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    INTERPRETED = "interpreted"


class DataStatus(str, Enum):
    CONFIRMED = "confirmed"
    UNKNOWN = "unknown"
    NOT_DOCUMENTED = "not_documented"
    NOT_ASSESSED = "not_assessed"
    PENDING = "pending"
    NOT_APPLICABLE = "not_applicable"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"


class TreatmentStatus(str, Enum):
    PLANNED = "planned"
    ORDERED = "ordered"
    STARTED = "started"
    COMPLETED = "completed"
    STOPPED = "stopped"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class Provenance(BaseModel):
    document_id: str
    document_type: str | None = None
    source_section: str | None = None
    source_excerpt: str | None = None
    source_segment_ids: list[str] = Field(default_factory=list)
    source_verified: bool = False
    document_date: date | None = None
    author_role: str | None = None
    care_site: str | None = None
    page: int | None = None


class Fact(BaseModel):
    field: str
    value: Any = None
    status: DataStatus = DataStatus.CONFIRMED
    information_type: InformationType = InformationType.OBSERVED
    provenance: list[Provenance] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    human_verified: bool = False


class MolecularFinding(BaseModel):
    gene: str
    alteration_type: str | None = None
    hgvs_c: str | None = None
    hgvs_p: str | None = None
    variant_allele_frequency: float | None = None
    specimen_type: str | None = None
    specimen_date: date | None = None
    assay: str | None = None
    laboratory_interpretation: str | None = None
    provenance: list[Provenance] = Field(default_factory=list)
    human_verified: bool = False


class TreatmentEpisode(BaseModel):
    episode_id: str
    regimen: str
    treatment_status: TreatmentStatus = TreatmentStatus.UNKNOWN
    intent: str | None = None
    line_of_therapy: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    agents: list[str] = Field(default_factory=list)
    dose_modifications: list[str] = Field(default_factory=list)
    reason_stopped: str | None = None
    best_response: str | None = None
    toxicities: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=list)
    human_verified: bool = False


class ClinicalQuestion(BaseModel):
    question_type: str
    question: str
    urgency: str = "routine_tumor_board"


class Conflict(BaseModel):
    conflict_id: str
    field: str
    value_a: str
    value_b: str
    severity: Literal["low", "moderate", "high", "critical"]
    resolution_status: Literal["unresolved", "resolved"] = "unresolved"
    source_segment_ids: list[str] = Field(default_factory=list)


class MissingItem(BaseModel):
    field: str
    importance: Literal["low", "moderate", "high", "critical"]
    reason: str
    availability: str = "not_documented"
    recommendation_blocking: bool = False


class CancerTumorBoardCase(BaseModel):
    case_id: str
    case_type: Literal["synthetic", "deidentified_research", "prospective_silent", "clinical"] = "synthetic"
    disease_program: str = "hematologic_malignancy"
    tumor_board_type: str = "hematologic_malignancy_board"
    schema_version: str = "0.3.0"

    care_site: str | None = None
    age: int | None = Field(default=None, ge=0, le=130)
    sex: str | None = None

    diagnosis: Fact
    disease_state: Fact
    performance_status: Fact | None = None

    pathology: list[Fact] = Field(default_factory=list)
    molecular_findings: list[MolecularFinding] = Field(default_factory=list)
    imaging: list[Fact] = Field(default_factory=list)
    labs: list[Fact] = Field(default_factory=list)
    comorbidities: list[Fact] = Field(default_factory=list)
    treatments: list[TreatmentEpisode] = Field(default_factory=list)
    toxicities: list[Fact] = Field(default_factory=list)
    transplant_cellular_therapy: list[Fact] = Field(default_factory=list)
    current_medications: list[Fact] = Field(default_factory=list)

    clinical_question: ClinicalQuestion
    conflicts: list[Conflict] = Field(default_factory=list)
    missing_items: list[MissingItem] = Field(default_factory=list)
    source_documents: list[str] = Field(default_factory=list)
