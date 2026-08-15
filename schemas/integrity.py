from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class IntegritySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    MAJOR = "major"
    CRITICAL = "critical"


class IntegrityDisposition(str, Enum):
    PASS = "pass"
    PASS_WITH_WARNINGS = "pass_with_warnings"
    BLOCK = "block"


class IntegrityFinding(BaseModel):
    finding_id: str
    code: str
    severity: IntegritySeverity
    category: Literal[
        "provenance",
        "missing_information",
        "conflict",
        "diagnostic_certainty",
        "treatment",
        "temporal_consistency",
        "schema_consistency",
    ]
    field_path: str
    message: str
    recommendation_blocking: bool = False
    source_segment_ids: list[str] = Field(default_factory=list)


class IntegrityCheckResult(BaseModel):
    check_id: str
    check_version: str
    passed: bool
    findings: list[IntegrityFinding] = Field(default_factory=list)


class CaseIntegrityReport(BaseModel):
    agent_id: str = "case_integrity"
    agent_version: str = "1.0.0"
    case_id: str
    disposition: IntegrityDisposition
    checks_run: int
    checks_passed: int
    critical_count: int = 0
    major_count: int = 0
    warning_count: int = 0
    recommendation_blocking_count: int = 0
    findings: list[IntegrityFinding] = Field(default_factory=list)
    check_results: list[IntegrityCheckResult] = Field(default_factory=list)
    requires_human_review: bool = False
    safe_to_route_to_specialists: bool = False
