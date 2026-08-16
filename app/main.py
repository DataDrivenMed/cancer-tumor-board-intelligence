from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.extraction_v25 import extract_case_v25
from app.ui import apply_design_system, badge, hero
from orchestration.workflow import run_workflow
from schemas.case import CancerTumorBoardCase, InformationType, Provenance
from services.document_parser import parse_text, parse_upload
from services.model_gateway import ModelGatewayError


st.set_page_config(
    page_title="Tumor Board Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_design_system()


VIEWS = [
    "Overview",
    "1. Start case",
    "2. Review case",
    "3. Tumor Board Brief",
    "Evidence & audit",
]


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def as_text(value: Any) -> str:
    if value is None:
        return "Not represented"
    if hasattr(value, "value"):
        value = value.value
    return str(value)


def go_to(view: str) -> None:
    st.session_state.nav_choice = view


def add_human_correction(fact, old_value, new_value):
    if fact is None:
        return
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


def render_item(item) -> None:
    refs = list(val(item, "source_refs", []) or [])
    limits = list(val(item, "limitations", []) or [])
    label = as_text(val(item, "label", "Item"))
    value = as_text(val(item, "value", ""))
    epistemic = val(item, "epistemic_label", None)
    st.markdown(f"**{label}**")
    st.write(value)
    if epistemic:
        st.caption(f"Epistemic label: {epistemic}")
    if refs:
        st.caption("Source trace: " + " · ".join(str(x) for x in refs))
    for limitation in limits:
        st.caption(f"Limit: {limitation}")


def render_brief(brief) -> None:
    if brief is None:
        st.info("No structured tumor-board brief is available for this workflow state.")
        return

    status = as_text(val(brief, "status", "unknown")).upper()
    decision_state = as_text(val(brief, "decision_state", "unknown")).replace("_", " ").upper()
    strength = as_text(val(brief, "decision_support_strength", "unknown")).upper()
    source_count = int(val(brief, "source_trace_count", 0) or 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Brief status", status)
    c2.metric("Decision state", decision_state)
    c3.metric("Support strength", strength)
    c4.metric("Source traces", source_count)

    warnings = list(val(brief, "critical_warnings", []) or [])
    for warning in warnings:
        st.error(warning)

    sections = list(val(brief, "sections", []) or [])
    priority_ids = [
        "patient_snapshot",
        "clinical_question",
        "decision_critical_information",
        "management_strategy",
        "guideline_analysis",
        "molecular_translational",
        "clinical_trials",
        "safety",
        "red_team",
        "uncertainty",
        "what_changes_recommendation",
    ]
    section_map = {val(section, "section_id", ""): section for section in sections}

    for section_id in priority_ids:
        section = section_map.get(section_id)
        if section is None:
            continue
        title = as_text(val(section, "title", section_id))
        items = list(val(section, "items", []) or [])
        note = val(section, "section_note", None)
        st.markdown(f"### {title}")
        if note:
            st.caption(str(note))
        if not items:
            st.caption("No items represented in this section.")
            continue
        if section_id in {"patient_snapshot", "decision_critical_information"}:
            cols = st.columns(min(3, len(items)))
            for index, item in enumerate(items):
                with cols[index % len(cols)]:
                    with st.container(border=True):
                        render_item(item)
        else:
            for item in items:
                with st.container(border=True):
                    render_item(item)

    remaining = [s for s in sections if val(s, "section_id", "") not in priority_ids]
    if remaining:
        with st.expander("Additional case detail and audit trace"):
            for section in remaining:
                st.markdown(f"#### {as_text(val(section, 'title', 'Section'))}")
                for item in list(val(section, "items", []) or []):
                    render_item(item)


for key, default in {
    "result": None,
    "extraction_package": None,
    "parsed_document": None,
    "reviewed_case": None,
    "nav_choice": "Overview",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


with st.sidebar:
    st.markdown("### Tumor Board Intelligence")
    st.caption("Research v1.0")
    st.markdown(
        badge("Qualified synthetic integration", "ok")
        + badge("Human review required", "warn"),
        unsafe_allow_html=True,
    )
    st.divider()
    st.radio("Clinician workflow", VIEWS, key="nav_choice")
    st.divider()
    st.page_link("pages/00_Architecture_Anatomy.py", label="System anatomy")
    st.caption("Architecture, evidence boundaries, safety invariants, and validation anatomy.")
    st.divider()
    st.caption("Public deployment: synthetic or fully de-identified material only. Do not enter PHI.")


view = st.session_state.nav_choice
result = st.session_state.result
package = st.session_state.extraction_package


if view == "Overview":
    hero(
        "Evidence-grounded intelligence for multidisciplinary tumor boards",
        "A guided workflow turns tumor-board source material into a structured, provenance-aware case, challenges the evidence stack, and produces an auditable decision-support brief. The system is designed to stop or abstain when information or evidence is insufficient.",
        eyebrow="Clinician workspace · Research v1.0",
    )

    st.markdown(
        badge("36/36 frozen whole-system qualification", "ok")
        + badge("0 observed safety-stop violations", "ok")
        + badge("Synthetic/de-identified only", "warn"),
        unsafe_allow_html=True,
    )

    st.markdown("## One workflow, four actions")
    st.write(
        "The multi-agent system runs behind the interface. A clinician does not select agents or operate validation components individually."
    )

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("01", "Enter the case", "Paste a de-identified narrative, upload a document, or use the built-in synthetic example."),
        ("02", "Verify the case", "Confirm decision-critical facts and source provenance before downstream analysis."),
        ("03", "Run analysis", "Routing, specialist evidence channels, verification, Red Team, and consensus execute behind the scenes."),
        ("04", "Review the brief", "Read the board-ready management discussion, evidence, uncertainty, safety, trials, and challenges."),
    ]
    for col, (num, title, copy) in zip([c1, c2, c3, c4], cards):
        with col:
            st.markdown(
                f'<div class="ctb-card"><div class="ctb-kicker">Step {num}</div><h3>{title}</h3><p>{copy}</p></div>',
                unsafe_allow_html=True,
            )

    st.markdown("## What happens behind the interface")
    st.markdown(
        """
        <div class="ctb-strip">
          <span class="ctb-chip">Case input</span><span class="ctb-chip">Extraction</span>
          <span class="ctb-chip">Provenance</span><span class="ctb-chip">Integrity gates</span>
          <span class="ctb-chip">Missing information</span><span class="ctb-chip">Routing</span>
          <span class="ctb-chip">Specialist evidence</span><span class="ctb-chip">Verification</span>
          <span class="ctb-chip">Clinical Red Team</span><span class="ctb-chip">Consensus</span>
          <span class="ctb-chip">Tumor Board Brief</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.35, .65])
    with left:
        st.markdown("### Safety by separation of responsibilities")
        st.write(
            "Patient facts, evidence retrieval, evidence verification, molecular interpretation, trial matching, safety analysis, adversarial challenge, and consensus are separate bounded functions. A retrieved paper is not automatically a recommendation; a molecular signal is not automatically actionability; a possible trial match is not patient eligibility."
        )
        st.page_link("pages/00_Architecture_Anatomy.py", label="Open the detailed system anatomy")
    with right:
        st.markdown(
            '<div class="ctb-card accent"><div class="ctb-kicker">Validation boundary</div><div class="ctb-number">36/36</div><h3>Strict synthetic executions</h3><p>Zero observed safety-stop violations in the frozen controlled whole-system benchmark. This is software qualification, not clinical validation.</p></div>',
            unsafe_allow_html=True,
        )

    st.warning(
        "This public research deployment is for synthetic or fully de-identified data only. It is not a production PHI environment and is not an autonomous treatment system."
    )
    st.button("Start a case", type="primary", on_click=go_to, args=("1. Start case",))


elif view == "1. Start case":
    hero(
        "Start a tumor-board case",
        "Choose one input method. The system will either load the built-in synthetic case or structure a narrative/document under the frozen v2.5 extraction contract.",
        eyebrow="Step 1 of 4",
    )

    st.info("Public research deployment: use synthetic or fully de-identified material only. Do not enter PHI.")

    mode = st.segmented_control(
        "Input method",
        options=["Synthetic example", "Synthetic narrative", "Paste narrative", "Upload document"],
        default="Synthetic example",
    )

    parsed_document = None
    direct_case = None

    if mode == "Synthetic example":
        sample_path = PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.json"
        sample_data = json.loads(sample_path.read_text(encoding="utf-8"))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Disease", "AML")
        c2.metric("Disease state", "Relapsed")
        c3.metric("Molecular", "FLT3-ITD")
        c4.metric("ECOG", "1")
        st.caption("Best path for exploring the clinician interface without invoking extraction inference.")
        if st.button("Run synthetic example", type="primary", key="run_structured"):
            direct_case = CancerTumorBoardCase.model_validate(sample_data)

    elif mode == "Synthetic narrative":
        narrative_path = PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.txt"
        narrative = narrative_path.read_text(encoding="utf-8")
        st.text_area("Source narrative", value=narrative, height=280, disabled=True)
        parsed_document = parse_text(narrative, document_id="SYN-DOC-NARRATIVE", filename="syn_aml_001.txt")

    elif mode == "Paste narrative":
        narrative = st.text_area(
            "Tumor-board narrative",
            height=300,
            placeholder="Paste a synthetic or fully de-identified case narrative. Include the clinical question when possible.",
        )
        if narrative.strip():
            parsed_document = parse_text(narrative, document_id="DOC-PASTED", filename="pasted_case.txt")

    else:
        uploaded = st.file_uploader(
            "Upload source document",
            type=["pdf", "docx", "txt", "md"],
            help="Synthetic or fully de-identified material only in this public deployment.",
        )
        if uploaded:
            try:
                parsed_document = parse_upload(uploaded.name, uploaded.getvalue(), document_id="DOC-UPLOAD")
            except Exception as exc:
                st.error(f"Could not parse file safely: {exc}")

    if parsed_document is not None:
        st.session_state.parsed_document = parsed_document
        c1, c2 = st.columns(2)
        c1.metric("Source segments", len(parsed_document.segments))
        c2.metric("Document type", parsed_document.document_type.upper())
        with st.expander("Inspect source segments"):
            st.code(parsed_document.numbered_text(), language="text")

        model_token = get_secret("MODEL_AUTH_TOKEN") or get_secret("HF_TOKEN")
        model_name = get_secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
        model_base_url = get_secret("MODEL_BASE_URL")
        reasoning_effort = get_secret("MODEL_REASONING_EFFORT", "high") or "high"
        if model_base_url:
            os.environ["MODEL_BASE_URL"] = model_base_url

        if not model_token and not model_base_url:
            st.info("The extraction endpoint is not configured for this deployment. The structured synthetic example remains available.")
        else:
            st.caption(f"Extraction model: {model_name} · reasoning effort: {reasoning_effort} · extraction contract: v2.5")
            if st.button("Extract and verify case", type="primary", key="extract_case"):
                try:
                    with st.spinner("Structuring the case and verifying exact source provenance..."):
                        package = extract_case_v25(
                            document=parsed_document,
                            api_key=model_token or "local-no-auth",
                            model=model_name,
                            case_id="EXTRACTED-001",
                        )
                    st.session_state.extraction_package = package
                    st.session_state.reviewed_case = None
                    st.session_state.result = None
                    st.success("Extraction complete. The case is ready for clinician review.")
                except ModelGatewayError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Extraction failed safely: {exc}")

    if direct_case is not None:
        st.session_state.extraction_package = None
        st.session_state.reviewed_case = direct_case
        st.session_state.result = run_workflow(direct_case)
        st.success("Synthetic workflow completed successfully.")

    if st.session_state.extraction_package is not None:
        st.button("Continue to case review", type="primary", on_click=go_to, args=("2. Review case",))
    elif st.session_state.result is not None:
        st.button("Open Tumor Board Brief", type="primary", on_click=go_to, args=("3. Tumor Board Brief",))


elif view == "2. Review case":
    hero(
        "Verify what the system understood",
        "Human review occurs before the case is allowed to proceed through the downstream intelligence stack. Confirm decision-critical facts, molecular findings, treatment history, and provenance.",
        eyebrow="Step 2 of 4",
    )

    package = st.session_state.extraction_package
    if package is None:
        if st.session_state.reviewed_case is not None:
            st.info("The current case was loaded from the structured synthetic example, so narrative extraction review was not required.")
            st.button("Open Tumor Board Brief", type="primary", on_click=go_to, args=("3. Tumor Board Brief",))
        else:
            st.info("No extracted case is waiting for review. Start a case first.")
            st.button("Start a case", type="primary", on_click=go_to, args=("1. Start case",))
    else:
        total = package.provenance_total
        verified = package.provenance_verified
        rate = package.provenance_rate * 100 if total else 0.0
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Provenance anchors", total)
        q2.metric("Exact verified", verified)
        q3.metric("Verification rate", f"{rate:.1f}%")
        q4.metric("Failures", len(package.provenance_failures))

        if package.provenance_failures:
            st.error("One or more extracted claims failed exact provenance verification. Do not treat them as verified facts until reviewed.")
        else:
            st.success("All provenance-bearing extracted items passed the exact source verification gate.")

        for warning in package.warnings:
            st.warning(warning)

        case = package.case
        with st.form("clinical_review_form"):
            st.markdown("### Decision-critical facts")
            r1, r2, r3 = st.columns(3)
            diagnosis_value = r1.text_input("Diagnosis", value=str(case.diagnosis.value or ""))
            disease_state_value = r2.text_input("Disease state", value=str(case.disease_state.value or ""))
            ecog_value = r3.text_input("Performance status", value=str(case.performance_status.value or "") if case.performance_status else "")
            question_value = st.text_area("Clinical question", value=case.clinical_question.question, height=90)

            st.markdown("### Molecular findings")
            molecular_checks = []
            for idx, item in enumerate(case.molecular_findings):
                molecular_checks.append(
                    st.checkbox(
                        f"I verified: {item.gene} {item.alteration_type or ''}".strip(),
                        key=f"mol_verify_{idx}",
                    )
                )
            if not case.molecular_findings:
                st.caption("No molecular findings were extracted. This is not equivalent to a negative molecular result.")

            st.markdown("### Treatment history")
            treatment_checks = []
            for idx, item in enumerate(case.treatments):
                treatment_checks.append(
                    st.checkbox(
                        f"I verified treatment episode: {item.regimen}",
                        key=f"tx_verify_{idx}",
                    )
                )
            if not case.treatments:
                st.caption("No treatment episodes were extracted.")

            confirm = st.form_submit_button("Confirm case and run analysis", type="primary")

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
            st.session_state.reviewed_case = case
            st.session_state.result = run_workflow(case, raw_extraction=package.raw_extraction)
            st.success("Analysis complete. The board brief is ready.")

        with st.expander("Inspect structured extraction and provenance"):
            st.json(package.raw_extraction)

        if st.session_state.result is not None:
            st.button("Open Tumor Board Brief", type="primary", on_click=go_to, args=("3. Tumor Board Brief",))


elif view == "3. Tumor Board Brief":
    hero(
        "Tumor Board Intelligence Brief",
        "The clinician-facing synthesis. Management candidates are rendered only when the upstream consensus contract permits them; uncertainty, missing information, Red Team challenges, and evidence boundaries remain visible.",
        eyebrow="Steps 3 and 4 · Analyze and review",
    )

    if not result:
        st.info("No completed case analysis is available yet.")
        st.button("Start a case", type="primary", on_click=go_to, args=("1. Start case",))
    else:
        render_brief(result.get("tumor_board_brief"))
        st.divider()
        st.button("Inspect evidence and audit trail", on_click=go_to, args=("Evidence & audit",))


elif view == "Evidence & audit":
    hero(
        "Evidence and audit trail",
        "A single expert view for provenance, specialist outputs, Red Team findings, consensus, and workflow events. This is progressive disclosure for clinicians, reviewers, researchers, and validation teams.",
        eyebrow="Expert review",
    )

    if not result:
        st.info("Run a case first.")
        st.button("Start a case", type="primary", on_click=go_to, args=("1. Start case",))
    else:
        routing = result.get("routing")
        if routing:
            c1, c2, c3 = st.columns(3)
            c1.metric("Question class", routing.question_type.replace("_", " ").title())
            c2.metric("Complexity", routing.complexity.replace("_", " ").title())
            c3.metric("Selected agents", len(routing.selected_agents))
            st.markdown(
                "<div class='ctb-strip'>"
                + "".join(f"<span class='ctb-chip'>{a.replace('_',' ').title()}</span>" for a in routing.selected_agents)
                + "</div>",
                unsafe_allow_html=True,
            )

        st.markdown("## Independent challenge and consensus")
        red = result.get("red_team_report")
        consensus = result.get("consensus_report")
        if red:
            c1, c2 = st.columns(2)
            c1.metric("Red Team", as_text(red.disposition).upper())
            c2.metric("Blocking findings", red.blocking_count)
            for finding in red.findings:
                level = finding.severity.value.upper()
                if finding.recommendation_blocking:
                    st.error(f"{level} · {finding.code}: {finding.issue}")
                else:
                    st.warning(f"{level} · {finding.code}: {finding.issue}")
        if consensus:
            st.write(
                f"**Consensus:** {consensus.decision_state.replace('_', ' ').upper()} · support strength {consensus.decision_support_strength.upper()}"
            )
            st.caption(consensus.summary)

        st.markdown("## Specialist evidence channels")
        for agent_id, output in result.get("specialist_outputs", {}).items():
            status = as_text(val(output, "status", "unknown"))
            with st.expander(f"{agent_id.replace('_', ' ').title()} · {status.upper()}"):
                summary = val(output, "summary", None)
                if summary:
                    st.write(summary)
                for warning in list(val(output, "warnings", []) or []):
                    st.warning(warning)
                if hasattr(output, "model_dump"):
                    st.json(output.model_dump(mode="json"))
                elif isinstance(output, dict):
                    st.json(output)

        st.markdown("## Workflow audit")
        events = result.get("audit_events", [])
        if events:
            st.dataframe(events, use_container_width=True, hide_index=True)

        with st.expander("Structured Red Team report"):
            st.json(red.model_dump(mode="json") if red and hasattr(red, "model_dump") else red or {})
        with st.expander("Structured Consensus report"):
            st.json(consensus.model_dump(mode="json") if consensus and hasattr(consensus, "model_dump") else consensus or {})
        with st.expander("Structured final brief"):
            brief = result.get("tumor_board_brief")
            st.json(brief.model_dump(mode="json") if brief and hasattr(brief, "model_dump") else brief or {})

        package = st.session_state.extraction_package
        if package is not None:
            st.markdown("## Extraction v2.5 audit")
            c1, c2, c3 = st.columns(3)
            c1.metric("Provenance anchors", package.provenance_total)
            c2.metric("Exact verified", package.provenance_verified)
            c3.metric("Duplicate treatments removed", package.duplicate_treatments_removed)
            if package.provenance_failures:
                st.error("Failed provenance items: " + ", ".join(package.provenance_failures))


st.divider()
st.caption(
    "Research prototype. Controlled synthetic software qualification does not establish clinical validation, real-world efficacy, or autonomous clinical safety. Human multidisciplinary review remains required."
)
