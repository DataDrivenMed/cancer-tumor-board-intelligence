from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class MissingInformationDisposition(str, Enum):
    READY = "ready"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"


class MissingInformationPriority(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class MissingInformationAction(str, Enum):
    OBTAIN = "obtain"
    VERIFY = "verify"
    RESOLVE_CONFLICT = "resolve_conflict"
    REVIEW = "review"


class MissingInformationItem(BaseModel):
    item_id: str
    field: str
    category: Literal[
        "diagnostic_clarification",
        "pathology",
        "molecular",
        "performance_status",
        "disease_state",
        "treatment_history",
        "treatment_plan",
        "conflict_resolution",
        "other",
    ]
    priority: MissingInformationPriority
    reason: str
    availability: str = "not_documented"
    recommendation_blocking: bool = False
    action: MissingInformationAction
    source: Literal["canonical_missing_item", "structural_rule", "conflict_rule"]
    field_path: str | None = None
    source_segment_ids: list[str] = Field(default_factory=list)
    priority_score: int = Field(ge=0, le=100)


class MissingInformationReport(BaseModel):
    agent_id: str = "missing_information"
    agent_version: str = "1.0.0"
    case_id: str
    disposition: MissingInformationDisposition
    items: list[MissingInformationItem] = Field(default_factory=list)
    blocking_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    moderate_count: int = 0
    low_count: int = 0
    safe_to_route_to_specialists: bool = True
    requires_human_review: bool = False
    summary: str = ""
