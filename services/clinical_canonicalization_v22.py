from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from services.document_parser import ParsedDocument
from services.extraction_audit import NormalizationEvent, make_normalization_event


CANONICALIZATION_V22_VERSION = "2.2.0"

_UNCERTAINTY_RE = re.compile(r"\b(suspected|possible|probable|unconfirmed|working diagnosis|concern for|cannot exclude)\b", re.I)
_METASTATIC_RE = re.compile(r"\bmetastatic\b|\b(?:hepatic|liver|pulmonary|lung|bone|osseous|adrenal|distant)\s+metastas(?:is|es)\b|\bmetastas(?:is|es)\b", re.I)
_PROGRESSIVE_RE = re.compile(r"\bradiographic progression\b|\bdisease progression\b|\bprogressive disease\b|\bprogression\b", re.I)
_STAGE_RE = re.compile(r"\bstage\s+([0-9ivx]+[a-c]?)\b", re.I)


@dataclass(frozen=True)
class CanonicalizationResult:
    payload: dict[str, Any]
    events: list[NormalizationEvent]
    diagnostic_certainty: str
    stage: dict[str, Any] | None
    warnings: list[str]


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _segment_texts(document: ParsedDocument, segment_ids: list[str] | None = None) -> list[tuple[str, str]]:
    wanted = set(segment_ids or [])
    rows: list[tuple[str, str]] = []
    for segment in document.segments:
        if wanted and segment.segment_id not in wanted:
            continue
        rows.append((segment.segment_id, segment.text))
    return rows


def _exact_phrase(document: ParsedDocument, segment_ids: list[str], patterns: tuple[re.Pattern[str], ...]) -> tuple[list[str], str] | None:
    for segment_id, text in _segment_texts(document, segment_ids):
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return [segment_id], match.group(0)
    return None


def _certainty(payload: dict[str, Any]) -> str:
    diagnosis = payload.get("diagnosis") or {}
    combined = " ".join(
        str(value or "")
        for value in (
            diagnosis.get("value"),
            diagnosis.get("source_excerpt"),
            diagnosis.get("status"),
        )
    )
    if _UNCERTAINTY_RE.search(combined):
        return "suspected"
    status = _norm(diagnosis.get("status"))
    if status == "confirmed":
        return "confirmed"
    if status == "pending":
        return "pending_pathology"
    return "unknown"


def _stage_from_conflicts(payload: dict[str, Any]) -> dict[str, Any] | None:
    for conflict in payload.get("conflicts", []) or []:
        if "stage" not in _norm(conflict.get("field")):
            continue
        values = [str(conflict.get("value_a") or ""), str(conflict.get("value_b") or "")]
        return {
            "value": None,
            "status": "conflicting",
            "candidates": values,
            "source_segment_ids": list(conflict.get("source_segment_ids", []) or []),
        }
    return None


def _canonicalize_disease_state(
    document: ParsedDocument,
    payload: dict[str, Any],
    certainty: str,
    events: list[NormalizationEvent],
    warnings: list[str],
) -> None:
    disease = payload.get("disease_state")
    if not isinstance(disease, dict):
        return

    before = deepcopy(disease)
    value = str(disease.get("value") or "")
    status = _norm(disease.get("status"))
    source_ids = list(disease.get("source_segment_ids", []) or [])

    # Suspected malignancy must not be promoted to a confirmed canonical disease state.
    if certainty == "suspected" and value:
        disease["value"] = None
        disease["status"] = "unknown"
        disease["confidence"] = min(float(disease.get("confidence", 1.0)), 0.5)
        warning = "Disease-state value was withheld because the underlying diagnosis is explicitly suspected/unconfirmed."
        warnings.append(warning)
        events.append(
            make_normalization_event(
                rule="uncertain_diagnosis_disease_state_guard",
                field_path="disease_state",
                before=before,
                after=deepcopy(disease),
                reason=warning,
                source_segment_ids=source_ids,
                source_excerpt=disease.get("source_excerpt"),
            )
        )
        return

    # Stage conflicts belong to a stage representation, not disease_state.
    if any("stage" in _norm(item.get("field")) for item in payload.get("conflicts", []) or []):
        if "stage" in _norm(value) or status == "conflicting":
            disease["value"] = None
            disease["status"] = "conflicting"
            warning = "Disease-state value was cleared because unresolved stage information is represented as a separate conflict."
            warnings.append(warning)
            events.append(
                make_normalization_event(
                    rule="stage_conflict_separation",
                    field_path="disease_state",
                    before=before,
                    after=deepcopy(disease),
                    reason=warning,
                    source_segment_ids=source_ids,
                    source_excerpt=disease.get("source_excerpt"),
                )
            )
            return

    # Canonicalize explicit metastatic wording while retaining exact source evidence.
    if _METASTATIC_RE.search(value):
        exact = _exact_phrase(document, source_ids, (_METASTATIC_RE,))
        if exact:
            disease["value"] = "metastatic"
            disease["status"] = "confirmed"
            disease["source_segment_ids"], disease["source_excerpt"] = exact
            if disease != before:
                events.append(
                    make_normalization_event(
                        rule="canonical_metastatic_state",
                        field_path="disease_state",
                        before=before,
                        after=deepcopy(disease),
                        reason="Canonicalized explicit source-supported metastatic wording without adding clinical inference.",
                        source_segment_ids=disease["source_segment_ids"],
                        source_excerpt=disease["source_excerpt"],
                    )
                )
            return

    if _PROGRESSIVE_RE.search(value):
        exact = _exact_phrase(document, source_ids, (_PROGRESSIVE_RE,))
        if exact:
            disease["value"] = "progressive"
            disease["status"] = "confirmed"
            disease["source_segment_ids"], disease["source_excerpt"] = exact
            if disease != before:
                events.append(
                    make_normalization_event(
                        rule="canonical_progressive_state",
                        field_path="disease_state",
                        before=before,
                        after=deepcopy(disease),
                        reason="Canonicalized explicit source-supported progression wording.",
                        source_segment_ids=disease["source_segment_ids"],
                        source_excerpt=disease["source_excerpt"],
                    )
                )


def _repair_disease_state_provenance(document: ParsedDocument, payload: dict[str, Any], events: list[NormalizationEvent]) -> None:
    disease = payload.get("disease_state")
    if not isinstance(disease, dict) or not disease.get("value"):
        return
    source_ids = list(disease.get("source_segment_ids", []) or [])
    excerpt = " ".join(str(disease.get("source_excerpt") or "").split())
    if excerpt and any(excerpt in " ".join(text.split()) for _, text in _segment_texts(document, source_ids)):
        return

    canonical = _norm(disease.get("value"))
    patterns: tuple[re.Pattern[str], ...] = ()
    if canonical == "progressive":
        patterns = (_PROGRESSIVE_RE,)
    elif canonical == "metastatic":
        patterns = (_METASTATIC_RE,)
    elif canonical == "resected":
        patterns = (re.compile(r"\bresected\b|\bstatus post resection\b|\bpost-resection\b", re.I),)
    elif canonical == "newly diagnosed":
        patterns = (re.compile(r"\bnewly[- ]diagnosed\b", re.I),)
    elif canonical == "persistent":
        patterns = (re.compile(r"\bpersistent disease\b|\bpersistent\b", re.I),)
    elif canonical == "relapsed":
        patterns = (re.compile(r"\brelaps(?:e|ed)\b", re.I),)

    if not patterns:
        return
    exact = _exact_phrase(document, source_ids, patterns)
    if not exact:
        return
    before = deepcopy(disease)
    disease["source_segment_ids"], disease["source_excerpt"] = exact
    events.append(
        make_normalization_event(
            rule="exact_disease_state_provenance_repair",
            field_path="disease_state.provenance",
            before=before,
            after=deepcopy(disease),
            reason="Replaced a non-exact model excerpt with an exact source substring supporting the same canonical disease-state assertion.",
            source_segment_ids=disease["source_segment_ids"],
            source_excerpt=disease["source_excerpt"],
        )
    )


def canonicalize_clinical_fields_v22(*, document: ParsedDocument, payload: dict[str, Any]) -> CanonicalizationResult:
    out = deepcopy(payload)
    events: list[NormalizationEvent] = []
    warnings: list[str] = []
    certainty = _certainty(out)
    stage = _stage_from_conflicts(out)

    _canonicalize_disease_state(document, out, certainty, events, warnings)
    _repair_disease_state_provenance(document, out, events)

    # Add deterministic missing-information categories for evaluation and downstream routing.
    for item in out.get("missing_items", []) or []:
        text = _norm(f"{item.get('field', '')} {item.get('reason', '')}")
        if any(term in text for term in ("pathology", "biopsy", "tissue diagnosis", "histology", "marrow")):
            item["category"] = "pathology"
        elif any(term in text for term in ("molecular", "genomic", "sequencing", "cytogenetic", "flt3", "egfr")):
            item["category"] = "molecular"
        elif any(term in text for term in ("ecog", "performance")):
            item["category"] = "performance_status"
        elif any(term in text for term in ("stage", "staging")):
            item["category"] = "stage"
        elif any(term in text for term in ("treatment", "therapy", "regimen")):
            item["category"] = "treatment_history"
        else:
            item.setdefault("category", "other")

    out["diagnostic_certainty"] = certainty
    out["stage"] = stage
    return CanonicalizationResult(out, events, certainty, stage, warnings)
