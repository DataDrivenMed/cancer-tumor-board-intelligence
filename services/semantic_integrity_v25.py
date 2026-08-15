from __future__ import annotations

import re
from typing import Any

from services.extraction_hardening_v25 import classify_missing_information
from services.semantic_integrity import SemanticIntegrityFinding, inspect_raw_semantic_integrity


SEMANTIC_INTEGRITY_V25_VERSION = "2.5.0"
_PHASE_WORDS = {"induction", "maintenance", "consolidation", "salvage", "adjuvant", "neoadjuvant"}
_STOPWORDS = {"plus", "and", "with", "therapy", "treatment", "regimen", "received", "started", "initiated", "underwent"}


def _norm(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("–", "-").replace("—", "-").split())


def _expand_token(token: str) -> list[str]:
    if token == "rvd":
        return ["lenalidomide", "bortezomib", "dexamethasone"]
    return [token]


def _signature(item: dict[str, Any]) -> tuple[str, ...]:
    text = re.sub(r"[/,+]", " ", _norm(item.get("regimen"))).replace("-", " ")
    expanded: list[str] = []
    for token in re.findall(r"[a-z0-9]+", text):
        if token not in _STOPWORDS:
            expanded.extend(_expand_token(token))
    for agent in item.get("agents", []) or []:
        agent_text = re.sub(r"[/,+]", " ", _norm(agent)).replace("-", " ")
        for token in re.findall(r"[a-z0-9]+", agent_text):
            if token not in _STOPWORDS:
                expanded.extend(_expand_token(token))
    return tuple(sorted(set(expanded)))


def _likely_duplicate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    sig_a, sig_b = _signature(a), _signature(b)
    if not sig_a or sig_a != sig_b:
        return False
    phases_a, phases_b = set(sig_a) & _PHASE_WORDS, set(sig_b) & _PHASE_WORDS
    if phases_a and phases_b and phases_a != phases_b:
        return False
    ids_a = set(a.get("source_segment_ids", []) or [])
    ids_b = set(b.get("source_segment_ids", []) or [])
    if ids_a and ids_b and not (ids_a & ids_b):
        return False
    ex_a, ex_b = _norm(a.get("source_excerpt")), _norm(b.get("source_excerpt"))
    return bool(ex_a and ex_b and (ex_a == ex_b or ex_a in ex_b or ex_b in ex_a))


def inspect_raw_semantic_integrity_v25(raw: dict[str, Any] | None) -> list[SemanticIntegrityFinding]:
    raw = raw or {}
    findings = list(inspect_raw_semantic_integrity(raw))
    treatments = [x for x in raw.get("treatments", []) or [] if isinstance(x, dict)]
    for i, first in enumerate(treatments):
        for second in treatments[i + 1:]:
            if _likely_duplicate(first, second):
                findings.append(SemanticIntegrityFinding(code="DUPLICATE_TREATMENT_EPISODE", severity="error", field="treatments", message=f"Semantically duplicate treatment episodes remain for '{first.get('regimen')}' and '{second.get('regimen')}'."))
    for index, item in enumerate(raw.get("missing_items", []) or []):
        if not isinstance(item, dict):
            continue
        expected = classify_missing_information(item)
        actual = _norm(item.get("category"))
        if actual != expected:
            findings.append(SemanticIntegrityFinding(code="MISSING_INFORMATION_CATEGORY_MISMATCH", severity="error", field=f"missing_items[{index}].category", message=f"Missing-information category '{actual or 'unset'}' does not match deterministic ontology category '{expected}'."))
    return findings


def semantic_integrity_v25_passes(findings: list[SemanticIntegrityFinding]) -> bool:
    return not any(f.severity in {"error", "critical"} for f in findings)
