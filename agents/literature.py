from __future__ import annotations

from schemas.case import CancerTumorBoardCase
from schemas.literature import LiteratureReport, LiteratureSearchTrace
from services.pubmed_client import PubMedClient, PubMedClientError


AGENT_ID = "literature"
AGENT_VERSION = "1.0.0"


def _clean_phrase(value: object | None) -> str:
    text = " ".join(str(value or "").strip().split())
    return text.replace('"', "")


def _question_family(case: CancerTumorBoardCase) -> str:
    text = f"{case.clinical_question.question_type} {case.clinical_question.question}".lower()
    if any(token in text for token in ("safety", "toxicity", "interaction", "contraindication")):
        return "safety"
    if any(token in text for token in ("trial", "study")):
        return "trial"
    if any(token in text for token in ("molecular", "mutation", "genomic", "target", "biomarker")):
        return "molecular"
    if any(token in text for token in ("diagnos", "classification", "workup")):
        return "diagnosis"
    return "management"


def build_pubmed_query(case: CancerTumorBoardCase) -> tuple[str, list[str]]:
    """Build a bounded PubMed query from structured clinical concepts only.

    The free-text clinical question is used only to classify the question family. It
    is never sent verbatim to PubMed. This reduces the risk of accidentally sending
    identifiers or narrative details to an external public service.
    """
    diagnosis = _clean_phrase(case.diagnosis.value)
    state = _clean_phrase(case.disease_state.value)
    if not diagnosis:
        raise ValueError("A represented diagnosis is required to construct a PubMed query.")

    terms: list[str] = [f'"{diagnosis}"[Title/Abstract]']
    trace_terms: list[str] = [diagnosis]

    state_lower = state.lower()
    useful_states = ("relapsed", "refractory", "progressive", "progression", "newly diagnosed", "untreated", "maintenance")
    if state and any(token in state_lower for token in useful_states):
        terms.append(f'"{state}"[Title/Abstract]')
        trace_terms.append(state)

    genes = sorted({m.gene.strip().upper() for m in case.molecular_findings if m.gene.strip()})
    if genes:
        gene_clause = " OR ".join(f'"{gene}"[Title/Abstract]' for gene in genes[:5])
        terms.append(f"({gene_clause})")
        trace_terms.extend(genes[:5])

    family = _question_family(case)
    if family == "safety":
        terms.append('(toxicity[Title/Abstract] OR safety[Title/Abstract] OR adverse[Title/Abstract])')
        trace_terms.append("safety/toxicity")
    elif family == "trial":
        terms.append('(clinical trial[Publication Type] OR trial[Title/Abstract])')
        trace_terms.append("clinical trial")
    elif family == "molecular":
        terms.append('(molecular[Title/Abstract] OR genomic[Title/Abstract] OR biomarker[Title/Abstract])')
        trace_terms.append("molecular/genomic")
    elif family == "diagnosis":
        terms.append('(diagnosis[Title/Abstract] OR classification[Title/Abstract])')
        trace_terms.append("diagnosis/classification")
    else:
        terms.append('(treatment[Title/Abstract] OR therapy[Title/Abstract] OR management[Title/Abstract])')
        trace_terms.append("treatment/therapy")

    return " AND ".join(terms), trace_terms


class LiteratureAgent:
    """PubMed retrieval specialist with a strict claim boundary.

    Version 1 retrieves and normalizes PubMed records. It does not interpret study
    results, infer efficacy, compare treatments, or convert abstracts into clinical
    recommendations. Retrieval is evidence discovery, not evidence verification.
    """

    agent_id = AGENT_ID
    agent_version = AGENT_VERSION

    def __init__(self, client: PubMedClient | None = None, *, retmax: int = 10) -> None:
        self.client = client
        self.retmax = max(1, min(25, int(retmax)))

    def run(self, case: CancerTumorBoardCase) -> LiteratureReport:
        if case.disease_program != "hematologic_malignancy":
            return LiteratureReport(
                case_id=case.case_id,
                status="abstain_domain",
                summary="Literature Agent v1 is restricted to hematologic malignancy cases.",
                limitations=["Case is outside the v1 hematologic-malignancy domain."],
                can_support_literature_claim=False,
            )

        if self.client is None:
            return LiteratureReport(
                case_id=case.case_id,
                status="source_unavailable",
                summary="No PubMed client is configured; literature retrieval was not attempted.",
                limitations=["Configure an NCBI E-utilities contact email before enabling live PubMed retrieval."],
                can_support_literature_claim=False,
            )

        try:
            query, query_terms = build_pubmed_query(case)
            search_result, articles = self.client.search_and_fetch(query, retmax=self.retmax, sort="pub date")
        except (PubMedClientError, ValueError) as exc:
            return LiteratureReport(
                case_id=case.case_id,
                status="tool_failure",
                summary="PubMed retrieval failed; no literature claim was generated.",
                warnings=[str(exc)],
                can_support_literature_claim=False,
            )

        trace = LiteratureSearchTrace(
            query=query,
            sort="pub date",
            requested_limit=self.retmax,
            retrieved_pmids=list(search_result.pmids),
            retrieved_count=len(articles),
            query_terms=query_terms,
        )

        if not articles:
            return LiteratureReport(
                case_id=case.case_id,
                status="no_evidence_found",
                search_trace=trace,
                summary="PubMed returned no records for the bounded structured query.",
                limitations=["A no-result search does not establish absence of evidence."],
                can_support_literature_claim=False,
            )

        warnings: list[str] = []
        if len(articles) != len(search_result.pmids):
            warnings.append(
                f"ESearch returned {len(search_result.pmids)} PMID(s), while EFetch yielded {len(articles)} parseable record(s)."
            )

        return LiteratureReport(
            case_id=case.case_id,
            status="completed_with_limitations",
            search_trace=trace,
            articles=articles,
            warnings=warnings,
            limitations=[
                "PubMed retrieval identifies candidate literature but does not verify a clinical claim.",
                "Abstract availability does not imply full-text availability or sufficient evidence for decision support.",
                "Study design, population, endpoints, effect estimates, bias, applicability, and contradictions require a separate evidence-verification step.",
            ],
            summary=f"Retrieved {len(articles)} PubMed record(s) using a bounded query derived from structured case concepts.",
            can_support_literature_claim=False,
        )
