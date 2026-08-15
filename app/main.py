from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.extraction import extract_case
from orchestration.workflow import run_workflow
from schemas.case import CancerTumorBoardCase, InformationType, Provenance
from services.document_parser import parse_text, parse_upload
from services.model_gateway import ModelGatewayError


st.set_page_config(
    page_title="Cancer Tumor Board Intelligence",
    page_icon="🧬",
    layout="wide",
)


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def add_human_correction(fact, old_value, new_value):
    if str(old_value) == str(new_value):
        fact.human_verified = True
        return
    fact.value = new_value
    fact.human_verified = True
    fact.information_type = InformationType.OBSERVED
    fact.provenance.append(
        Provenance(
            document_id="HUMAN-REVIEW",
            document_type="human_correction",
            source_excerpt=f"Reviewer corrected value from '{old_value}' to '{new_value}'.",
            source_verified=True,
            author_role="tumor_board_reviewer",
        )
    )


st.title("Cancer Tumor Board Intelligence")
st.caption("Research prototype • Synthetic/de-identified cases only • Step 9: provenance-aware case extraction")
st.warning("Development environment only. Do not enter or upload protected health information (PHI).")

tabs = st.tabs([
    "Case & Extraction",
    "Data Quality",
    "Routing & Agents",
    "Tumor Board Brief",
    "Audit",
])

for key, default in {
    "result": None,
    "extraction_package": None,
    "parsed_document": None,
    "reviewed_case": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

with tabs[0]:
    st.subheader("Case ingestion and extraction")
    st.write(
        "The extraction layer converts narrative tumor-board material into a structured case while retaining exact source provenance. "
        "No treatment recommendation is generated at this stage."
    )

    mode = st.radio(
        "Input method",
        [
            "Load synthetic structured example",
            "Extract synthetic narrative",
            "Paste synthetic/de-identified narrative",
            "Upload synthetic/de-identified document",
        ],
        horizontal=False,
    )

    parsed_document = None
    direct_case = None

    if mode == "Load synthetic structured example":
        sample_path = PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.json"
        sample_data = json.loads(sample_path.read_text(encoding="utf-8"))
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Disease", "AML")
        col2.metric("Disease state", "Relapsed")
        col3.metric("Molecular", "FLT3-ITD")
        col4.metric("ECOG", "1")
        with st.expander("View canonical synthetic case"):
            st.code(json.dumps(sample_data, indent=2), language="json")
        if st.button("Run structured development workflow", type="primary"):
            direct_case = CancerTumorBoardCase.model_validate(sample_data)

    elif mode == "Extract synthetic narrative":
        narrative_path = PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.txt"
        narrative = narrative_path.read_text(encoding="utf-8")
        st.text_area("Synthetic source narrative", value=narrative, height=300, disabled=True)
        parsed_document = parse_text(narrative, document_id="SYN-DOC-NARRATIVE", filename="syn_aml_001.txt")

    elif mode == "Paste synthetic/de-identified narrative":
        narrative = st.text_area(
            "Paste narrative",
            height=300,
            placeholder="Paste a synthetic or fully de-identified tumor-board narrative here. Do not enter PHI.",
        )
        if narrative.strip():
            parsed_document = parse_text(narrative, document_id="DOC-PASTED", filename="pasted_case.txt")

    else:
        uploaded = st.file_uploader(
            "Upload PDF, DOCX, TXT or MD",
            type=["pdf", "docx", "txt", "md"],
            help="Synthetic or fully de-identified material only in this public development environment.",
        )
        if uploaded:
            try:
                parsed_document = parse_upload(uploaded.name, uploaded.getvalue(), document_id="DOC-UPLOAD")
            except Exception as exc:
                st.error(f"Could not parse file: {exc}")

    if parsed_document is not None:
        st.session_state.parsed_document = parsed_document
        c1, c2 = st.columns(2)
        c1.metric("Source segments", len(parsed_document.segments))
        c2.metric("Document type", parsed_document.document_type.upper())
        with st.expander("Inspect provenance-ready source segments"):
            st.code(parsed_document.numbered_text(), language="text")

        api_key = get_secret("OPENAI_API_KEY")
        model = get_secret("OPENAI_EXTRACTION_MODEL", "gpt-5") or "gpt-5"

        if not api_key:
            st.warning(
                "AI extraction is installed but not activated because OPENAI_API_KEY has not yet been added to Streamlit Secrets. "
                "The structured synthetic workflow remains available without a key."
            )
        else:
            st.caption(f"Extraction model configured: {model}")
            if st.button("Extract structured case with AI", type="primary"):
                try:
                    with st.spinner("Extracting patient facts and verifying source provenance..."):
                        package = extract_case(
                            document=parsed_document,
                            api_key=api_key,
                            model=model,
                            case_id="EXTRACTED-001",
                        )
                    st.session_state.extraction_package = package
                    st.session_state.reviewed_case = None
                    st.session_state.result = None
                except ModelGatewayError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Extraction failed safely: {exc}")

    package = st.session_state.extraction_package
    if package is not None:
        st.divider()
        st.subheader("Extraction quality control")

        total = package.provenance_total
        verified = package.provenance_verified
        rate = package.provenance_rate * 100 if total else 0
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Provenance anchors", total)
        q2.metric("Exact verified", verified)
        q3.metric("Verification rate", f"{rate:.1f}%")
        q4.metric("Provenance failures", len(package.provenance_failures))

        if package.provenance_failures:
            st.error(
                "Some extracted claims failed exact source verification. These items must not be treated as verified facts until reviewed."
            )
            st.write("Failed items: " + ", ".join(package.provenance_failures))
        else:
            st.success("All extracted items carrying provenance passed exact source-segment verification.")

        for warning in package.warnings:
            st.warning(warning)

        case = package.case
        st.markdown("### Clinician verification")
        st.caption(
            "Review the decision-critical extraction before allowing downstream routing. Changes are recorded as human corrections in provenance."
        )

        with st.form("clinical_review_form"):
            r1, r2, r3 = st.columns(3)
            diagnosis_value = r1.text_input("Diagnosis", value=str(case.diagnosis.value or ""))
            disease_state_value = r2.text_input("Disease state", value=str(case.disease_state.value or ""))
            ecog_value = r3.text_input(
                "Performance status / ECOG",
                value=str(case.performance_status.value or "") if case.performance_status else "",
            )
            question_value = st.text_area("Clinical question", value=case.clinical_question.question, height=90)

            st.markdown("#### Molecular findings")
            molecular_checks = []
            if case.molecular_findings:
                for idx, item in enumerate(case.molecular_findings):
                    label = f"Verify {item.gene} {item.alteration_type or ''}".strip()
                    molecular_checks.append(st.checkbox(label, key=f"mol_verify_{idx}"))
            else:
                st.info("No molecular findings extracted.")

            st.markdown("#### Treatment history")
            treatment_checks = []
            if case.treatments:
                for idx, item in enumerate(case.treatments):
                    treatment_checks.append(
                        st.checkbox(f"Verify treatment episode: {item.regimen}", key=f"tx_verify_{idx}")
                    )
            else:
                st.info("No treatment episodes extracted.")

            confirm = st.form_submit_button("Confirm reviewed case for downstream workflow", type="primary")

        if confirm:
            add_human_correction(case.diagnosis, case.diagnosis.value, diagnosis_value)
            add_human_correction(case.disease_state, case.disease_state.value, disease_state_value)
            if case.performance_status is not None:
                add_human_correction(case.performance_status, case.performance_status.value, ecog_value)
            case.clinical_question.question = question_value

            for idx, checked in enumerate(molecular_checks):
                case.molecular_findings[idx].human_verified = checked
            for idx, checked in enumerate(treatment_checks):
                case.treatments[idx].human_verified = checked

            unresolved_provenance = len(package.provenance_failures) > 0
            unreviewed_molecular = any(not x for x in molecular_checks) if molecular_checks else False
            unreviewed_treatments = any(not x for x in treatment_checks) if treatment_checks else False

            if unresolved_provenance or unreviewed_molecular or unreviewed_treatments:
                st.warning(
                    "The case was saved, but one or more provenance or verification items remain unresolved. "
                    "Downstream clinical recommendation remains blocked."
                )

            st.session_state.reviewed_case = case
            st.session_state.result = run_workflow(case)
            st.success("Reviewed case stored. Review Data Quality, Routing & Agents, Tumor Board Brief, and Audit.")

        with st.expander("View raw structured extraction"):
            st.json(package.raw_extraction)

    if direct_case is not None:
        st.session_state.reviewed_case = direct_case
        st.session_state.result = run_workflow(direct_case)
        st.success("Structured synthetic workflow completed. Review the remaining tabs.")

result = st.session_state.result

with tabs[1]:
    st.subheader("Data quality")
    if not result:
        st.info("Extract and review a case, or run the structured synthetic example first.")
    else:
        c = result["case"]
        left, right = st.columns(2)
        with left:
            st.markdown("#### Conflicts")
            if c.conflicts:
                for item in c.conflicts:
                    st.warning(f"{item.severity.upper()}: {item.field} • {item.value_a} vs {item.value_b}")
            else:
                st.success("No stored conflicts.")
        with right:
            st.markdown("#### Missing decision-relevant information")
            if c.missing_items:
                for item in c.missing_items:
                    st.warning(f"{item.importance.upper()}: {item.field} • {item.reason}")
            else:
                st.success("No missing items detected by current structural checks.")

        st.markdown("#### Key facts and provenance")
        key_facts = [c.diagnosis, c.disease_state]
        if c.performance_status is not None:
            key_facts.append(c.performance_status)
        for fact in key_facts:
            with st.expander(f"{fact.field}: {fact.value}"):
                st.write(f"Status: {fact.status.value}")
                st.write(f"Extraction confidence: {fact.confidence if fact.confidence is not None else 'not reported'}")
                st.write(f"Human verified: {'Yes' if fact.human_verified else 'No'}")
                for prov in fact.provenance:
                    st.write(f"Source: {prov.document_id} • segments {', '.join(prov.source_segment_ids) or 'n/a'}")
                    st.write(f"Exact provenance verified: {'Yes' if prov.source_verified else 'No'}")
                    if prov.source_excerpt:
                        st.code(prov.source_excerpt, language="text")

        st.markdown("#### Canonical case")
        st.json(c.model_dump(mode="json"))

with tabs[2]:
    st.subheader("Routing & agent analysis")
    if not result:
        st.info("Run a case first.")
    else:
        routing = result["routing"]
        if routing:
            c1, c2 = st.columns(2)
            c1.metric("Question class", routing.question_type.replace("_", " ").title())
            c2.metric("Complexity", routing.complexity.replace("_", " ").title())
            st.markdown("**Agents selected:** " + " · ".join(a.replace("_", " ").title() for a in routing.selected_agents))
            st.markdown("**Routing rationale:**")
            for r in routing.rationale:
                st.write(f"• {r}")

        st.markdown("### Specialist outputs")
        for agent_id, output in result["specialist_outputs"].items():
            with st.expander(agent_id.replace("_", " ").title(), expanded=False):
                st.write(output.summary)
                for warning in output.warnings:
                    st.warning(warning)
                if output.findings:
                    st.json(output.findings)

with tabs[3]:
    st.subheader("Tumor Board Brief")
    if not result:
        st.info("Run a case first.")
    else:
        final = result["final_decision"]
        st.markdown(f"### Decision state: `{final.decision_state.upper()}`")
        st.markdown(f"**Decision-support strength:** {final.decision_support_strength.upper()}")
        if final.abstention_reason:
            st.error(final.abstention_reason)
        if final.major_uncertainties:
            st.markdown("#### Major uncertainties")
            for u in final.major_uncertainties:
                st.write(f"• {u}")
        st.markdown("#### Board discussion priorities")
        for p in final.discussion_priorities:
            st.write(f"• {p}")
        st.markdown("#### Red-team findings")
        for f in result["red_team_findings"]:
            st.warning(f"{f.severity.upper()} • {f.category}: {f.issue}")
        st.caption(
            "Clinical recommendation remains intentionally disabled until authoritative evidence connectors, verification, and validation benchmarks are active."
        )

with tabs[4]:
    st.subheader("Audit")
    if not result:
        st.info("Run a case first.")
    else:
        st.dataframe(result["audit_events"], use_container_width=True, hide_index=True)
        package = st.session_state.extraction_package
        if package is not None:
            st.markdown("#### Extraction audit")
            st.write(f"Provenance anchors: {package.provenance_total}")
            st.write(f"Exact provenance verified: {package.provenance_verified}")
            st.write(f"Provenance verification rate: {package.provenance_rate * 100:.1f}%")
            if package.provenance_failures:
                st.write("Failed provenance items: " + ", ".join(package.provenance_failures))
