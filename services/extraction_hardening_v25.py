from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from services.document_parser import ParsedDocument
from services.extraction_audit import NormalizationEvent, make_normalization_event


HARDENING_V25_VERSION = "2.5.0"

_MOLECULAR_TOKENS = (
    "molecular", "genomic", "sequencing", "ngs", "mutation", "variant", "cytogenetic",
    "cytogenetics", "karyotype", "fish", "flt3", "npm1", "idh1", "idh2", "tp53",
    "braf", "egfr", "alk", "ros1", "kras", "nras", "her2", "brca", "pdl1", "pd-l1",
)
_PATHOLOGY_TOKENS = ("pathology", "biopsy", "histology", "tissue diagnosis", "marrow", "cytology")
_PERFORMANCE_TOKENS = ("ecog", "performance status", "karnofsky", "kps")
_STAGE_TOKENS = ("stage", "staging", "ann arbor", "tnm")
_DIAGNOSIS_TOKENS = ("primary site", "site of origin", "diagnosis", "diagnostic", "tumor origin")
_TREATMENT_TOKENS = ("therapy", "treatment", "regimen", "initiation", "start", "transplant", "car-t", "radiation")

_ACTION_WORDS = ("received", "started", "initiated", "underwent", "completed", "treated with", "currently receiving", "now receiving")
_PHASE_WORDS = {"induction", "maintenance", "consolidation", "salvage", "adjuvant", "neoadjuvant"}
_STOPWORDS = {"plus", "and", "with", "therapy", "treatment", "regimen", "received", "started", "initiated", "underwent"}


@dataclass(frozen=True)
class HardeningResultV25:
    payload: dict[str, Any]
    events: list[NormalizationEvent]
    warnings: list[str]
    duplicate_treatments_removed: int
    missing_categories_reclassified: int


def _norm(value: Any) -> str:
    text = str(value or "").lower().replace("–", "-").replace("—", "-")
    return " ".join(text.split())


def classify_missing_information(item: dict[str, Any]) -> str:
    text = _norm(f"{item.get('field', '')} {item.get('reason', '')}")
    if any(token in text for token in _MOLECULAR_TOKENS):
        return "molecular"
    if any(token in text for token in _PATHOLOGY_TOKENS):
        return "pathology"
    if any(token in text for token in _PERFORMANCE_TOKENS):
        return "performance_status"
    if any(token in text for token in _STAGE_TOKENS):
        return "stage"
    if any(token in text for token in _DIAGNOSIS_TOKENS):
        return "diagnostic_clarification"
    if any(token in text for token in _TREATMENT_TOKENS):
        return "treatment_plan"
    return "other"


def _canonical_regimen_tokens(item: dict[str, Any]) -> tuple[str, ...]:
    text = _norm(item.get("regimen"))
    # Normalize common separators while retaining phase words such as maintenance.
    text = re.sub(r"[/,+]", " ", text)
    text = text.replace("-", " ")
    tokens = [t for t in re.findall(r"[a-z0-9]+", text) if t not in _STOPWORDS]
    expanded: list[str] = []
    for token in tokens:
        if token == "rvd":
            expanded.extend(["lenalidomide", "bortezomib", "dexamethasone"])
        else:
            expanded.append(token)
    # Agents help when regimen typography differs, but avoid duplicating phase labels.
    for agent in item.get("agents", []) or []:
        a = _norm(agent)
        if a == "rvd":
            expanded.extend(["lenalidomide", "bortezomib", "dexamethasone"])
        else:
            expanded.extend(t for t in re.findall(r"[a-z0-9]+", a.replace("-", " ")) if t not in _STOPWORDS)
    return tuple(sorted(set(expanded)))


def _source_position(document: ParsedDocument, item: dict[str, Any]) -> tuple[str | None, int]:
    ids = list(item.get("source_segment_ids", []) or [])
    sid = ids[0] if ids else None
    excerpt = str(item.get("source_excerpt") or "")
    segment = next((s for s in document.segments if s.segment_id == sid), None)
    pos = segment.text.lower().find(excerpt.lower()) if segment and excerpt else -1
    return sid, pos


def _same_local_event(document: ParsedDocument, a: dict[str, Any], b: dict[str, Any]) -> bool:
    ex_a, ex_b = _norm(a.get("source_excerpt")), _norm(b.get("source_excerpt"))
    if ex_a and ex_b and (ex_a == ex_b or ex_a in ex_b or ex_b in ex_a):
        return True
    sid_a, pos_a = _source_position(document, a)
    sid_b, pos_b = _source_position(document, b)
    if sid_a and sid_a == sid_b and pos_a >= 0 and pos_b >= 0 and abs(pos_a - pos_b) <= 48:
        return True
    return False


def treatments_are_semantic_duplicates(document: ParsedDocument, a: dict[str, Any], b: dict[str, Any]) -> bool:
    sig_a, sig_b = _canonical_regimen_tokens(a), _canonical_regimen_tokens(b)
    if not sig_a or not sig_b:
        return False
    phases_a = set(sig_a) & _PHASE_WORDS
    phases_b = set(sig_b) & _PHASE_WORDS
    # Different explicit phases are distinct episodes even when the drug backbone is the same.
    if phases_a and phases_b and phases_a != phases_b:
        return False
    core_a = set(sig_a) - _PHASE_WORDS
    core_b = set(sig_b) - _PHASE_WORDS
    if core_a != core_b:
        return False
    return _same_local_event(document, a, b)


def _episode_quality(item: dict[str, Any]) -> tuple[int, int, int, float]:
    status = _norm(item.get("treatment_status"))
    status_score = 3 if status in {"started", "completed", "stopped"} else 1 if status == "unknown" else 0
    excerpt = _norm(item.get("source_excerpt"))
    action_score = 2 if any(word in excerpt for word in _ACTION_WORDS) else 0
    agents_score = len(item.get("agents", []) or [])
    confidence = float(item.get("confidence", 0.0) or 0.0)
    return status_score, action_score, agents_score, confidence


def _merge_episode_fields(preferred: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(preferred)
    for key in ("intent", "line_of_therapy", "start_date", "end_date", "reason_stopped", "best_response"):
        if out.get(key) in (None, "") and other.get(key) not in (None, ""):
            out[key] = deepcopy(other.get(key))
    if not out.get("agents") and other.get("agents"):
        out["agents"] = deepcopy(other.get("agents"))
    if not out.get("toxicities") and other.get("toxicities"):
        out["toxicities"] = deepcopy(other.get("toxicities"))
    return out


def _deduplicate_treatments(document: ParsedDocument, payload: dict[str, Any], events: list[NormalizationEvent], warnings: list[str]) -> int:
    treatments = [deepcopy(x) for x in payload.get("treatments", []) or [] if isinstance(x, dict)]
    if len(treatments) < 2:
        return 0
    before = deepcopy(treatments)
    kept: list[dict[str, Any]] = []
    removed = 0
    for item in treatments:
        duplicate_index = next((i for i, existing in enumerate(kept) if treatments_are_semantic_duplicates(document, existing, item)), None)
        if duplicate_index is None:
            kept.append(item)
            continue
        existing = kept[duplicate_index]
        preferred, other = (item, existing) if _episode_quality(item) > _episode_quality(existing) else (existing, item)
        kept[duplicate_index] = _merge_episode_fields(preferred, other)
        removed += 1
    if removed:
        payload["treatments"] = kept
        reason = f"Removed {removed} semantically duplicate treatment episode(s) representing the same local source event."
        warnings.append(reason)
        events.append(make_normalization_event(
            rule="v25_semantic_treatment_deduplication",
            field_path="treatments",
            before=before,
            after=deepcopy(kept),
            reason=reason,
        ))
    return removed


def _reclassify_missing(payload: dict[str, Any], events: list[NormalizationEvent]) -> int:
    items = payload.get("missing_items", []) or []
    changed = 0
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        canonical = classify_missing_information(item)
        if _norm(item.get("category")) == canonical:
            continue
        before = deepcopy(item)
        item["category"] = canonical
        changed += 1
        events.append(make_normalization_event(
            rule="v25_missing_information_ontology",
            field_path=f"missing_items[{idx}].category",
            before=before,
            after=deepcopy(item),
            reason="Assigned missing-information category deterministically from the unresolved field/reason text.",
        ))
    return changed


def harden_extraction_v25(*, document: ParsedDocument, payload: dict[str, Any]) -> HardeningResultV25:
    out = deepcopy(payload)
    events: list[NormalizationEvent] = []
    warnings: list[str] = []
    removed = _deduplicate_treatments(document, out, events, warnings)
    reclassified = _reclassify_missing(out, events)
    if warnings:
        out.setdefault("extraction_warnings", [])
        for warning in warnings:
            if warning not in out["extraction_warnings"]:
                out["extraction_warnings"].append(warning)
    return HardeningResultV25(
        payload=out,
        events=events,
        warnings=warnings,
        duplicate_treatments_removed=removed,
        missing_categories_reclassified=reclassified,
    )
