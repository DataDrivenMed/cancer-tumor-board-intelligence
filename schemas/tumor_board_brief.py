from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BriefItem(BaseModel):
    label: str
    value: str
    epistemic_label: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class BriefSection(BaseModel):
    section_id: str
    title: str
    items: list[BriefItem] = Field(default_factory=list)
    section_note: str | None = None


class TumorBoardIntelligenceBrief(BaseModel):
    agent_id: str = "tumor_board_brief"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal["completed", "completed_with_limitations", "abstain"]
    decision_state: str
    decision_support_strength: str
    sections: list[BriefSection] = Field(default_factory=list)
    critical_warnings: list[str] = Field(default_factory=list)
    source_trace_count: int = 0
    safe_to_display: bool = False
    decision_support_only: bool = True
    summary: str
