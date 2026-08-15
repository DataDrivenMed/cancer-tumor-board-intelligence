from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from services.document_parser import ParsedDocument
from services.extraction_audit import NormalizationEvent, make_normalization_event


DISEASE_STATE_RESOLVER_VERSION = "1.0.0"


_PLACEHOLDER_STATUSES = {
    "",
    "unknown",
    "not_documented",
    "not documented",
    "not_assessed",
    "not assessed",
    "pending",
    "unavailable",
}

_UNCERTAINTY_MARKERS = (
    "suspected",
    "possible",
    "probable",
    "concern for",
    "cannot exclude",
    "may represent",
    "may be",
)

_NEGATION_MARKERS = (
    "no evidence of",
    "without",
    "negative for",
    "not metastatic",
    "no metastatic",
    "no metastasis",
    "no metastases",
)

# Ordered only for deterministic reporting. We never choose among multiple distinct
# candidate states; ambiguity is preserved instead of adjudicated.
_STATE_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("newly diagnosed", re.compile(r"\bnewly[- ]diagnosed\b", re.I), "observed"),
    ("relapsed", re.compile(r"\brelaps(?:e|ed)\b", re.I), "observed"),
    ("recurrent", re.compile(r"\brecurr(?:ent|ence)\b", re.I), "observed"),
    ("refractory", re.compile(r"\brefractory\b", re.I), "observed"),
    (
        "progressive",
        re.compile(r"\bprogressive disease\b|\bdisease progression\b|\bradiographic progression\b|\bprogression\b", re.I),
        "observed",
    ),
    ("persistent", re.compile(r"\bpersistent disease\b", re.I), "observed"),
    ("remission", re.compile(r"\bin remission\b|\bremission\b", re.I), "observed"),
    ("metastatic", re.compile(r"\bmetastatic\b", re.I), "observed"),
    ("metastatic", re.compile(r"\bmetastas(?:is|es)\b", re.I), "derived"),
)


@dataclass(frozen=True)
class DiseaseStateResolution:
    payload: dict[str, Any]
    events: list[NormalizationEvent]
    warnings: list[str]


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _is_missing_disease_state(payload: dict[str, Any]) -> bool:
    disease_state = payload.get("disease_state")
    if not isinstance(disease_state, dict):
        return True
    value = disease_state.get("value")
    status = _norm(disease_state.get("status"))
    return value is None or _norm(value) in _PLACEHOLDER_STATUSES or status in _PLACEHOLDER_STATUSES


def _has_disease_state_conflict(payload: dict[str, Any]) -> bool:
    for conflict in payload.get("conflicts", []) or []:
        field = _norm(conflict.get("field"))
        if "disease state" in field or "stage" in field or "progress" in field or "response" in field:
            return True
    return False


def _window(text: str, start: int, end: int, radius: int = 48) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)].lower()


def _is_uncertain_or_negated(text: str, start: int, end: int) -> bool:
    context = _window(text, start, end)
    if any(marker in context for marker in _NEGATION_MARKERS):
        return True

    # Restrict uncertainty handling to the local phrase so a remote "suspected"
    # does not suppress an otherwise explicit current-state statement.
    local_left = text[max(0, start - 35):start].lower()
    local_right = text[end:min(len(text), end + 20)].lower()
    local = local_left + text[start:end].lower() + local_right
    return any(marker in local for marker in _UNCERTAINTY_MARKERS)


def _candidate_states(document: ParsedDocument) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for segment in document.segments:
        text = segment.text
        for canonical, pattern, information_type in _STATE_PATTERNS:
            for match in pattern.finditer(text):
                if _is_uncertain_or_negated(text, match.start(), match.end()):
                    continue
                candidates.append(
                    {
                        "canonical": canonical,
                        "information_type": information_type,
                        "source_segment_ids": [segment.segment_id],
                        "source_excerpt": match.group(0),
                    }
                )
    return candidates


def resolve_disease_state(
    *,
    document: ParsedDocument,
    payload: dict[str, Any],
) -> DiseaseStateResolution:
    """Promote only explicit, unambiguous source-supported disease-state evidence.

    This resolver runs after model extraction. It never overwrites a substantive
    model disease state, never adjudicates a conflict, and never uses external
    medical knowledge. A source phrase such as "liver metastases" can support a
    derived canonical state of "metastatic" because the metastatic concept is
    directly present in the source text. Uncertain/negated mentions are ignored.
    """

    out = deepcopy(payload)
    events: list[NormalizationEvent] = []
    warnings: list[str] = []

    if not _is_missing_disease_state(out):
        return DiseaseStateResolution(out, events, warnings)
    if _has_disease_state_conflict(out):
        warnings.append("Disease-state resolver abstained because a relevant unresolved conflict is present.")
        return DiseaseStateResolution(out, events, warnings)

    candidates = _candidate_states(document)
    canonical_states = sorted({candidate["canonical"] for candidate in candidates})
    if not canonical_states:
        return DiseaseStateResolution(out, events, warnings)
    if len(canonical_states) != 1:
        warnings.append(
            "Disease-state resolver found multiple distinct explicit state candidates and abstained: "
            + ", ".join(canonical_states)
        )
        return DiseaseStateResolution(out, events, warnings)

    canonical = canonical_states[0]
    matching = [candidate for candidate in candidates if candidate["canonical"] == canonical]
    # Prefer a directly observed adjective/state phrase over a derived plural-noun
    # form when both are present, but both remain source-grounded.
    selected = next((item for item in matching if item["information_type"] == "observed"), matching[0])

    before = deepcopy(out.get("disease_state"))
    field = "disease_state"
    after = {
        "field": field,
        "value": canonical,
        "status": "confirmed",
        "confidence": 1.0,
        "source_segment_ids": selected["source_segment_ids"],
        "source_excerpt": selected["source_excerpt"],
        "information_type": selected["information_type"],
    }
    out["disease_state"] = after
    warning = (
        f"Disease-state consistency resolver populated '{canonical}' from explicit source-supported evidence "
        "because the primary extraction left disease_state unresolved."
    )
    out.setdefault("extraction_warnings", [])
    if warning not in out["extraction_warnings"]:
        out["extraction_warnings"].append(warning)
    warnings.append(warning)
    events.append(
        make_normalization_event(
            rule="disease_state_consistency_resolver",
            field_path="disease_state",
            before=before,
            after=after,
            reason=warning,
            source_segment_ids=selected["source_segment_ids"],
            source_excerpt=selected["source_excerpt"],
        )
    )
    return DiseaseStateResolution(out, events, warnings)
