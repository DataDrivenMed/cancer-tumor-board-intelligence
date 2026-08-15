from __future__ import annotations

import re
from dataclasses import dataclass

from services.document_parser import ParsedDocument


_STAGE_PATTERN = re.compile(r"\bstage\s+(?:is\s+)?(iv|iii|ii|i|[1-4])\b", re.IGNORECASE)
_STAGE_CANONICAL = {
    "i": "I",
    "1": "I",
    "ii": "II",
    "2": "II",
    "iii": "III",
    "3": "III",
    "iv": "IV",
    "4": "IV",
}


@dataclass(frozen=True)
class ExplicitConflictRecovery:
    conflicts: list[dict]
    recovered: bool
    warnings: list[str]


def _normalise_field(value: str) -> str:
    return " ".join((value or "").lower().replace("_", " ").split())


def _has_stage_conflict(conflicts: list[dict]) -> bool:
    return any("stage" in _normalise_field(item.get("field", "")) for item in conflicts)


def _explicit_stage_mentions(document: ParsedDocument) -> list[tuple[str, str]]:
    """Return unique, source-explicit stage values with authoritative segment IDs.

    This deliberately recognises only explicit strings such as ``stage III`` or
    ``stage 4``. It does not infer stage from anatomy, imaging findings, or outside
    medical knowledge.
    """
    mentions: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for segment in document.segments:
        for match in _STAGE_PATTERN.finditer(segment.text):
            canonical = _STAGE_CANONICAL[match.group(1).lower()]
            key = (canonical, segment.segment_id)
            if key not in seen:
                seen.add(key)
                mentions.append(key)
    return mentions


def recover_explicit_conflicts(
    *,
    document: ParsedDocument,
    conflicts: list[dict] | None,
    missing_items: list[dict] | None = None,
) -> ExplicitConflictRecovery:
    """Recover only contradictions that can be proven deterministically from source text.

    The current deterministic rule handles explicit disease-stage disagreements.
    It never converts a single stage mention into a conflict, never derives stage
    from clinical findings, and never overwrites a model-produced conflict.
    """
    result = [dict(item) for item in (conflicts or [])]
    warnings: list[str] = []

    if _has_stage_conflict(result):
        return ExplicitConflictRecovery(result, False, warnings)

    mentions = _explicit_stage_mentions(document)
    distinct_values: list[str] = []
    segment_ids: list[str] = []
    for value, segment_id in mentions:
        if value not in distinct_values:
            distinct_values.append(value)
        if segment_id not in segment_ids:
            segment_ids.append(segment_id)

    if len(distinct_values) < 2:
        return ExplicitConflictRecovery(result, False, warnings)

    # Require corroborating unresolved/discrepancy language from either the source
    # or the model's missing-information layer before auto-constructing a conflict.
    source_text = document.full_text.lower()
    missing_text = " ".join(
        f"{item.get('field', '')} {item.get('reason', '')}" for item in (missing_items or [])
    ).lower()
    conflict_cues = (
        "discrepancy",
        "conflict",
        "discordant",
        "inconsistent",
        "unresolved",
        "differs",
        "different",
    )
    if not any(cue in source_text or cue in missing_text for cue in conflict_cues):
        warnings.append(
            "Multiple explicit stage values were found, but no conflict was auto-created because no discrepancy/unresolved cue was present."
        )
        return ExplicitConflictRecovery(result, False, warnings)

    result.append(
        {
            "field": "disease_stage",
            "value_a": f"stage {distinct_values[0]}",
            "value_b": f"stage {distinct_values[1]}",
            "severity": "moderate",
            "source_segment_ids": segment_ids,
        }
    )
    warnings.append(
        "Deterministic consistency gate recovered an explicit disease-stage conflict from two source-supported stage statements."
    )
    return ExplicitConflictRecovery(result, True, warnings)
