from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from services.document_parser import ParsedDocument
from services.extraction_audit import NormalizationEvent, make_normalization_event


RECONCILIATION_V24_VERSION = "2.4.0"
_UNCERTAIN = {"suspected", "pending_pathology", "possible", "probable", "unknown"}
_UNRESOLVED_STATUS = {"pending", "unknown", "not_documented", "unavailable"}
_DIAGNOSIS_ENTITY_PATTERNS = (
    re.compile(r"\bmetastatic carcinoma\b", re.I),
    re.compile(r"\bcarcinoma\b", re.I),
    re.compile(r"\b(?:lymphoma|acute myeloid leukemia|acute lymphoblastic leukemia|multiple myeloma|diffuse large b-cell lymphoma|follicular lymphoma|mantle cell lymphoma|myelodysplastic syndrome)\b", re.I),
)


@dataclass(frozen=True)
class ReconciliationResultV24:
    payload: dict[str, Any]
    events: list[NormalizationEvent]
    warnings: list[str]


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _segments(document: ParsedDocument, segment_ids: list[str] | None = None) -> list[tuple[str, str]]:
    wanted = set(segment_ids or [])
    return [
        (segment.segment_id, segment.text)
        for segment in document.segments
        if not wanted or segment.segment_id in wanted
    ]


def _exact_match(document: ParsedDocument, segment_ids: list[str], patterns: tuple[re.Pattern[str], ...]) -> tuple[list[str], str] | None:
    for segment_id, text in _segments(document, segment_ids):
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return [segment_id], match.group(0)
    return None


def _excerpt_is_exact(document: ParsedDocument, segment_ids: list[str], excerpt: str | None) -> bool:
    compact = " ".join(str(excerpt or "").split())
    if not compact:
        return False
    return any(compact in " ".join(text.split()) for _, text in _segments(document, segment_ids))


def _repair_diagnosis_provenance(document: ParsedDocument, payload: dict[str, Any], events: list[NormalizationEvent]) -> None:
    diagnosis = payload.get("diagnosis")
    if not isinstance(diagnosis, dict) or not diagnosis.get("value"):
        return
    source_ids = list(diagnosis.get("source_segment_ids", []) or [])
    if _excerpt_is_exact(document, source_ids, diagnosis.get("source_excerpt")):
        return

    value = str(diagnosis.get("value") or "").strip()
    exact = _exact_match(document, source_ids, (re.compile(re.escape(value), re.I),)) if value else None
    if not exact:
        exact = _exact_match(document, source_ids, _DIAGNOSIS_ENTITY_PATTERNS)
    if not exact:
        return

    before = deepcopy(diagnosis)
    diagnosis["source_segment_ids"], diagnosis["source_excerpt"] = exact
    events.append(
        make_normalization_event(
            rule="v24_exact_diagnosis_provenance_repair",
            field_path="diagnosis.provenance",
            before=before,
            after=deepcopy(diagnosis),
            reason="Replaced a non-exact diagnosis excerpt with an exact source substring supporting the same diagnosis entity.",
            source_segment_ids=diagnosis["source_segment_ids"],
            source_excerpt=diagnosis["source_excerpt"],
        )
    )


def _has_missing_category(payload: dict[str, Any], category: str) -> bool:
    target = _norm(category)
    for item in payload.get("missing_items", []) or []:
        if not isinstance(item, dict):
            continue
        if _norm(item.get("category")) == target:
            return True
        text = _norm(f"{item.get('field', '')} {item.get('reason', '')}")
        if target == "pathology" and any(token in text for token in ("pathology", "biopsy", "tissue diagnosis", "histology", "marrow")):
            return True
        if target == "performance_status" and any(token in text for token in ("ecog", "performance")):
            return True
    return False


def _append_missing(payload: dict[str, Any], item: dict[str, Any], events: list[NormalizationEvent], reason: str) -> None:
    missing_items = payload.setdefault("missing_items", [])
    before = deepcopy(missing_items)
    missing_items.append(item)
    events.append(
        make_normalization_event(
            rule="v24_cross_field_missingness_reconciliation",
            field_path="missing_items",
            before=before,
            after=deepcopy(missing_items),
            reason=reason,
            source_segment_ids=[],
            source_excerpt=None,
        )
    )


def _reconcile_missingness(payload: dict[str, Any], events: list[NormalizationEvent]) -> None:
    pathology_unresolved = False
    pathology_status = "pending"
    for fact in payload.get("pathology", []) or []:
        if not isinstance(fact, dict):
            continue
        status = _norm(fact.get("status"))
        if fact.get("value") in (None, "") and status in _UNRESOLVED_STATUS:
            pathology_unresolved = True
            pathology_status = status or "pending"
            break

    certainty = _norm(payload.get("diagnostic_certainty"))
    if (pathology_unresolved or certainty in _UNCERTAIN) and not _has_missing_category(payload, "pathology"):
        _append_missing(
            payload,
            {
                "field": "tissue diagnosis",
                "importance": "high",
                "reason": "Diagnostic pathology remains unresolved.",
                "availability": pathology_status,
                "recommendation_blocking": True,
                "category": "pathology",
            },
            events,
            "Promoted unresolved diagnostic pathology into canonical missing information.",
        )

    performance = payload.get("performance_status")
    if isinstance(performance, dict):
        status = _norm(performance.get("status"))
        if performance.get("value") in (None, "") and status in _UNRESOLVED_STATUS and not _has_missing_category(payload, "performance_status"):
            _append_missing(
                payload,
                {
                    "field": "ECOG",
                    "importance": "moderate",
                    "reason": "Performance status is unresolved.",
                    "availability": status or "not_documented",
                    "recommendation_blocking": False,
                    "category": "performance_status",
                },
                events,
                "Promoted unresolved performance status into canonical missing information.",
            )


def _enforce_final_uncertainty_invariant(payload: dict[str, Any], events: list[NormalizationEvent], warnings: list[str]) -> None:
    certainty = _norm(payload.get("diagnostic_certainty"))
    disease = payload.get("disease_state")
    if not isinstance(disease, dict):
        return
    if certainty in _UNCERTAIN and disease.get("value") not in (None, ""):
        before = deepcopy(disease)
        disease["value"] = None
        disease["status"] = "unknown"
        disease["confidence"] = min(float(disease.get("confidence", 1.0)), 0.5)
        events.append(
            make_normalization_event(
                rule="v24_final_uncertain_diagnosis_invariant",
                field_path="disease_state",
                before=before,
                after=deepcopy(disease),
                reason="Final safety invariant: a non-confirmed diagnosis cannot yield a confirmed disease-state assertion.",
                source_segment_ids=list(disease.get("source_segment_ids", []) or []),
                source_excerpt=disease.get("source_excerpt"),
            )
        )
        warnings.append("Final uncertainty invariant withheld disease state because the diagnosis is not confirmed.")


def reconcile_clinical_fields_v24(*, document: ParsedDocument, payload: dict[str, Any]) -> ReconciliationResultV24:
    """Apply bounded post-v2.2 reconciliation only.

    This function intentionally does not invoke any prior canonicalizer. It is designed
    to be idempotent and cannot re-run metastatic/progression canonicalization.
    """
    out = deepcopy(payload)
    events: list[NormalizationEvent] = []
    warnings: list[str] = []
    _repair_diagnosis_provenance(document, out, events)
    _reconcile_missingness(out, events)
    _enforce_final_uncertainty_invariant(out, events, warnings)
    return ReconciliationResultV24(payload=out, events=events, warnings=warnings)
