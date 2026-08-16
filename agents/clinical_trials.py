from __future__ import annotations

import re

from schemas.case import CancerTumorBoardCase
from schemas.clinical_trials import ClinicalTrialsReport, TrialMatch, TrialSearchTrace
from services.clinicaltrials_client import ClinicalTrialsClient, ClinicalTrialsClientError
from services.oncology_programs import is_registered_oncology_program


AGENT_ID = "clinical_trials"
AGENT_VERSION = "1.2.0"

_ACTIVE_RECRUITMENT = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}


def _clean(value: object | None) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: object | None) -> str:
    return _clean(value).lower().replace("_", " ")


def _age_in_years(value: str | None) -> float | None:
    text = _norm(value)
    if not text or text in {"n/a", "na", "none"}:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*(year|month|week|day)s?", text)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "year": return amount
    if unit == "month": return amount / 12.0
    if unit == "week": return amount / 52.1429
    if unit == "day": return amount / 365.25
    return None


def _age_compatible(case_age: int | None, record) -> tuple[bool, str | None]:
    if case_age is None:
        return True, None
    minimum = _age_in_years(record.minimum_age)
    maximum = _age_in_years(record.maximum_age)
    if minimum is not None and case_age < minimum:
        return False, f"patient age {case_age} is below registry minimum age {record.minimum_age}"
    if maximum is not None and case_age > maximum:
        return False, f"patient age {case_age} exceeds registry maximum age {record.maximum_age}"
    return True, None


def build_trial_query(case: CancerTumorBoardCase) -> tuple[str, list[str]]:
    diagnosis = _clean(case.diagnosis.value)
    if not diagnosis:
        raise ValueError("A represented diagnosis is required for trial retrieval.")
    genes = sorted({m.gene.strip().upper() for m in case.molecular_findings if m.gene.strip()})[:5]
    return diagnosis, genes


def _concept_matches(record, diagnosis: str, genes: list[str]) -> list[str]:
    matched: list[str] = []
    diagnosis_norm = _norm(diagnosis)
    condition_blob = " | ".join(_norm(x) for x in record.conditions)
    title_blob = _norm(record.title)
    disease_match = bool(diagnosis_norm and (diagnosis_norm in condition_blob or diagnosis_norm in title_blob))
    if not disease_match:
        return []
    matched.append(f"diagnosis:{diagnosis}")
    searchable = " | ".join([title_blob, condition_blob] + [_norm(x) for x in record.interventions] + [_norm(record.eligibility_criteria)])
    for gene in genes:
        if _norm(gene) in searchable:
            matched.append(f"gene:{gene}")
    return matched


class ClinicalTrialsAgent:
    """Pan-oncology ClinicalTrials.gov retrieval and candidate-matching specialist."""

    agent_id = AGENT_ID
    agent_version = AGENT_VERSION

    def __init__(self, client: ClinicalTrialsClient | None = None, *, page_size: int = 10) -> None:
        self.client = client
        self.page_size = max(1, min(50, int(page_size)))

    def run(self, case: CancerTumorBoardCase) -> ClinicalTrialsReport:
        if not is_registered_oncology_program(case.disease_program):
            return ClinicalTrialsReport(
                case_id=case.case_id,
                status="abstain_domain",
                summary="Clinical Trials Agent received a case outside the registered oncology programs.",
                limitations=["The disease program must be classified into the governed pan-oncology registry before trial retrieval."],
            )
        if self.client is None:
            return ClinicalTrialsReport(
                case_id=case.case_id,
                status="source_unavailable",
                summary="No ClinicalTrials.gov client is configured; trial retrieval was not attempted.",
                limitations=["Enable the official ClinicalTrials.gov API v2 client to retrieve current study records."],
            )

        try:
            condition, genes = build_trial_query(case)
            timestamp, records = self.client.search(condition=condition, other_terms=genes, page_size=self.page_size)
        except (ClinicalTrialsClientError, ValueError) as exc:
            return ClinicalTrialsReport(
                case_id=case.case_id,
                status="tool_failure",
                summary="ClinicalTrials.gov retrieval failed; no trial-match claim was generated.",
                warnings=[str(exc)],
            )

        trace = TrialSearchTrace(query_condition=condition, query_terms=genes, requested_limit=self.page_size, returned_count=len(records), data_timestamp=timestamp)
        if not records:
            return ClinicalTrialsReport(
                case_id=case.case_id,
                status="no_evidence_found",
                search_trace=trace,
                summary="ClinicalTrials.gov returned no study records for the bounded structured query.",
                limitations=["A no-result query does not establish that no relevant trial exists."],
            )

        matches: list[TrialMatch] = []
        age_excluded: list[str] = []
        for record in records:
            concepts = _concept_matches(record, condition, genes)
            active = (record.overall_status or "").upper() in _ACTIVE_RECRUITMENT
            if not concepts or not active:
                continue
            age_ok, age_reason = _age_compatible(case.age, record)
            if not age_ok:
                age_excluded.append(f"{record.nct_id}: {age_reason}")
                continue
            unresolved = [
                "full inclusion/exclusion criteria", "site-specific recruitment status", "investigator confirmation",
                "patient-specific laboratory and organ-function criteria", "prior-therapy and washout requirements",
            ]
            if case.age is None:
                unresolved.append("age eligibility")
            matched_concepts = list(concepts)
            if case.age is not None and (record.minimum_age or record.maximum_age):
                matched_concepts.append("age:registry-bounds-compatible")
            matches.append(TrialMatch(
                nct_id=record.nct_id, title=record.title, overall_status=record.overall_status,
                matched_concepts=matched_concepts, unresolved_eligibility_domains=unresolved,
                eligibility_determined=False, eligible=None, match_strength="possible",
                rationale="Current ClinicalTrials.gov record has active recruitment status, overlaps the represented disease context, and is not excluded by explicit registry age bounds. Eligibility has not been determined.",
                source_url=record.source_url,
            ))

        warnings = []
        if age_excluded:
            warnings.append(f"Excluded {len(age_excluded)} otherwise disease-matched active trial record(s) because explicit registry age bounds were incompatible with the represented age.")
        if not matches:
            return ClinicalTrialsReport(
                case_id=case.case_id, status="no_evidence_found", search_trace=trace, records=records, warnings=warnings,
                summary="Study records were retrieved, but none met the deterministic active-recruitment, disease-context, and explicit-age-bound screening rules.",
                limitations=["Retrieved records may still warrant manual review; no eligibility inference was made."],
            )

        return ClinicalTrialsReport(
            case_id=case.case_id, status="completed_with_limitations", search_trace=trace, records=records, matches=matches, warnings=warnings,
            summary=f"Identified {len(matches)} possible actively recruiting trial match(es) from {len(records)} retrieved ClinicalTrials.gov record(s) after deterministic age-bound screening.",
            limitations=[
                "TRIAL MATCH IS NOT TRIAL ELIGIBILITY.",
                "ClinicalTrials.gov recruitment status can change and must be rechecked at decision time.",
                "Age-bound screening only excludes explicit incompatibility; it does not establish eligibility.",
                "Site availability and patient-specific inclusion/exclusion criteria require direct study-team confirmation.",
                "The agent does not recommend enrollment or rank investigational therapies by expected benefit.",
            ],
            can_support_trial_match_claim=True, can_support_eligibility_claim=False,
        )
