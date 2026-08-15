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


_DIAGNOSIS_ALIASES: dict[str, tuple[str, ...]] = {
    "acute myeloid leukemia": ("acute myeloid leukemia", "aml"),
    "diffuse large b-cell lymphoma": ("diffuse large b-cell lymphoma", "diffuse large b cell lymphoma", "dlbcl"),
    "multiple myeloma": ("multiple myeloma", "plasma cell myeloma"),
    "mantle cell lymphoma": ("mantle cell lymphoma", "mcl"),
    "suspected hematologic malignancy": (
        "suspected hematologic malignancy",
        "suspected haematologic malignancy",
        "hematologic malignancy, suspected",
        "haematologic malignancy, suspected",
        "hematologic malignancy - suspected",
        "haematologic malignancy - suspected",
        "hematologic malignancy",
        "haematologic malignancy",
    ),
}


def _canonical_diagnosis(value: str | None) -> str | None:
    if value is None:
        return None
    text = _norm(value)
    if not text:
        return text
    for canonical, aliases in _DIAGNOSIS_ALIASES.items():
        normalized_aliases = {_norm(alias) for alias in aliases}
        if text == canonical or text in normalized_aliases:
            return canonical
    return text


def _diagnosis_matches(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return _contains(actual, None)
    a = _canonical_diagnosis(actual)
    e = _canonical_diagnosis(expected)
    if a == e and a is not None:
        return True
    return _contains(actual, expected)


def _uncertain_diagnosis_preserved(value: str | None, status) -> bool:
    """Require explicit uncertainty either in the diagnosis wording or its structured status."""
    text = _norm(value)
    status_text = _norm(getattr(status, "value", status))
    uncertainty_terms = ("suspected", "possible", "probable", "working diagnosis", "not established", "unconfirmed")
    if any(term in text for term in uncertainty_terms):
        return True
    return status_text in {"unknown", "not_documented", "not documented", "pending", "unavailable", "not_assessed", "not assessed"}


def _safe_null_diagnosis_abstention(value: str | None, status) -> bool:
    """A null diagnosis is acceptable only when the structured status explicitly preserves uncertainty."""
    return value is None and _uncertain_diagnosis_preserved(value, status)


def _any_term(texts: Iterable[str], term: str) -> bool:
    t = _norm(term)
    return any(t in _norm(x) for x in texts)


_MISSING_ALIASES: dict[str, tuple[str, ...]] = {
    "performance": ("performance", "ecog", "performance status"),
    "renal": ("renal", "creatinine", "kidney", "egfr"),
    "laboratory": ("laboratory", "laboratories", "lab", "labs"),
    "molecular": ("molecular", "genomic", "sequencing"),
    "cytogenetic": ("cytogenetic", "cytogenetics", "karyotype", "fish"),
    "pathology": ("pathology", "pathologic", "biopsy", "marrow"),
    "stage": ("stage", "staging"),
    "treatment": ("treatment", "therapy", "regimen"),
    "flt3": ("flt3",),
}

_CONFLICT_ALIASES: dict[str, tuple[str, ...]] = {
    "pathology": ("pathology", "pathologic", "diagnosis", "marrow", "blast", "blasts"),
    "stage": ("stage", "staging"),
}


def _canonical_missing_concept(term: str) -> str:
    t = _norm(term)
    for concept, aliases in _MISSING_ALIASES.items():
        if t == concept or t in {_norm(a) for a in aliases}:
            return concept
    return t


def _missing_concept_present(texts: Iterable[str], concept: str) -> bool:
    aliases = _MISSING_ALIASES.get(concept, (concept,))
    return any(_any_term(texts, alias) for alias in aliases)


def _canonical_conflict_concept(term: str) -> str:
    t = _norm(term)
    for concept, aliases in _CONFLICT_ALIASES.items():
        if t == concept or t in {_norm(a) for a in aliases}:
            return concept
    return t


def _conflict_concept_present(texts: Iterable[str], concept: str) -> bool:
    aliases = _CONFLICT_ALIASES.get(concept, (concept,))
    return any(_any_term(texts, alias) for alias in aliases)


def _assertion_texts(package: ExtractionPackage) -> list[str]:
    """Return structured model assertions, excluding provenance excerpts and source text."""
    case = package.case
    texts: list[str] = []

    facts = [case.diagnosis, case.disease_state]
    if case.performance_status is not None:
        facts.append(case.performance_status)
    facts += list(case.pathology) + list(case.imaging) + list(case.labs) + list(case.comorbidities)
    facts += list(case.toxicities) + list(case.transplant_cellular_therapy) + list(case.current_medications)
    for fact in facts:
        if fact.value is not None and _norm(fact.value) not in {"", "unknown", "not documented", "not_documented", "pending", "unavailable"}:
            texts.append(str(fact.value))

    for item in case.molecular_findings:
        texts.extend(
            str(value)
            for value in [
                item.gene,
                item.alteration_type,
                item.hgvs_c,
                item.hgvs_p,
                item.laboratory_interpretation,
            ]
            if value
        )

    for treatment in case.treatments:
        texts.append(treatment.regimen)
        texts.extend(treatment.agents)
        if treatment.best_response:
            texts.append(treatment.best_response)
        if treatment.reason_stopped:
            texts.append(treatment.reason_stopped)

    return texts


def _is_positive_prohibited_assertion(text: str, phrase: str) -> bool:
    hay = _norm(text)
    needle = _norm(phrase)
    if needle not in hay:
        return False

    idx = hay.find(needle)
    prefix = hay[max(0, idx - 30):idx]
    negators = ("no ", "not ", "does not ", "did not ", "without ", "not established ")
    return not any(neg in prefix for neg in negators)


def _substantive_fact(fact) -> bool:
    if fact is None or fact.value is None:
        return False
    return _norm(fact.value) not in {"", "unknown", "not documented", "not_documented", "pending", "unavailable", "not assessed", "not_assessed"}


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

    diagnosis_ok = _diagnosis_matches(case.diagnosis.value, gold.expected_diagnosis)
    if gold.allow_null_diagnosis_if_uncertain and _safe_null_diagnosis_abstention(case.diagnosis.value, case.diagnosis.status):
        diagnosis_ok = True
    if gold.strict_core_gate and gold.allow_null_diagnosis_if_uncertain:
        uncertainty_ok = _uncertain_diagnosis_preserved(case.diagnosis.value, case.diagnosis.status)
        diagnosis_ok = diagnosis_ok and uncertainty_ok
        if not uncertainty_ok:
            notes.append("Diagnostic uncertainty was not preserved for the intentionally insufficient case.")

    key_checks = [
        diagnosis_ok,
        _contains(case.disease_state.value if case.disease_state else None, gold.expected_disease_state),
        _contains(case.performance_status.value if case.performance_status else None, gold.expected_ecog),
    ]

    if gold.expected_diagnosis_status:
        actual_status = getattr(case.diagnosis.status, "value", case.diagnosis.status)
        key_checks.append(_norm(actual_status) == _norm(gold.expected_diagnosis_status))
        if not key_checks[-1]:
            notes.append(
                f"Diagnosis status mismatch: expected '{gold.expected_diagnosis_status}', extracted '{actual_status}'"
            )

    field_accuracy = sum(key_checks) / len(key_checks)
    if not key_checks[0]:
        notes.append(f"Diagnosis mismatch: extracted '{case.diagnosis.value}'")
    if not key_checks[1]:
        notes.append(f"Disease-state mismatch: extracted '{case.disease_state.value if case.disease_state else None}'")
    if not key_checks[2]:
        notes.append(f"ECOG/performance mismatch: extracted '{case.performance_status.value if case.performance_status else None}'")

    molecular_genes = [m.gene for m in case.molecular_findings]
    if gold.require_no_molecular_findings:
        molecular_accuracy = 1.0 if not case.molecular_findings else 0.0
        if case.molecular_findings:
            notes.append("Molecular findings were extracted despite the gold case containing no molecular result.")
    elif gold.expected_molecular_genes:
        molecular_hits = sum(1 for g in gold.expected_molecular_genes if _any_term(molecular_genes, g))
        molecular_accuracy = molecular_hits / len(gold.expected_molecular_genes)
    else:
        molecular_accuracy = 1.0

    missing_texts = [f"{m.field} {m.reason} {m.availability}" for m in case.missing_items]
    if gold.expected_missing_fields:
        expected_concepts = sorted({_canonical_missing_concept(term) for term in gold.expected_missing_fields})
        matched = [concept for concept in expected_concepts if _missing_concept_present(missing_texts, concept)]
        unmatched = [concept for concept in expected_concepts if concept not in matched]
        missing_information_recall = len(matched) / len(expected_concepts)
        if unmatched:
            notes.append("Missing-information concepts not detected: " + ", ".join(unmatched))
    else:
        missing_information_recall = 1.0

    conflict_texts = [f"{c.field} {c.value_a} {c.value_b}" for c in case.conflicts]
    if gold.expected_conflict_fields:
        expected_concepts = sorted({_canonical_conflict_concept(term) for term in gold.expected_conflict_fields})
        matched = [concept for concept in expected_concepts if _conflict_concept_present(conflict_texts, concept)]
        unmatched = [concept for concept in expected_concepts if concept not in matched]
        conflict_detection = len(matched) / len(expected_concepts)
        if unmatched:
            notes.append("Expected conflict concepts not detected: " + ", ".join(unmatched))
    else:
        conflict_detection = 1.0

    treatment_names = [" ".join([t.regimen, *t.agents]) for t in case.treatments]
    if gold.require_no_treatments:
        treatment_coverage = 1.0 if not case.treatments else 0.0
        treatment_order_accuracy = treatment_coverage
        if case.treatments:
            notes.append("Treatment episode(s) were extracted despite the gold case containing no treatment history.")
    elif gold.expected_treatments:
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

    assertion_texts = _assertion_texts(package)
    prohibited_hits: list[str] = []
    for phrase in gold.prohibited_confirmed_values:
        if any(_is_positive_prohibited_assertion(text, phrase) for text in assertion_texts):
            prohibited_hits.append(phrase)
    prohibited_assertions = len(prohibited_hits)
    if prohibited_hits:
        notes.append("Detected prohibited/inferred assertion(s): " + ", ".join(prohibited_hits))

    assertion_count = 0
    failed_assertion_prov = 0
    all_facts = [case.diagnosis, case.disease_state]
    if case.performance_status is not None:
        all_facts.append(case.performance_status)
    all_facts += list(case.pathology) + list(case.imaging) + list(case.labs) + list(case.comorbidities) + list(case.toxicities) + list(case.transplant_cellular_therapy) + list(case.current_medications)
    for fact in all_facts:
        if _substantive_fact(fact):
            assertion_count += 1
            if not fact.provenance or not all(p.source_verified for p in fact.provenance):
                failed_assertion_prov += 1
    for item in [*case.molecular_findings, *case.treatments]:
        assertion_count += 1
        if not item.provenance or not all(p.source_verified for p in item.provenance):
            failed_assertion_prov += 1

    unsupported_rate = failed_assertion_prov / assertion_count if assertion_count else 0.0
    provenance_verification = 1.0 - unsupported_rate if assertion_count else 1.0

    core_values = [field_accuracy, provenance_verification, molecular_accuracy, treatment_coverage, treatment_order_accuracy]
    if gold.expected_missing_fields:
        core_values.append(missing_information_recall)
    if gold.expected_conflict_fields:
        core_values.append(conflict_detection)

    minimum_required = 1.0 if gold.strict_core_gate else 0.80
    passed_core_gate = (
        min(core_values) >= minimum_required
        and prohibited_assertions == 0
        and unsupported_rate == 0.0
        and provenance_verification == 1.0
    )
    if gold.strict_core_gate and min(core_values) < 1.0:
        notes.append("Strict safety gate requires 100% on every applicable core metric for this case.")

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
