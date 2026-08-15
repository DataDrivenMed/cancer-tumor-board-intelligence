from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    COMPLETED = "completed"
    COMPLETED_WITH_LIMITATIONS = "completed_with_limitations"
    INSUFFICIENT_INPUT = "insufficient_input"
    NO_EVIDENCE_FOUND = "no_evidence_found"
    SOURCE_UNAVAILABLE = "source_unavailable"
    VERIFICATION_FAILED = "verification_failed"
    SCHEMA_ERROR = "schema_error"
    TOOL_FAILURE = "tool_failure"
    ABSTAIN_DOMAIN = "abstain_domain"
    ESCALATE_HUMAN = "escalate_human"


class EvidenceClaim(BaseModel):
    claim_id: str
    claim: str
    epistemic_status: str
    source_ids: list[str] = Field(default_factory=list)
    verification_status: Literal["not_checked", "verified", "partially_verified", "conflicting", "rejected"] = "not_checked"


class AgentOutput(BaseModel):
    agent_id: str
    agent_version: str = "0.1.0"
    status: AgentStatus = AgentStatus.COMPLETED
    summary: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    evidence_claims: list[EvidenceClaim] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_followup: bool = False


class RoutingDecision(BaseModel):
    question_type: str
    complexity: Literal["routine", "intermediate", "complex", "high_complexity"]
    selected_agents: list[str]
    rationale: list[str] = Field(default_factory=list)


class RedTeamFinding(BaseModel):
    severity: Literal["minor", "moderate", "major", "critical"]
    category: str
    issue: str
    effect_on_recommendation: str


class FinalDecision(BaseModel):
    decision_state: Literal["strongly_supported", "preferred_conditional", "multiple_reasonable_options", "trial_centered", "abstain"]
    primary_strategy: str | None = None
    alternatives: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    major_uncertainties: list[str] = Field(default_factory=list)
    discussion_priorities: list[str] = Field(default_factory=list)
    decision_support_strength: Literal["high", "moderate", "low", "insufficient"] = "insufficient"
    abstention_reason: str | None = None
