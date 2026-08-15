from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

from agents.extraction import ExtractionPackage
from qualification.cases import GoldCase


def _norm(value) -> str:
    return " ".join(str(value or "").lower().replace("–", "-").replace("—", "-").split())


def _contains(actual, expected: str | None) -> bool:
    if expected is None:
        return actual is None or _norm(actual) in {"", "unknown", "not documented", "not_documented", "pending", "unavailable"}
    a, e = _norm(actual), _norm(expected)
    return e in a or a in e if a and e else False


def _any_term(texts: Iterable[str], term: str) -> bool:
    t = _norm(term)
    return any(t in _norm(x) for x in texts)


@dataclass
class QualificationScore:
    case_id: str
    title: str
    field_accuracy: float
    provenance_verification: float
    missing_information_recall: float
    conflict_detection: float
    molecular_accuracy: float
    treatment_coverage: float
    treatment_order_accuracy: float
    prohibited_assertions: int
    unsupported_provenance_assertion_rate: float
    passed_core_gate: bool
    notes: list[str]

    def as_dict(self):
        return asdict(self)


def score_case(gold: GoldCase, package: ExtractionPackage) -> QualificationScore:
    case = package.case
    notes: list[str] = []

    key_checks = [
        _contains(case.diagnosis.value, gold.expected_diagnosis),
        _contains(case.disease_state.value if case.disease_state else None, gold.expected_disease_state),
        _contains(case.performance_status.value if case.performance_status else None, gold.expected_ecog),
    ]
    field_accuracy = sum(key_checks) / len(key_checks)
    if not key_checks[0]:
        notes.append(f"Diagnosis mismatch: extracted '{case.diagnosis.value}'")
    if not key_checks[1]:
        notes.append(f"Disease-state mismatch: extracted '{case.disease_state.value if case.disease_state else None}'")
    if not key_checks[2]:
        notes.append(f"ECOG/performance mismatch: extracted '{case.performance_status.value if case.performance_status else None}'")

    molecular_genes = [m.gene for m in case.molecular_findings]
    if gold.expected_molecular_genes:
        molecular_hits = sum(1 for g in gold.expected_molecular_genes if _any_term(molecular_genes, g))
        molecular_accuracy = molecular_hits / len(gold.expected_molecular_genes)
    else:
        molecular_accuracy = 1.0

    missing_texts = [f"{m.field} {m.reason} {m.availability}" for m in case.missing_items]
    if gold.expected_missing_fields:
        hits = sum(1 for term in gold.expected_missing_fields if _any_term(missing_texts, term))
        missing_information_recall = hits / len(gold.expected_missing_fields)
    else:
        missing_information_recall = 1.0

    conflict_texts = [f"{c.field} {c.value_a} {c.value_b}" for c in case.conflicts]
    if gold.expected_conflict_fields:
        hits = sum(1 for term in gold.expected_conflict_fields if _any_term(conflict_texts, term))
        conflict_detection = hits / len(gold.expected_conflict_fields)
    else:
        conflict_detection = 1.0

    treatment_names = [" ".join([t.regimen, *t.agents]) for t in case.treatments]
    if gold.expected_treatments:
        hits = sum(1 for term in gold.expected_treatments if _any_term(treatment_names, term))
        treatment_coverage = hits / len(gold.expected_treatments)
        positions = []
        for term in gold.expected_treatments:
            pos = next((i for i, txt in enumerate(treatment_names) if _norm(term) in _norm(txt)), None)
            if pos is not None:
                positions.append(pos)
        treatment_order_accuracy = 1.0 if len(positions) >= 2 and positions == sorted(positions) else (1.0 if len(positions) <= 1 and treatment_coverage == 1.0 else 0.0)
    else:
        treatment_coverage = 1.0
        treatment_order_accuracy = 1.0

    raw_text = _norm(package.raw_extraction)
    prohibited_assertions = sum(1 for phrase in gold.prohibited_confirmed_values if _norm(phrase) in raw_text)
    if prohibited_assertions:
        notes.append(f"Detected {prohibited_assertions} prohibited/inferred assertion(s) requiring review.")

    confirmed_with_prov = 0
    failed_confirmed_prov = 0
    all_facts = [case.diagnosis, case.disease_state]
    if case.performance_status is not None:
        all_facts.append(case.performance_status)
    all_facts += list(case.pathology) + list(case.imaging) + list(case.labs) + list(case.comorbidities) + list(case.toxicities) + list(case.transplant_cellular_therapy) + list(case.current_medications)
    for fact in all_facts:
        if getattr(fact.status, "value", fact.status) == "confirmed":
            confirmed_with_prov += 1
            if not fact.provenance or not all(p.source_verified for p in fact.provenance):
                failed_confirmed_prov += 1
    for item in [*case.molecular_findings, *case.treatments]:
        confirmed_with_prov += 1
        if not item.provenance or not all(p.source_verified for p in item.provenance):
            failed_confirmed_prov += 1

    unsupported_rate = failed_confirmed_prov / confirmed_with_prov if confirmed_with_prov else 0.0
    provenance_verification = package.provenance_rate

    core_values = [field_accuracy, provenance_verification, molecular_accuracy, treatment_coverage, treatment_order_accuracy]
    if gold.expected_missing_fields:
        core_values.append(missing_information_recall)
    if gold.expected_conflict_fields:
        core_values.append(conflict_detection)

    passed_core_gate = (
        min(core_values) >= 0.80
        and prohibited_assertions == 0
        and unsupported_rate == 0.0
        and provenance_verification == 1.0
    )

    return QualificationScore(
        case_id=gold.case_id,
        title=gold.title,
        field_accuracy=field_accuracy,
        provenance_verification=provenance_verification,
        missing_information_recall=missing_information_recall,
        conflict_detection=conflict_detection,
        molecular_accuracy=molecular_accuracy,
        treatment_coverage=treatment_coverage,
        treatment_order_accuracy=treatment_order_accuracy,
        prohibited_assertions=prohibited_assertions,
        unsupported_provenance_assertion_rate=unsupported_rate,
        passed_core_gate=passed_core_gate,
        notes=notes,
    )


def summarize(scores: list[QualificationScore]) -> dict:
    if not scores:
        return {}
    metrics = [
        "field_accuracy",
        "provenance_verification",
        "missing_information_recall",
        "conflict_detection",
        "molecular_accuracy",
        "treatment_coverage",
        "treatment_order_accuracy",
    ]
    out = {m: sum(getattr(s, m) for s in scores) / len(scores) for m in metrics}
    out["cases_run"] = len(scores)
    out["cases_passing_core_gate"] = sum(1 for s in scores if s.passed_core_gate)
    out["prohibited_assertions"] = sum(s.prohibited_assertions for s in scores)
    total_unsupported = sum(s.unsupported_provenance_assertion_rate for s in scores)
    out["mean_unsupported_provenance_assertion_rate"] = total_unsupported / len(scores)
    return out
