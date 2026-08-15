from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from services.document_parser import ParsedDocument
from services.extraction_audit import NormalizationEvent, make_normalization_event
from services.model_gateway import structured_json_response_raw


TREATMENT_COMPLETENESS_VERSION = "1.1.0"

_ADMINISTERED_STATUSES = {"started", "completed", "stopped"}
_NONADMINISTERED_STATUSES = {"planned", "ordered", "cancelled", "unknown"}

_TIMELINE_CUES = (
    "received",
    "treated with",
    "started",
    "initiated",
    "underwent",
    "maintenance",
    "induction",
    "consolidation",
    "salvage",
    "followed by",
    "then received",
    "later received",
    "now receiving",
    "currently receiving",
)

_TREATMENT_STATUS_VALUES = [
    "planned",
    "ordered",
    "started",
    "completed",
    "stopped",
    "cancelled",
    "unknown",
]


def _nullable_string() -> dict[str, Any]:
    return {"type": ["string", "null"]}


TREATMENT_COMPLETENESS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["treatments"],
    "properties": {
        "treatments": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "regimen",
                    "treatment_status",
                    "intent",
                    "line_of_therapy",
                    "start_date",
                    "end_date",
                    "agents",
                    "reason_stopped",
                    "best_response",
                    "toxicities",
                    "confidence",
                    "source_segment_ids",
                    "source_excerpt",
                ],
                "properties": {
                    "regimen": {"type": "string"},
                    "treatment_status": {"type": "string", "enum": _TREATMENT_STATUS_VALUES},
                    "intent": _nullable_string(),
                    "line_of_therapy": {"type": ["integer", "null"]},
                    "start_date": _nullable_string(),
                    "end_date": _nullable_string(),
                    "agents": {"type": "array", "items": {"type": "string"}},
                    "reason_stopped": _nullable_string(),
                    "best_response": _nullable_string(),
                    "toxicities": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "source_segment_ids": {"type": "array", "items": {"type": "string"}},
                    "source_excerpt": {"type": "string"},
                },
            },
        }
    },
}


TREATMENT_COMPLETENESS_SYSTEM = """You are a bounded treatment-history completeness extraction service.

Your only task is to enumerate every explicit cancer-directed treatment episode that the patient actually started, received, underwent, completed, or stopped in the supplied source segments.

Rules:
1. Use only the supplied source text. Do not infer therapy from diagnosis or standard of care.
2. Extract one chronological episode for every explicit treatment event, including induction, consolidation, maintenance, salvage, systemic therapy, radiation, transplant, and cellular therapy when documented.
3. Do not compress distinct chronological episodes into one summary episode.
4. Do not omit an intermediate maintenance or consolidation episode merely because later therapy is more recent.
5. Planned, recommended, ordered, scheduled, or not-yet-started therapy must not be treated as administered. It may be returned only with the corresponding nonadministered treatment_status.
6. For every returned episode, source_segment_ids must contain only exact supplied segment IDs and source_excerpt must be an exact substring of the cited segment.
7. Preserve chronology from the source. Do not invent dates, line of therapy, response, reason stopped, or agents.
8. treatment_status describes documented administration state only: planned, ordered, started, completed, stopped, cancelled, or unknown. Use unknown only when the source truly does not establish administration status.
9. If the source does not explicitly contain cancer treatment history, return an empty treatments array.
"""


@dataclass(frozen=True)
class TreatmentCompletenessResult:
    payload: dict[str, Any]
    events: list[NormalizationEvent]
    warnings: list[str]
    second_pass_performed: bool
    candidate_count: int
    added_count: int


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("–", "-").replace("—", "-").split())


def needs_treatment_completeness_pass(document: ParsedDocument) -> bool:
    text = " ".join(segment.text.lower() for segment in document.segments)
    return any(cue in text for cue in _TIMELINE_CUES)


def extract_treatment_candidates(
    *,
    document: ParsedDocument,
    api_key: str,
    model: str,
) -> list[dict[str, Any]]:
    user_input = (
        "Perform an independent treatment-history completeness pass over the source below. "
        "Read the source sequentially and return every explicit treatment episode as a separate record. "
        "Do not omit intermediate treatment phases.\n\n"
        + document.numbered_text()
    )
    response = structured_json_response_raw(
        api_key=api_key,
        model=model,
        system_instructions=TREATMENT_COMPLETENESS_SYSTEM,
        user_input=user_input,
        schema_name="treatment_history_completeness",
        json_schema=TREATMENT_COMPLETENESS_SCHEMA,
    )
    return list(response.get("treatments", []) or [])


def _candidate_is_exactly_provenanced(document: ParsedDocument, candidate: dict[str, Any]) -> bool:
    segment_map = {segment.segment_id: segment for segment in document.segments}
    ids = list(candidate.get("source_segment_ids", []) or [])
    excerpt = str(candidate.get("source_excerpt") or "")
    if not ids or not excerpt:
        return False
    if any(segment_id not in segment_map for segment_id in ids):
        return False
    normalized_excerpt = " ".join(excerpt.split())
    return any(
        normalized_excerpt in " ".join(segment_map[segment_id].text.split())
        for segment_id in ids
    )


def _episode_text(item: dict[str, Any]) -> str:
    return _norm(" ".join([str(item.get("regimen") or ""), *[str(agent) for agent in item.get("agents", []) or []]]))


def _is_duplicate(candidate: dict[str, Any], existing: list[dict[str, Any]]) -> bool:
    candidate_text = _episode_text(candidate)
    candidate_excerpt = _norm(candidate.get("source_excerpt"))
    for item in existing:
        existing_text = _episode_text(item)
        existing_excerpt = _norm(item.get("source_excerpt"))
        if candidate_excerpt and existing_excerpt and candidate_excerpt == existing_excerpt:
            return True
        if candidate_text and existing_text:
            if candidate_text == existing_text:
                return True
            if candidate_text in existing_text or existing_text in candidate_text:
                return True
    return False


def _source_position(document: ParsedDocument, item: dict[str, Any]) -> tuple[int, int]:
    segment_rank = {segment.segment_id: idx for idx, segment in enumerate(document.segments)}
    ids = list(item.get("source_segment_ids", []) or [])
    first_id = ids[0] if ids else None
    rank = segment_rank.get(first_id, 10**9)
    excerpt = str(item.get("source_excerpt") or "")
    segment = next((segment for segment in document.segments if segment.segment_id == first_id), None)
    excerpt_rank = segment.text.find(excerpt) if segment and excerpt else -1
    if excerpt_rank < 0:
        excerpt_rank = 10**9
    return rank, excerpt_rank


def _infer_status_from_excerpt(item: dict[str, Any]) -> str:
    status = _norm(item.get("treatment_status"))
    if status in set(_TREATMENT_STATUS_VALUES):
        return status
    excerpt = _norm(item.get("source_excerpt"))
    if any(term in excerpt for term in ("not yet started", "not started", "recommended", "planned")):
        return "planned"
    if "ordered" in excerpt:
        return "ordered"
    if any(term in excerpt for term in ("stopped", "discontinued")):
        return "stopped"
    if any(term in excerpt for term in ("completed", "finished")):
        return "completed"
    if any(term in excerpt for term in ("received", "started", "initiated", "underwent", "now receiving", "currently receiving")):
        return "started"
    return "unknown"


def merge_treatment_candidates(
    *,
    document: ParsedDocument,
    payload: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> TreatmentCompletenessResult:
    out = deepcopy(payload)
    existing = list(out.get("treatments", []) or [])
    events: list[NormalizationEvent] = []
    warnings: list[str] = []
    added = 0

    for item in existing:
        item.setdefault("treatment_status", _infer_status_from_excerpt(item))

    for candidate in candidates:
        candidate = deepcopy(candidate)
        candidate["treatment_status"] = _infer_status_from_excerpt(candidate)
        if candidate["treatment_status"] not in _ADMINISTERED_STATUSES:
            # Repair is intentionally conservative. Unknown administration status
            # is not enough to add a new canonical administered episode.
            continue
        if not _candidate_is_exactly_provenanced(document, candidate):
            warnings.append(
                f"Treatment completeness candidate '{candidate.get('regimen', 'unknown')}' was not merged because exact provenance verification failed."
            )
            continue
        if _is_duplicate(candidate, existing):
            continue

        existing.append(candidate)
        added += 1
        reason = (
            f"Treatment completeness pass added source-supported administered episode '{candidate.get('regimen', 'unknown')}' "
            "that was absent from the primary extraction."
        )
        warnings.append(reason)
        events.append(
            make_normalization_event(
                rule="treatment_episode_completeness",
                field_path="treatments",
                before=None,
                after=candidate,
                reason=reason,
                source_segment_ids=candidate.get("source_segment_ids", []),
                source_excerpt=candidate.get("source_excerpt"),
            )
        )

    existing.sort(key=lambda item: _source_position(document, item))
    out["treatments"] = existing
    if warnings:
        out.setdefault("extraction_warnings", [])
        for warning in warnings:
            if warning not in out["extraction_warnings"]:
                out["extraction_warnings"].append(warning)

    return TreatmentCompletenessResult(
        payload=out,
        events=events,
        warnings=warnings,
        second_pass_performed=True,
        candidate_count=len(candidates),
        added_count=added,
    )
