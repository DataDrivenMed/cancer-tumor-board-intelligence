from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from schemas.case import CancerTumorBoardCase


@dataclass(frozen=True)
class SemanticIntegrityFinding:
    code: str
    severity: str
    field: str
    message: str


_JSON_OBJECT_RE = re.compile(r"^\s*\{.*\}\s*$", re.DOTALL)
_NOT_STARTED_PATTERNS = (
    "has not yet started",
    "has not started",
    "not yet started",
    "not started",
    "planned but not started",
    "scheduled but not started",
)
_CURRENT_MEDICATION_MARKERS = (
    "currently taking",
    "currently on",
    "continues",
    "continue",
    "remains on",
    "taking ",
    "active medication",
    "current medication",
    "medication list",
)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _looks_like_serialized_json_object(value: Any) -> bool:
    if not isinstance(value, str) or not _JSON_OBJECT_RE.match(value):
        return False
    try:
        return isinstance(json.loads(value), dict)
    except Exception:
        return False


def _excerpt_from_provenance(item) -> str:
    excerpts = [p.source_excerpt for p in getattr(item, "provenance", []) if p.source_excerpt]
    return " ".join(excerpts)


def inspect_semantic_integrity(
    case: CancerTumorBoardCase,
    raw_extraction: dict[str, Any] | None = None,
) -> list[SemanticIntegrityFinding]:
    """Deterministic cross-field semantic checks after extraction.

    This gate does not infer diagnosis, stage, treatment response, or actionability.
    It checks whether the structured representation is internally compatible with
    explicit source-supported wording already carried in provenance/raw extraction.
    """
    findings: list[SemanticIntegrityFinding] = []
    raw = raw_extraction or {}

    # Check both the raw model output and the canonical case so this guard remains
    # active even when callers no longer retain raw_extraction.
    care_site_values = [raw.get("care_site"), case.care_site]
    if any(_looks_like_serialized_json_object(value) for value in care_site_values):
        findings.append(
            SemanticIntegrityFinding(
                code="SERIALIZED_JSON_IN_SCALAR",
                severity="error",
                field="care_site",
                message="care_site contains a serialized JSON object instead of null or a plain scalar value.",
            )
        )

    for treatment in case.treatments:
        excerpt = _norm(_excerpt_from_provenance(treatment))
        if any(pattern in excerpt for pattern in _NOT_STARTED_PATTERNS):
            findings.append(
                SemanticIntegrityFinding(
                    code="UNSTARTED_THERAPY_AS_ADMINISTERED",
                    severity="error",
                    field="treatments",
                    message=(
                        f"{treatment.regimen} is represented as a treatment episode even though its source provenance "
                        "explicitly states that treatment has not started."
                    ),
                )
            )

    for fact in case.current_medications:
        excerpt = _norm(_excerpt_from_provenance(fact))
        if excerpt and not any(marker in excerpt for marker in _CURRENT_MEDICATION_MARKERS):
            findings.append(
                SemanticIntegrityFinding(
                    code="CURRENT_MEDICATION_TEMPORALITY_UNVERIFIED",
                    severity="error",
                    field="current_medications",
                    message=(
                        f"{fact.field} is placed in current_medications without explicit source wording that it is current."
                    ),
                )
            )

    for fact in case.transplant_cellular_therapy:
        if getattr(fact.status, "value", fact.status) == "confirmed" and fact.value is None:
            findings.append(
                SemanticIntegrityFinding(
                    code="CONFIRMED_NULL_TRANSPLANT_VALUE",
                    severity="error",
                    field="transplant_cellular_therapy",
                    message=(
                        f"{fact.field} is marked confirmed but has a null value; the transplant/cellular-therapy representation is incomplete."
                    ),
                )
            )

    for fact in case.current_medications:
        if getattr(fact.status, "value", fact.status) == "confirmed" and fact.value is None:
            findings.append(
                SemanticIntegrityFinding(
                    code="CONFIRMED_NULL_CURRENT_MEDICATION_VALUE",
                    severity="error",
                    field="current_medications",
                    message=(
                        f"{fact.field} is marked confirmed but has a null value; the current-medication representation is incomplete."
                    ),
                )
            )

    return findings


def semantic_integrity_passes(findings: list[SemanticIntegrityFinding]) -> bool:
    return not any(f.severity in {"error", "critical"} for f in findings)
