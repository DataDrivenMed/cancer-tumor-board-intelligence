from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ConsensusDisposition(str, Enum):
    READY = "ready"
    CONDITIONAL = "conditional"
    ABSTAIN = "abstain"


class EvidenceChannelState(str, Enum):
    SUPPORTIVE = "supportive"
    LIMITING = "limiting"
    UNAVAILABLE = "unavailable"
    NON_DECISIONAL = "non_decisional"
    NOT_SELECTED = "not_selected"


class ConsensusEvidenceChannel(BaseModel):
    agent_id: str
    state: EvidenceChannelState
    status: str
    supports_decision: bool = False
    rationale: str


class ConsensusCandidate(BaseModel):
    candidate_id: str
    strategy: str
    source_agent_id: str
    source_record_id: str
    source_type: str
    evidence_strength: str | None = None
    source_excerpt: str
    source_locator: str | None = None
    conditions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)


class ConsensusReport(BaseModel):
    agent_id: str = "consensus"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal["completed", "completed_with_limitations", "escalate_human"]
    disposition: ConsensusDisposition
    decision_state: Literal[
        "preferred_conditional",
        "multiple_reasonable_options",
        "abstain",
    ]
    decision_support_strength: Literal["moderate", "low", "insufficient"]
    candidates: list[ConsensusCandidate] = Field(default_factory=list)
    evidence_channels: list[ConsensusEvidenceChannel] = Field(default_factory=list)
    red_team_challenges: list[str] = Field(default_factory=list)
    major_uncertainties: list[str] = Field(default_factory=list)
    discussion_priorities: list[str] = Field(default_factory=list)
    summary: str
    abstention_reason: str | None = None
    safe_to_render_decision_support: bool = False
