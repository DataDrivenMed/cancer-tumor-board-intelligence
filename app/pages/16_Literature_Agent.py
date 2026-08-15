from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.literature import LiteratureAgent, build_pubmed_query
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MolecularFinding, Provenance
from services.pubmed_client import PubMedClient


st.set_page_config(page_title="Literature Agent", page_icon="📚", layout="wide")
st.title("Literature Agent v1.0.0")
st.caption("Live PubMed candidate-literature retrieval through NCBI E-utilities, with a strict no-claim boundary.")
st.warning(
    "Development environment only. Synthetic/de-identified cases only. PubMed retrieval identifies candidate literature; it does not generate clinical recommendations or verify efficacy claims."
)


def prov(text: str) -> Provenance:
    return Provenance(
        document_id="LITERATURE-DEMO",
        source_excerpt=text,
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def fact(field: str, value: str) -> Fact:
    return Fact(field=field, value=value, provenance=[prov(value)])


def case_for(name: str) -> CancerTumorBoardCase:
    if name == "Relapsed AML management":
        return CancerTumorBoardCase(
            case_id="LIT-DEMO-RELAPSED-AML",
            diagnosis=fact("diagnosis", "acute myeloid leukemia"),
            disease_state=fact("disease_state", "relapsed"),
            performance_status=fact("ECOG", "1"),
            clinical_question=ClinicalQuestion(
                question_type="management",
                question="What treatment strategies should be discussed?",
            ),
        )
    if name == "Newly diagnosed AML with FLT3":
        case = CancerTumorBoardCase(
            case_id="LIT-DEMO-FLT3-AML",
            diagnosis=fact("diagnosis", "acute myeloid leukemia"),
            disease_state=fact("disease_state", "newly diagnosed"),
            performance_status=fact("ECOG", "1"),
            clinical_question=ClinicalQuestion(
                question_type="molecular_management",
                question="How should molecular evidence be reviewed?",
            ),
        )
        case.molecular_findings = [MolecularFinding(
            gene="FLT3",
            alteration_type="ITD",
            provenance=[prov("FLT3-ITD detected")],
        )]
        return case
    return CancerTumorBoardCase(
        case_id="LIT-DEMO-SAFETY-AML",
        diagnosis=fact("diagnosis", "acute myeloid leukemia"),
        disease_state=fact("disease_state", "relapsed"),
        performance_status=fact("ECOG", "1"),
        clinical_question=ClinicalQuestion(
            question_type="safety",
            question="What safety evidence should be reviewed?",
        ),
    )


scenario = st.selectbox(
    "Synthetic PubMed retrieval scenario",
    ["Relapsed AML management", "Newly diagnosed AML with FLT3", "Relapsed AML safety"],
)
case = case_for(scenario)
query, query_terms = build_pubmed_query(case)

st.markdown("### Structured search plan")
left, right = st.columns([1, 1])
with left:
    st.write(f"**Case:** {case.case_id}")
    st.write(f"**Diagnosis:** {case.diagnosis.value}")
    st.write(f"**Disease state:** {case.disease_state.value}")
    st.write(f"**Molecular findings:** {', '.join(m.gene for m in case.molecular_findings) or 'None'}")
with right:
    st.write("**Bounded query terms:** " + " · ".join(query_terms))
    st.code(query, language="text")

st.info(
    "The free-text clinical question is not sent to PubMed. The query is constructed from bounded structured concepts to reduce accidental disclosure of narrative identifiers."
)

try:
    default_email = str(st.secrets.get("NCBI_CONTACT_EMAIL", ""))
except Exception:
    default_email = ""

contact_email = st.text_input(
    "NCBI contact email",
    value=default_email,
    help="NCBI recommends including a valid contact email on E-utility requests. You may store NCBI_CONTACT_EMAIL in Streamlit secrets.",
)
retmax = st.slider("Maximum PubMed records", min_value=1, max_value=20, value=10)

try:
    api_key = str(st.secrets.get("NCBI_API_KEY", "")) or None
except Exception:
    api_key = None

if st.button("Run live PubMed retrieval", type="primary"):
    if not contact_email.strip():
        st.error("Enter an NCBI contact email before running live PubMed retrieval.")
    else:
        with st.spinner("Searching PubMed through NCBI E-utilities..."):
            client = PubMedClient(email=contact_email, api_key=api_key)
            st.session_state["literature_agent_report"] = LiteratureAgent(client, retmax=retmax).run(case)

report = st.session_state.get("literature_agent_report")
if report is not None:
    st.markdown("### Literature Agent result")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", report.status.replace("_", " ").upper())
    c2.metric("Articles", len(report.articles))
    c3.metric("PubMed claim support", "YES" if report.can_support_literature_claim else "NO")
    c4.metric("Agent version", report.agent_version)

    if report.status in {"tool_failure", "source_unavailable"}:
        st.error(report.summary)
    elif report.status == "no_evidence_found":
        st.warning(report.summary)
    else:
        st.success(report.summary)

    if report.search_trace is not None:
        st.markdown("#### Search audit trace")
        st.write(f"**Database:** {report.search_trace.database}")
        st.write(f"**Sort:** {report.search_trace.sort}")
        st.write(f"**Retrieved PMIDs:** {', '.join(report.search_trace.retrieved_pmids) or 'None'}")
        st.code(report.search_trace.query, language="text")

    if report.articles:
        st.markdown("#### Candidate literature")
        for idx, article in enumerate(report.articles, start=1):
            with st.expander(f"{idx}. {article.title}"):
                st.write(f"**PMID:** {article.pmid}")
                st.write(f"**Journal:** {article.journal or 'Not represented'}")
                st.write(f"**Publication date:** {article.publication_date_text or article.publication_date or 'Not represented'}")
                st.write(f"**Authors:** {', '.join(article.authors[:8]) or 'Not represented'}")
                st.write(f"**Publication types:** {', '.join(article.publication_types) or 'Not represented'}")
                st.write(f"**DOI:** {article.doi or 'Not represented'}")
                st.write(f"**PMCID:** {article.pmcid or 'Not represented'}")
                st.write(f"**Abstract available:** {'Yes' if article.abstract_available else 'No'}")
                if article.abstract_sha256:
                    st.code(article.abstract_sha256, language="text")
                if article.abstract_excerpt:
                    st.caption("Short PubMed abstract excerpt for retrieval inspection only:")
                    st.write(article.abstract_excerpt)
                st.link_button("Open PubMed record", article.pubmed_url)

    for warning in report.warnings:
        st.warning(warning)
    for limitation in report.limitations:
        st.info(limitation)

    with st.expander("Typed LiteratureReport"):
        st.json(report.model_dump(mode="json"))

st.divider()
st.caption(
    "PubMed retrieval is a discovery layer. A separate evidence-verification layer must inspect study design, population, endpoints, results, applicability, contradictions, and exact supporting text before any clinical claim is propagated."
)
