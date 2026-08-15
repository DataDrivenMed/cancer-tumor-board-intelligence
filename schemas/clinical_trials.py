from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class TrialLocation(BaseModel):
    facility: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class TrialRecord(BaseModel):
    nct_id: str
    title: str
    overall_status: str | None = None
    study_type: str | None = None
    phases: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    interventions: list[str] = Field(default_factory=list)
    eligibility_criteria: str | None = None
    minimum_age: str | None = None
    maximum_age: str | None = None
    sex: str | None = None
    locations: list[TrialLocation] = Field(default_factory=list)
    last_update_post_date: date | None = None
    source_url: str
    source_verified: bool = True


class TrialSearchTrace(BaseModel):
    query_condition: str
    query_terms: list[str] = Field(default_factory=list)
    requested_limit: int
    returned_count: int = 0
    api_version: str = "v2"
    data_timestamp: str | None = None


class TrialMatch(BaseModel):
    nct_id: str
    title: str
    overall_status: str | None = None
    matched_concepts: list[str] = Field(default_factory=list)
    unresolved_eligibility_domains: list[str] = Field(default_factory=list)
    eligibility_determined: bool = False
    eligible: bool | None = None
    match_strength: Literal["possible", "contextual"] = "possible"
    rationale: str
    source_url: str


class ClinicalTrialsReport(BaseModel):
    agent_id: str = "clinical_trials"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal[
        "completed",
        "completed_with_limitations",
        "no_evidence_found",
        "source_unavailable",
        "tool_failure",
        "abstain_domain",
    ]
    search_trace: TrialSearchTrace | None = None
    records: list[TrialRecord] = Field(default_factory=list)
    matches: list[TrialMatch] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str
    can_support_trial_match_claim: bool = False
    can_support_eligibility_claim: bool = False
