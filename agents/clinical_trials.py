from __future__ import annotations

from schemas.case import CancerTumorBoardCase
from schemas.clinical_trials import ClinicalTrialsReport, TrialMatch, TrialSearchTrace
from services.clinicaltrials_client import ClinicalTrialsClient, ClinicalTrialsClientError


AGENT_ID = "clinical_trials"
AGENT_VERSION = "1.0.0"

_ACTIVE_RECRUITMENT = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION"}


def _clean(value: object | None) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: object | None) -> str:
    return _clean(value).lower().replace("_", " ")


def build_trial_query(case: CancerTumorBoardCase) -> tuple[str, list[str]]:
    """Build a bounded trial query from canonical structured concepts.

    Free-text tumor-board narrative and care-site data are not transmitted.
    """
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
    if diagnosis_norm and (diagnosis_norm in condition_blob or diagnosis_norm in title_blob):
        matched.append(f"diagnosis:{diagnosis}")

    searchable = " | ".join(
        [title_blob, condition_blob]
        + [_norm(x) for x in record.interventions]
        + [_norm(record.eligibility_criteria)]
    )
    for gene in genes:
        if _norm(gene) in searchable:
            matched.append(f"gene:{gene}")
    return matched


class ClinicalTrialsAgent:
    """ClinicalTrials.gov retrieval and candidate-matching specialist.

    Trial matching is intentionally distinct from eligibility determination. The
    agent does not assert that a patient is eligible, available at a site, or should
    receive an investigational intervention.
    """

    agent_id = AGENT_ID
    agent_version = AGENT_VERSION

    def __init__(self, client: ClinicalTrialsClient | None = None, *, page_size: int = 10) -> None:
        self.client = client
        self.page_size = max(1, min(50, int(page_size)))

    def run(self, case: CancerTumorBoardCase) -> ClinicalTrialsReport:
        if case.disease_program != "hematologic_malignancy":
            return ClinicalTrialsReport(
                case_id=case.case_id,
                status="abstain_domain",
                summary="Clinical Trials Agent v1 is restricted to hematologic malignancy cases.",
                limitations=["Case is outside the v1 hematologic-malignancy domain."],
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

        trace = TrialSearchTrace(
            query_condition=condition,
            query_terms=genes,
            requested_limit=self.page_size,
            returned_count=len(records),
            data_timestamp=timestamp,
        )
        if not records:
            return ClinicalTrialsReport(
                case_id=case.case_id,
                status="no_evidence_found",
                search_trace=trace,
                summary="ClinicalTrials.gov returned no study records for the bounded structured query.",
                limitations=["A no-result query does not establish that no relevant trial exists."],
            )

        matches: list[TrialMatch] = []
        for record in records:
            concepts = _concept_matches(record, condition, genes)
            active = (record.overall_status or "").upper() in _ACTIVE_RECRUITMENT
            if not concepts or not active:
                continue
            unresolved = [
                "full inclusion/exclusion criteria",
                "site-specific recruitment status",
                "investigator confirmation",
                "patient-specific laboratory and organ-function criteria",
                "prior-therapy and washout requirements",
            ]
            matches.append(
                TrialMatch(
                    nct_id=record.nct_id,
                    title=record.title,
                    overall_status=record.overall_status,
                    matched_concepts=concepts,
                    unresolved_eligibility_domains=unresolved,
                    eligibility_determined=False,
                    eligible=None,
                    match_strength="possible",
                    rationale="Current ClinicalTrials.gov record has active recruitment status and overlaps one or more bounded structured case concepts. Eligibility has not been determined.",
                    source_url=record.source_url,
                )
            )

        if not matches:
            return ClinicalTrialsReport(
                case_id=case.case_id,
                status="no_evidence_found",
                search_trace=trace,
                records=records,
                summary="Study records were retrieved, but none met the deterministic active-recruitment plus structured-concept match rule.",
                limitations=["Retrieved records may still warrant manual review; no eligibility inference was made."],
            )

        return ClinicalTrialsReport(
            case_id=case.case_id,
            status="completed_with_limitations",
            search_trace=trace,
            records=records,
            matches=matches,
            summary=f"Identified {len(matches)} possible actively recruiting trial match(es) from {len(records)} retrieved ClinicalTrials.gov record(s).",
            limitations=[
                "TRIAL MATCH IS NOT TRIAL ELIGIBILITY.",
                "ClinicalTrials.gov recruitment status can change and must be rechecked at decision time.",
                "Site availability and patient-specific inclusion/exclusion criteria require direct study-team confirmation.",
                "The agent does not recommend enrollment or rank investigational therapies by expected benefit.",
            ],
            can_support_trial_match_claim=True,
            can_support_eligibility_claim=False,
        )
