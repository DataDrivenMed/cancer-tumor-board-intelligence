from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from services.clinical_canonicalization_v22 import canonicalize_clinical_fields_v22
from services.document_parser import ParsedDocument
from services.extraction_audit import NormalizationEvent, make_normalization_event


CANONICALIZATION_V23_VERSION = "2.3.0"

_UNCERTAIN_STATUS = {"pending", "unknown", "not_documented", "unavailable"}
_UNCERTAINTY_RE = re.compile(r"\b(suspected|possible|probable|unconfirmed|working diagnosis|concern for|cannot exclude)\b", re.I)
_DIAGNOSIS_ENTITY_PATTERNS = (
    re.compile(r"\bmetastatic carcinoma\b", re.I),
    re.compile(r"\bcarcinoma\b", re.I),
    re.compile(r"\b(?:acute myeloid leukemia|acute lymphoblastic leukemia|multiple myeloma|diffuse large b-cell lymphoma|follicular lymphoma|mantle cell lymphoma|myelodysplastic syndrome)\b", re.I),
)


@dataclass(frozen=True)
class CanonicalizationResultV23:
    payload: dict[str, Any]
    events: list[NormalizationEvent]
    diagnostic_certainty: str
    stage: dict[str, Any] | None
    warnings: list[str]


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _segment_rows(document: ParsedDocument, segment_ids: list[str] | None = None) -> list[tuple[str, str]]:
    wanted = set(segment_ids or [])
    rows: list[tuple[str, str]] = []
    for segment in document.segments:
        if wanted and segment.segment_id not in wanted:
            continue
        rows.append((segment.segment_id, segment.text))
    return rows


def _exact_match(document: ParsedDocument, segment_ids: list[str], patterns: tuple[re.Pattern[str], ...]) -> tuple[list[str], str] | None:
    for segment_id, text in _segment_rows(document, segment_ids):
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return [segment_id], match.group(0)
    return None


def _excerpt_is_exact(document: ParsedDocument, segment_ids: list[str], excerpt: str | None) -> bool:
    compact = " ".join(str(excerpt or "").split())
    if not compact:
        return False
    return any(compact in " ".join(text.split()) for _, text in _segment_rows(document, segment_ids))


def _repair_uncertain_diagnosis(document: ParsedDocument, payload: dict[str, Any], events: list[NormalizationEvent], warnings: list[str]) -> None:
    diagnosis = payload.get("diagnosis")
    if not isinstance(diagnosis, dict):
        return
    certainty = _norm(payload.get("diagnostic_certainty"))
    combined = f"{diagnosis.get('value', '')} {diagnosis.get('source_excerpt', '')}"
    if certainty not in {"suspected", "pending_pathology"} and not _UNCERTAINTY_RE.search(combined):
        return

    source_ids = list(diagnosis.get("source_segment_ids", []) or [])
    exact = _exact_match(document, source_ids, _DIAGNOSIS_ENTITY_PATTERNS)
    if not exact:
        return

    before = deepcopy(diagnosis)
    exact_ids, exact_entity = exact
    diagnosis["value"] = exact_entity.lower()
    diagnosis["source_segment_ids"] = exact_ids

    # Prefer an exact uncertainty-bearing phrase if present, otherwise use the exact entity.
    uncertainty_phrase = None
    for segment_id, text in _segment_rows(document, source_ids):
        escaped = re.escape(exact_entity)
        pattern = re.compile(rf"\b{escaped}\b(?:\s+is)?\s+(?:suspected|possible|probable|unconfirmed)", re.I)
        match = pattern.search(text)
        if match:
            uncertainty_phrase = ([segment_id], match.group(0))
            break
    if uncertainty_phrase:
        diagnosis["source_segment_ids"], diagnosis["source_excerpt"] = uncertainty_phrase
    else:
        diagnosis["source_excerpt"] = exact_entity

    if diagnosis != before:
        events.append(
            make_normalization_event(
                rule="uncertain_diagnosis_entity_provenance_repair",
                field_path="diagnosis",
                before=before,
                after=deepcopy(diagnosis),
                reason="Separated the uncertain diagnosis entity from unresolved primary-site detail and retained an exact source substring.",
                source_segment_ids=list(diagnosis.get("source_segment_ids", []) or []),
                source_excerpt=diagnosis.get("source_excerpt"),
            )
        )
        warnings.append("Uncertain diagnosis was normalized to an exact source-supported entity; unresolved primary-site detail remains separate missing information.")


def _repair_diagnosis_excerpt(document: ParsedDocument, payload: dict[str, Any], events: list[NormalizationEvent]) -> None:
    diagnosis = payload.get("diagnosis")
    if not isinstance(diagnosis, dict) or not diagnosis.get("value"):
        return
    source_ids = list(diagnosis.get("source_segment_ids", []) or [])
    if _excerpt_is_exact(document, source_ids, diagnosis.get("source_excerpt")):
        return

    value = str(diagnosis.get("value") or "").strip()
    if not value:
        return
    pattern = re.compile(re.escape(value), re.I)
    exact = _exact_match(document, source_ids, (pattern,))
    if not exact:
        return
    before = deepcopy(diagnosis)
    diagnosis["source_segment_ids"], diagnosis["source_excerpt"] = exact
    events.append(
        make_normalization_event(
            rule="exact_diagnosis_provenance_repair",
            field_path="diagnosis.provenance",
            before=before,
            after=deepcopy(diagnosis),
            reason="Replaced a non-exact diagnosis excerpt with an exact source substring supporting the same diagnosis entity.",
            source_segment_ids=diagnosis["source_segment_ids"],
            source_excerpt=diagnosis["source_excerpt"],
        )
    )


def _missing_key(item: dict[str, Any]) -> tuple[str, str]:
    return (_norm(item.get("category")), _norm(item.get("field")))


def _has_missing_category(payload: dict[str, Any], category: str) -> bool:
    target = _norm(category)
    for item in payload.get("missing_items", []) or []:
        if _norm(item.get("category")) == target:
            return True
        text = _norm(f"{item.get('field', '')} {item.get('reason', '')}")
        if target == "pathology" and any(token in text for token in ("pathology", "biopsy", "tissue diagnosis", "histology", "marrow")):
            return True
        if target == "performance_status" and any(token in text for token in ("ecog", "performance")):
            return True
        if target == "molecular" and any(token in text for token in ("molecular", "genomic", "sequencing", "cytogenetic")):
            return True
    return False


def _append_missing(payload: dict[str, Any], item: dict[str, Any], events: list[NormalizationEvent], reason: str) -> None:
    missing_items = payload.setdefault("missing_items", [])
    before = deepcopy(missing_items)
    key = _missing_key(item)
    if any(_missing_key(existing) == key for existing in missing_items if isinstance(existing, dict)):
        return
    missing_items.append(item)
    events.append(
        make_normalization_event(
            rule="cross_field_missingness_reconciliation",
            field_path="missing_items",
            before=before,
            after=deepcopy(missing_items),
            reason=reason,
            source_segment_ids=[],
            source_excerpt=None,
        )
    )


def _reconcile_missingness(payload: dict[str, Any], events: list[NormalizationEvent]) -> None:
    # Pending or unavailable pathology represented structurally must also appear in the
    # decision-critical missing-information list. This is deterministic duplication,
    # not a new clinical inference.
    pathology_unresolved = False
    pathology_availability = "pending"
    for fact in payload.get("pathology", []) or []:
        if not isinstance(fact, dict):
            continue
        status = _norm(fact.get("status"))
        value = fact.get("value")
        if value in (None, "") and status in _UNCERTAIN_STATUS:
            pathology_unresolved = True
            pathology_availability = status if status else "pending"
            break
    if pathology_unresolved and not _has_missing_category(payload, "pathology"):
        _append_missing(
            payload,
            {
                "field": "tissue diagnosis",
                "importance": "high",
                "reason": "Pathology/tissue diagnosis is unresolved in the structured pathology field.",
                "availability": pathology_availability,
                "recommendation_blocking": True,
                "category": "pathology",
            },
            events,
            "Promoted an unresolved structured pathology fact into canonical missing information.",
        )

    performance = payload.get("performance_status")
    if isinstance(performance, dict) and performance.get("value") in (None, "") and _norm(performance.get("status")) in _UNCERTAIN_STATUS:
        if not _has_missing_category(payload, "performance_status"):
            _append_missing(
                payload,
                {
                    "field": "ECOG",
                    "importance": "moderate",
                    "reason": "Performance status is unresolved in the structured performance-status field.",
                    "availability": _norm(performance.get("status")) or "not_documented",
                    "recommendation_blocking": False,
                    "category": "performance_status",
                },
                events,
                "Promoted unresolved structured performance status into canonical missing information.",
            )

    # A pending diagnosis plus no resolved pathology is always represented as a pathology gap.
    certainty = _norm(payload.get("diagnostic_certainty"))
    if certainty in {"suspected", "pending_pathology"} and not _has_missing_category(payload, "pathology"):
        _append_missing(
            payload,
            {
                "field": "tissue diagnosis",
                "importance": "high",
                "reason": "Diagnostic confirmation is pending.",
                "availability": "pending",
                "recommendation_blocking": True,
                "category": "pathology",
            },
            events,
            "Added the pathology gap required by a non-confirmed diagnosis.",
        )


def canonicalize_clinical_fields_v23(*, document: ParsedDocument, payload: dict[str, Any]) -> CanonicalizationResultV23:
    base = canonicalize_clinical_fields_v22(document=document, payload=payload)
    out = deepcopy(base.payload)
    events = list(base.events)
    warnings = list(base.warnings)

    _repair_uncertain_diagnosis(document, out, events, warnings)
    _repair_diagnosis_excerpt(document, out, events)
    _reconcile_missingness(out, events)

    return CanonicalizationResultV23(
        payload=out,
        events=events,
        diagnostic_certainty=str(out.get("diagnostic_certainty") or base.diagnostic_certainty),
        stage=deepcopy(out.get("stage")),
        warnings=warnings,
    )
