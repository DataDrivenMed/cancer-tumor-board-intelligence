from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any
import uuid


AUDIT_EVENT_VERSION = "1.0.0"


@dataclass(frozen=True)
class NormalizationEvent:
    """One explicit, reviewable mutation between model output and canonical extraction."""

    event_id: str
    rule: str
    field_path: str
    before: Any
    after: Any
    reason: str
    source_segment_ids: tuple[str, ...] = ()
    source_excerpt: str | None = None
    version: str = AUDIT_EVENT_VERSION

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["source_segment_ids"] = list(self.source_segment_ids)
        return payload


def make_normalization_event(
    *,
    rule: str,
    field_path: str,
    before: Any,
    after: Any,
    reason: str,
    source_segment_ids: list[str] | tuple[str, ...] | None = None,
    source_excerpt: str | None = None,
) -> NormalizationEvent:
    """Create a detached audit event so later object mutation cannot rewrite history."""

    return NormalizationEvent(
        event_id=f"NORM-{uuid.uuid4().hex[:12]}",
        rule=rule,
        field_path=field_path,
        before=deepcopy(before),
        after=deepcopy(after),
        reason=reason,
        source_segment_ids=tuple(source_segment_ids or ()),
        source_excerpt=source_excerpt,
    )


def serialize_events(events: list[NormalizationEvent]) -> list[dict[str, Any]]:
    return [event.as_dict() for event in events]
