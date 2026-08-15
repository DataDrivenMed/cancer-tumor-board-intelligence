from __future__ import annotations

import re
from typing import Any

from qualification.cases import GoldCase
from qualification.scoring import (
    QualificationScore,
    _contains,
    _norm,
    _uncertain_diagnosis_preserved,
    score_case,
    summarize,
)


SCORING_V21_VERSION = "2.1.0"


_DISEASE_STATE_EQUIVALENCE: dict[str, tuple[str, ...]] = {
    "progressive": (
        "progressive",
        "progression",
        "progressive disease",
        "disease progression",
        "radiographic progression",
        "radiographic progressive disease",
        "progressing",
    ),
    "metastatic": (
        "metastatic",
        "metastatic disease",
    ),
    "recurrent": ("recurrent", "recurrence"),
    "relapsed": ("relapsed", "relapse"),
    "refractory": ("refractory", "treatment refractory"),
    "remission": ("remission", "in remission"),
    "newly diagnosed": ("newly diagnosed", "new diagnosis", "newly-diagnosed"),
    "persistent": ("persistent", "persistent disease"),
}

_UNCERTAINTY_WORDS = re.compile(
    r"\b(suspected|possible|probable|working diagnosis of|working diagnosis|unconfirmed)\b",
    re.I,
)
_UNKNOWN_PRIMARY_WORDS = re.compile(
    r"\b(primary site unknown|unknown primary|of unknown primary)\b",
    re.I,
)
_NONALNUM = re.compile(r"[^a-z0-9]+")


def _canonical_disease_state(value: str | None) -> str | None:
    if value is None:
        return None
    text = _norm(value)
    for canonical, variants in _DISEASE_STATE_EQUIVALENCE.items():
        if text == canonical or text in {_norm(variant) for variant in variants}:
            return canonical
    return text


def _disease_state_matches_v21(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return _contains(actual, None)
    return _canonical_disease_state(actual) == _canonical_disease_state(expected) or _contains(actual, expected)


def _certainty_stripped_diagnosis(value: str | None) -> str:
    text = _norm(value)
    text = _UNCERTAINTY_WORDS.sub(" ", text)
    text = _UNKNOWN_PRIMARY_WORDS.sub(" ", text)
    text = _NONALNUM.sub(" ", text)
    return " ".join(text.split())


def _diagnosis_matches_v21(gold: GoldCase, actual_value: str | None, actual_status: Any) -> bool:
    if gold.expected_diagnosis is None:
        if gold.allow_null_diagnosis_if_uncertain:
            return actual_value is None and _uncertain_diagnosis_preserved(actual_value, actual_status)
        return _contains(actual_value, None)

    if _contains(actual_value, gold.expected_diagnosis):
        return True

    if gold.allow_null_diagnosis_if_uncertain:
        if actual_value is None:
            return _uncertain_diagnosis_preserved(actual_value, actual_status)
        expected_entity = _certainty_stripped_diagnosis(gold.expected_diagnosis)
        actual_entity = _certainty_stripped_diagnosis(actual_value)
        same_entity = bool(expected_entity and actual_entity) and (
            expected_entity == actual_entity
            or expected_entity in actual_entity
            or actual_entity in expected_entity
        )
        return same_entity and _uncertain_diagnosis_preserved(actual_value, actual_status)

    return False


def score_case_v21(gold: GoldCase, package) -> QualificationScore:
    """Score with explicit semantic equivalence while preserving all original safety gates."""

    base = score_case(gold, package)
    case = package.case

    diagnosis_ok = _diagnosis_matches_v21(gold, case.diagnosis.value, case.diagnosis.status)
    if gold.strict_core_gate and gold.allow_null_diagnosis_if_uncertain:
        diagnosis_ok = diagnosis_ok and _uncertain_diagnosis_preserved(case.diagnosis.value, case.diagnosis.status)

    disease_state_ok = _disease_state_matches_v21(
        case.disease_state.value if case.disease_state else None,
        gold.expected_disease_state,
    )
    ecog_ok = _contains(
        case.performance_status.value if case.performance_status else None,
        gold.expected_ecog,
    )

    key_checks = [diagnosis_ok, disease_state_ok, ecog_ok]
    if gold.expected_diagnosis_status:
        actual_status = getattr(case.diagnosis.status, "value", case.diagnosis.status)
        key_checks.append(_norm(actual_status) == _norm(gold.expected_diagnosis_status))

    field_accuracy = sum(key_checks) / len(key_checks)

    notes = [
        note
        for note in base.notes
        if not note.startswith("Diagnosis mismatch:")
        and not note.startswith("Disease-state mismatch:")
        and not note.startswith("ECOG/performance mismatch:")
        and not note.startswith("Diagnostic uncertainty was not preserved")
        and not note.startswith("Strict safety gate requires 100%")
    ]
    if not diagnosis_ok:
        notes.append(f"Diagnosis mismatch: extracted '{case.diagnosis.value}'")
    if not disease_state_ok:
        notes.append(
            f"Disease-state mismatch: extracted '{case.disease_state.value if case.disease_state else None}'"
        )
    if not ecog_ok:
        notes.append(
            f"ECOG/performance mismatch: extracted '{case.performance_status.value if case.performance_status else None}'"
        )

    core_values = [
        field_accuracy,
        base.provenance_verification,
        base.molecular_accuracy,
        base.treatment_coverage,
        base.treatment_order_accuracy,
    ]
    if gold.expected_missing_fields:
        core_values.append(base.missing_information_recall)
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
        field_accuracy=field_accuracy,
        provenance_verification=base.provenance_verification,
        missing_information_recall=base.missing_information_recall,
        conflict_detection=base.conflict_detection,
        molecular_accuracy=base.molecular_accuracy,
        treatment_coverage=base.treatment_coverage,
        treatment_order_accuracy=base.treatment_order_accuracy,
        prohibited_assertions=base.prohibited_assertions,
        unsupported_provenance_assertion_rate=base.unsupported_provenance_assertion_rate,
        passed_core_gate=passed_core_gate,
        notes=notes,
    )


__all__ = ["SCORING_V21_VERSION", "score_case_v21", "summarize"]
