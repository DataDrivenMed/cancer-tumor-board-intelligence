from __future__ import annotations

from qualification.cases import GoldCase
from qualification.scoring import QualificationScore, _norm, summarize
from qualification.scoring_v21 import score_case_v21
from services.repeatability import CORE_METRICS


SCORING_V22_VERSION = "2.2.0"

_MISSING_CATEGORY_ALIASES = {
    "pathology": {"pathology", "biopsy", "tissue", "tissue diagnosis", "histology", "marrow"},
    "molecular": {"molecular", "genomic", "sequencing", "cytogenetic", "cytogenetics", "flt3", "egfr"},
    "performance": {"performance", "performance status", "ecog"},
    "ecog": {"performance", "performance status", "ecog"},
    "stage": {"stage", "staging"},
    "treatment": {"treatment", "therapy", "regimen", "treatment history"},
    "laboratory": {"laboratory", "labs", "lab"},
    "renal": {"renal", "creatinine", "kidney", "egfr"},
}


def _missing_semantic_texts(package) -> list[str]:
    rows: list[str] = []
    for item in package.normalized_extraction.get("missing_items", []) or []:
        rows.append(
            _norm(
                " ".join(
                    str(item.get(key) or "")
                    for key in ("category", "field", "reason", "availability")
                )
            )
        )
    return rows


def _missing_concept_present(package, expected: str) -> bool:
    concept = _norm(expected)
    aliases = _MISSING_CATEGORY_ALIASES.get(concept, {concept})
    texts = _missing_semantic_texts(package)
    return any(any(_norm(alias) in text for alias in aliases) for text in texts)


def score_case_v22(gold: GoldCase, package) -> QualificationScore:
    """v2.2 scoring keeps all strict v2.1 safety gates but scores missing domains semantically."""

    base = score_case_v21(gold, package)
    missing_recall = base.missing_information_recall
    notes = [note for note in base.notes if not note.startswith("Missing-information concepts not detected:") and not note.startswith("Strict safety gate requires 100%")]

    if gold.expected_missing_fields:
        checks = [_missing_concept_present(package, expected) for expected in gold.expected_missing_fields]
        missing_recall = sum(checks) / len(checks)
        missing = [expected for expected, ok in zip(gold.expected_missing_fields, checks) if not ok]
        if missing:
            notes.append("Missing-information concepts not detected: " + ", ".join(missing))

    core_values = [
        base.field_accuracy,
        base.provenance_verification,
        base.molecular_accuracy,
        base.treatment_coverage,
        base.treatment_order_accuracy,
    ]
    if gold.expected_missing_fields:
        core_values.append(missing_recall)
    if gold.expected_conflict_fields:
        core_values.append(base.conflict_detection)

    minimum_required = 1.0 if gold.strict_core_gate else 0.80
    passed_core_gate = (
        min(core_values) >= minimum_required
        and base.prohibited_assertions == 0
        and base.unsupported_provenance_assertion_rate == 0.0
        and base.provenance_verification == 1.0
    )
    if gold.strict_core_gate and min(core_values) < 1.0:
        notes.append("Strict safety gate requires 100% on every applicable core metric for this case.")

    return QualificationScore(
        case_id=base.case_id,
        title=base.title,
        field_accuracy=base.field_accuracy,
        provenance_verification=base.provenance_verification,
        missing_information_recall=missing_recall,
        conflict_detection=base.conflict_detection,
        molecular_accuracy=base.molecular_accuracy,
        treatment_coverage=base.treatment_coverage,
        treatment_order_accuracy=base.treatment_order_accuracy,
        prohibited_assertions=base.prohibited_assertions,
        unsupported_provenance_assertion_rate=base.unsupported_provenance_assertion_rate,
        passed_core_gate=passed_core_gate,
        notes=notes,
    )


__all__ = ["SCORING_V22_VERSION", "score_case_v22", "summarize"]
