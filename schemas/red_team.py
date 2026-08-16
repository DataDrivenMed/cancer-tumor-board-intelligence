from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RedTeamDisposition(str, Enum):
    CLEAR = "clear"
    CHALLENGED = "challenged"
    BLOCKED = "blocked"


class RedTeamSeverity(str, Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class ClinicalRedTeamFinding(BaseModel):
    code: str
    severity: RedTeamSeverity
    category: str
    issue: str
    effect_on_recommendation: str
    source_agent_ids: list[str] = Field(default_factory=list)
    recommendation_blocking: bool = False
    human_review_required: bool = False


class ClinicalRedTeamReport(BaseModel):
    agent_id: str = "clinical_red_team"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal["completed", "completed_with_limitations", "escalate_human"]
    disposition: RedTeamDisposition
    findings: list[ClinicalRedTeamFinding] = Field(default_factory=list)
    critical_count: int = 0
    major_count: int = 0
    blocking_count: int = 0
    challenged_agent_ids: list[str] = Field(default_factory=list)
    summary: str
    limitations: list[str] = Field(default_factory=list)
    safe_for_consensus: bool = False
