from __future__ import annotations

from copy import deepcopy
import json
from typing import Any


_NOT_STARTED_PATTERNS = (
    "has not yet started",
    "has not started",
    "not yet started",
    "not started",
    "planned but not started",
    "scheduled but not started",
)

_CURRENT_MEDICATION_MARKERS = (
    "currently taking",
    "currently on",
    "continues",
    "continue",
    "remains on",
    "taking ",
    "active medication",
    "current medication",
    "medication list",
)


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().split())


def _serialized_object(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return False
    try:
        return isinstance(json.loads(text), dict)
    except Exception:
        return False


def _append_warning(raw: dict[str, Any], warning: str) -> None:
    warnings = raw.setdefault("extraction_warnings", [])
    if warning not in warnings:
        warnings.append(warning)


def _missing_mentions_regimen(missing_items: list[dict[str, Any]], regimen: str) -> bool:
    target = _norm(regimen)
    for item in missing_items:
        text = _norm(f"{item.get('field', '')} {item.get('reason', '')}")
        if target and target in text:
            return True
    return False


def normalize_extraction_output(raw: dict[str, Any]) -> dict[str, Any]:
    """Repair narrow representation errors without adding clinical facts.

    This function is intentionally deterministic and conservative. It operates
    only on explicit model output and source excerpts already returned by the
    extraction model. It does not infer diagnosis, stage, response, actionability,
    or treatment eligibility.
    """
    out = deepcopy(raw)

    # Scalar fields must remain scalar. A JSON object encoded inside a string is
    # treated as malformed representation, not as a care-site value.
    for field in ("care_site", "sex"):
        if _serialized_object(out.get(field)):
            out[field] = None
            _append_warning(
                out,
                f"Semantic normalization cleared malformed serialized JSON from scalar field '{field}'.",
            )

    # Treatment history represents therapy that actually started. Explicitly
    # planned/not-started therapy is removed from administered history and kept
    # as unresolved/planned information instead.
    kept_treatments: list[dict[str, Any]] = []
    missing_items = list(out.get("missing_items", []) or [])
    for treatment in out.get("treatments", []) or []:
        excerpt = _norm(treatment.get("source_excerpt"))
        if any(pattern in excerpt for pattern in _NOT_STARTED_PATTERNS):
            regimen = str(treatment.get("regimen") or "planned treatment")
            if not _missing_mentions_regimen(missing_items, regimen):
                missing_items.append(
                    {
                        "field": f"{regimen} initiation",
                        "importance": "moderate",
                        "reason": "Treatment is explicitly documented as not yet started.",
                        "availability": "pending",
                        "recommendation_blocking": False,
                    }
                )
            _append_warning(
                out,
                f"Semantic normalization removed not-started therapy '{regimen}' from administered treatment history.",
            )
            continue
        kept_treatments.append(treatment)
    out["treatments"] = kept_treatments
    out["missing_items"] = missing_items

    # current_medications requires explicit current-tense support. Historical or
    # temporally ambiguous medication mentions remain outside this field.
    current_medications: list[dict[str, Any]] = []
    for fact in out.get("current_medications", []) or []:
        excerpt = _norm(fact.get("source_excerpt"))
        has_current_support = any(marker in excerpt for marker in _CURRENT_MEDICATION_MARKERS)
        if excerpt and not has_current_support:
            _append_warning(
                out,
                f"Semantic normalization removed '{fact.get('field', 'medication')}' from current_medications because current use was not explicit.",
            )
            continue
        if fact.get("status") == "confirmed" and fact.get("value") is None:
            if has_current_support and fact.get("field"):
                fact["value"] = fact["field"]
                _append_warning(
                    out,
                    f"Semantic normalization populated confirmed current-medication value from its source-supported field label '{fact['field']}'.",
                )
            else:
                # Without an explicit current assertion, a confirmed-null current
                # medication is not safe to retain.
                _append_warning(
                    out,
                    f"Semantic normalization removed incomplete confirmed current-medication entry '{fact.get('field', 'medication')}'.",
                )
                continue
        current_medications.append(fact)
    out["current_medications"] = current_medications

    # A confirmed transplant/cellular-therapy assertion must carry a substantive
    # value. When the exact source excerpt explicitly supports the field label,
    # use that same label as the value. Otherwise remove the incomplete record.
    transplant_items: list[dict[str, Any]] = []
    for fact in out.get("transplant_cellular_therapy", []) or []:
        if fact.get("status") == "confirmed" and fact.get("value") is None:
            field = str(fact.get("field") or "").strip()
            excerpt = _norm(fact.get("source_excerpt"))
            if field and _norm(field) in excerpt:
                fact["value"] = field
                _append_warning(
                    out,
                    f"Semantic normalization populated confirmed transplant/cellular-therapy value from its exact source-supported field label '{field}'.",
                )
            else:
                _append_warning(
                    out,
                    f"Semantic normalization removed incomplete confirmed transplant/cellular-therapy entry '{field or 'unknown'}'.",
                )
                continue
        transplant_items.append(fact)
    out["transplant_cellular_therapy"] = transplant_items

    return out


def normalize_structured_output(schema_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Schema-aware normalization hook for provider-neutral structured output."""
    if schema_name == "tumor_board_case_extraction":
        return normalize_extraction_output(payload)
    return payload
