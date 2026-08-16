from __future__ import annotations

import streamlit as st

from qualification.system_protocol_v1 import (
    ACCEPTANCE_POLICY,
    FROZEN_SUITE_FINGERPRINT,
    PLANNED_EXECUTIONS,
    QUALIFICATION_SCOPE,
    SAFETY_STOP_RULES,
)
from services.system_qualification_v1 import run_full_study


st.set_page_config(page_title="Whole-System Qualification v1.0.0", layout="wide")
st.title("Whole-System Qualification v1.0.0")
st.caption("Frozen controlled synthetic qualification of post-extraction integration.")

st.warning(
    "Research prototype only. This study is software qualification, not clinical validation, patient-outcome validation, "
    "or evidence that the system is safe for autonomous clinical use."
)

st.subheader("Frozen protocol")
c1, c2 = st.columns(2)
c1.metric("Planned executions", PLANNED_EXECUTIONS)
c2.metric("Frozen fingerprint", FROZEN_SUITE_FINGERPRINT[:16] + "…")
st.code(FROZEN_SUITE_FINGERPRINT)
st.write(QUALIFICATION_SCOPE)

with st.expander("Acceptance policy"):
    for label, rule in ACCEPTANCE_POLICY.items():
        st.write(f"**{label}:** {rule}")

with st.expander("Prespecified safety-stop rules"):
    for rule in SAFETY_STOP_RULES:
        st.write(f"- {rule}")

st.divider()
st.subheader("Run frozen study")
st.info(
    "This qualification is deterministic and uses synthetic frozen specialist outputs. It does not use PHI, external APIs, "
    "or model calls. The historical Extraction v2.5 qualification remains separate and unchanged."
)

if st.button("Run 36-execution frozen qualification", type="primary"):
    study = run_full_study()
    st.session_state["whole_system_qualification_v1"] = study

study = st.session_state.get("whole_system_qualification_v1")
if study:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Disposition", study["formal_disposition"])
    c2.metric("Strict passes", f"{study['strict_passes']}/{study['completed_executions']}")
    c3.metric("Safety-stop violations", study["safety_stop_violation_count"])
    c4.metric("Repeat cases", ", ".join(f"{k}:{v}/3" for k, v in study["repeat_passes"].items()))

    if study["formal_disposition"] == "GREEN":
        st.success("GREEN: frozen controlled synthetic post-extraction integration gate passed.")
    elif study["formal_disposition"] == "AMBER":
        st.warning("AMBER: advancement requires review before any freeze or release claim.")
    else:
        st.error("RED: does not pass the advancement gate.")

    st.subheader("Baseline case results")
    st.dataframe(
        [
            {
                "case": item["case_id"],
                "attack class": item["attack_class"],
                "strict pass": item["strict_pass"],
                "red team": item["red_team_disposition"],
                "consensus": item["consensus_state"],
                "safe to render": item["safe_to_render"],
                "safety violations": ", ".join(item["safety_violations"]),
            }
            for item in study["baseline"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Raw qualification record"):
        st.json(study)

    st.caption(
        "Correct interpretation: strict case-execution performance in a frozen controlled synthetic software benchmark. "
        "Do not describe this as 100% clinically accurate, clinically validated, or error-free."
    )
