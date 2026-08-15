from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from services.document_parser import ParsedDocument
from services.extraction_audit import NormalizationEvent, make_normalization_event


DISEASE_STATE_RESOLVER_VERSION = "1.4.0"


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

_GENERIC_NEGATION_MARKERS = (
    "no evidence of",
    "negative for",
)

_STATE_NEGATION_MARKERS: dict[str, tuple[str, ...]] = {
    "newly diagnosed": ("not newly diagnosed",),
    "relapsed": ("no relapse", "without relapse", "not relapsed"),
    "recurrent": ("no recurrence", "without recurrence", "no recurrent", "not recurrent"),
    "refractory": ("not refractory", "non-refractory"),
    "progressive": ("no progression", "without progression", "not progressive"),
    "persistent": ("no persistent disease", "not persistent"),
    "remission": ("not in remission", "no remission"),
    "resected": ("not resected", "unresected"),
    "metastatic": (
        "not metastatic",
        "no metastatic",
        "no metastasis",
        "no metastases",
        "without metastasis",
        "without metastases",
    ),
}

_CURRENT_CONTEXT_MARKERS = (
    "now has",
    "currently has",
    "current disease",
    "currently",
    "now shows",
    "now with",
    "presented with",
    "presents with",
)

_DIAGNOSIS_GENERIC_TOKENS = {
    "cancer",
    "carcinoma",
    "adenocarcinoma",
    "malignancy",
    "metastatic",
    "recurrent",
    "relapsed",
    "progressive",
    "disease",
    "suspected",
    "unknown",
    "primary",
    "site",
    "stage",
}

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
    ("resected", re.compile(r"\bresected\b|\bstatus post resection\b|\bpost-resection\b", re.I), "observed"),
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


def _is_uncertain_or_negated(text: str, start: int, end: int, canonical: str) -> bool:
    context = _window(text, start, end)
    if any(marker in context for marker in _GENERIC_NEGATION_MARKERS):
        return True
    if any(marker in context for marker in _STATE_NEGATION_MARKERS.get(canonical, ())):
        return True

    local_left = text[max(0, start - 35):start].lower()
    local_right = text[end:min(len(text), end + 20)].lower()
    local = local_left + text[start:end].lower() + local_right
    return any(marker in local for marker in _UNCERTAINTY_MARKERS)


def _diagnosis_anchor_tokens(payload: dict[str, Any]) -> set[str]:
    diagnosis = payload.get("diagnosis") or {}
    value = _norm(diagnosis.get("value"))
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value)
        if len(token) >= 4 and token not in _DIAGNOSIS_GENERIC_TOKENS
    }


def _sentence_context(text: str, start: int, end: int) -> str:
    left_candidates = [text.rfind(mark, 0, start) for mark in (".", "?", "!", "\n")]
    left = max(left_candidates) + 1
    right_candidates = [position for mark in (".", "?", "!", "\n") if (position := text.find(mark, end)) >= 0]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left:right].lower()


def _match_is_current_diagnosis_context(
    text: str,
    start: int,
    end: int,
    diagnosis_tokens: set[str],
) -> bool:
    """Require current diagnosis evidence in the same sentence as the state phrase."""

    sentence = _sentence_context(text, start, end)
    if any(marker in sentence for marker in _CURRENT_CONTEXT_MARKERS):
        return True
    return bool(diagnosis_tokens and any(token in sentence for token in diagnosis_tokens))


def _candidate_states(document: ParsedDocument, payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    diagnosis_tokens = _diagnosis_anchor_tokens(payload)
    for segment in document.segments:
        text = segment.text
        for canonical, pattern, information_type in _STATE_PATTERNS:
            for match in pattern.finditer(text):
                if not _match_is_current_diagnosis_context(text, match.start(), match.end(), diagnosis_tokens):
                    continue
                if _is_uncertain_or_negated(text, match.start(), match.end(), canonical):
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
    """Promote only explicit, unambiguous, current source-supported disease state."""

    out = deepcopy(payload)
    events: list[NormalizationEvent] = []
    warnings: list[str] = []

    if not _is_missing_disease_state(out):
        return DiseaseStateResolution(out, events, warnings)
    if _has_disease_state_conflict(out):
        warnings.append("Disease-state resolver abstained because a relevant unresolved conflict is present.")
        return DiseaseStateResolution(out, events, warnings)

    candidates = _candidate_states(document, out)
    canonical_states = sorted({candidate["canonical"] for candidate in candidates})
    if not canonical_states:
        return DiseaseStateResolution(out, events, warnings)
    if len(canonical_states) != 1:
        warnings.append(
            "Disease-state resolver found multiple distinct explicit current-state candidates and abstained: "
            + ", ".join(canonical_states)
        )
        return DiseaseStateResolution(out, events, warnings)

    canonical = canonical_states[0]
    matching = [candidate for candidate in candidates if candidate["canonical"] == canonical]
    selected = next((item for item in matching if item["information_type"] == "observed"), matching[0])

    before = deepcopy(out.get("disease_state"))
    after = {
        "field": "disease_state",
        "value": canonical,
        "status": "confirmed",
        "confidence": 1.0,
        "source_segment_ids": selected["source_segment_ids"],
        "source_excerpt": selected["source_excerpt"],
        "information_type": selected["information_type"],
    }
    out["disease_state"] = after
    warning = (
        f"Disease-state consistency resolver populated '{canonical}' from explicit source-supported current-disease evidence "
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
