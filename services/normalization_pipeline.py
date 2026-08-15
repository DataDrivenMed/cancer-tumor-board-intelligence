from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.extraction_audit import NormalizationEvent, make_normalization_event
from services.extraction_normalization import normalize_extraction_output


NORMALIZATION_PIPELINE_VERSION = "1.0.0"


def _diff(before: Any, after: Any, path: str = "") -> list[tuple[str, Any, Any]]:
    if type(before) is not type(after):
        return [(path or "$", before, after)]

    if isinstance(before, dict):
        changes: list[tuple[str, Any, Any]] = []
        keys = sorted(set(before) | set(after))
        for key in keys:
            child_path = f"{path}.{key}" if path else key
            if key not in before:
                changes.append((child_path, None, after[key]))
            elif key not in after:
                changes.append((child_path, before[key], None))
            else:
                changes.extend(_diff(before[key], after[key], child_path))
        return changes

    if isinstance(before, list):
        if before == after:
            return []
        # Lists such as treatment history are semantically ordered collections.
        # Record the collection mutation as one event rather than fabricating an
        # unstable element-level identity for entries without durable IDs.
        return [(path or "$", before, after)]

    if before != after:
        return [(path or "$", before, after)]
    return []


def normalize_primary_extraction(
    raw_model_output: dict[str, Any],
) -> tuple[dict[str, Any], list[NormalizationEvent]]:
    """Normalize a detached copy and emit explicit before/after audit events."""

    immutable_raw = deepcopy(raw_model_output)
    normalized = normalize_extraction_output(immutable_raw)
    warnings = list(normalized.get("extraction_warnings", []) or [])
    reason = (
        "; ".join(warnings)
        if warnings
        else "Deterministic extraction normalization changed representation without adding external clinical facts."
    )

    events = [
        make_normalization_event(
            rule="primary_extraction_normalization",
            field_path=path,
            before=before,
            after=after,
            reason=reason,
        )
        for path, before, after in _diff(raw_model_output, normalized)
        if path != "extraction_warnings"
    ]
    return normalized, events
