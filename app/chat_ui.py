from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from services.governed_chat import answer_governed_question


def _txt(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if hasattr(value, "value"):
        value = value.value
    text = str(value).strip()
    return text or default


def chat_css() -> None:
    st.markdown(
        """
<style>
.tb-chat-shell{background:linear-gradient(180deg,#effbfc,#f8fcfd);border:1px solid #a9d8df;border-radius:18px;padding:12px;box-shadow:0 10px 28px rgba(26,92,105,.08)}
.tb-chat-head{background:linear-gradient(145deg,#155a70,#1d7183);color:#fff;border-radius:14px;padding:17px 18px}.tb-chat-head strong{font-size:21px;line-height:1.2;display:block}.tb-chat-head span{font-size:13px;color:#d9f0f4;line-height:1.5;display:block;margin-top:6px}
.tb-chat-note{font-size:12px;line-height:1.5;color:#3c6570;background:#e9f6f8;border:1px solid #c7e5ea;border-radius:10px;padding:10px 11px;margin:8px 0 11px}
.tb-turn{margin:12px 0}.tb-user{font-size:13px;font-weight:750;color:#183b56;margin:0 0 5px}.tb-answer{background:#fff;border:1px solid #d5e5e9;border-radius:13px;padding:13px 14px}.tb-status{font-size:12px;font-weight:800;color:#155a70;text-transform:uppercase;letter-spacing:.04em}.tb-answer-text{font-size:14px;line-height:1.62;color:#263f52;margin:7px 0 0;white-space:pre-wrap}.tb-block-title{font-size:11px;font-weight:800;color:#476474;margin-top:10px;text-transform:uppercase;letter-spacing:.05em}.tb-chip{display:inline-flex;padding:4px 8px;border-radius:999px;background:#edf4f7;color:#315b68;border:1px solid #d6e5e9;font-size:10px;font-weight:700;margin:4px 4px 0 0}.tb-limit{font-size:12px;line-height:1.45;color:#7c5a14;background:#fff8e8;border:1px solid #efdba8;border-radius:9px;padding:8px 9px;margin-top:6px}.tb-change{font-size:12px;line-height:1.45;color:#43586a;margin-top:4px}
</style>
""",
        unsafe_allow_html=True,
    )


def _history_for_model(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for row in rows[-6:]:
        history.append({"role": "user", "content": _txt(row.get("question"))})
        history.append({"role": "assistant", "content": _txt(row.get("answer"))})
    return history


def _render_answer(row: dict[str, Any]) -> None:
    agents = row.get("agents_consulted", []) or []
    evidence = row.get("evidence_used", []) or []
    limitations = row.get("limitations", []) or []
    changes = row.get("what_could_change", []) or []
    st.markdown(f'<div class="tb-turn"><div class="tb-user">You: {escape(_txt(row.get("question")))}</div><div class="tb-answer"><div class="tb-status">{escape(_txt(row.get("status"), "Case-grounded synthesis"))}</div><div class="tb-answer-text">{escape(_txt(row.get("answer")))}</div>', unsafe_allow_html=True)
    if agents:
        st.markdown('<div class="tb-block-title">Agents consulted</div>' + ''.join(f'<span class="tb-chip">{escape(_txt(x))}</span>' for x in agents), unsafe_allow_html=True)
    if evidence:
        st.markdown('<div class="tb-block-title">Evidence used</div>' + ''.join(f'<span class="tb-chip">{escape(_txt(x))}</span>' for x in evidence), unsafe_allow_html=True)
    if limitations:
        st.markdown('<div class="tb-block-title">Limitations</div>' + ''.join(f'<div class="tb-limit">{escape(_txt(x))}</div>' for x in limitations[:6]), unsafe_allow_html=True)
    if changes:
        st.markdown('<div class="tb-block-title">What could change the answer</div>' + ''.join(f'<div class="tb-change">• {escape(_txt(x))}</div>' for x in changes[:6]), unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)


def render_governed_chat(result: dict[str, Any], case: Any, *, key_prefix: str = "brief") -> None:
    chat_css()
    st.markdown('<div class="tb-chat-shell"><div class="tb-chat-head"><strong>Ask Tumor Board</strong><span>Case-grounded reasoning across the structured case, approved evidence, specialist agents, Challenge Review, consensus, and final brief. The chat may invoke configured specialist agents on demand, but it does not create a parallel treatment recommendation from unrestricted model memory.</span></div><div class="tb-chat-note"><strong>How to use it:</strong> ask natural follow-up questions such as “What is the best-supported treatment strategy and why?”, “Which trials matched and why?”, “What evidence is weakest?”, or “What would change this decision?”</div></div>', unsafe_allow_html=True)

    hist_key = f"{key_prefix}_governed_chat"
    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    prompts = [
        "Summarize for tumor board",
        "What is the best-supported treatment strategy and why?",
        "Which clinical trials matched and why?",
        "What is missing or uncertain?",
        "What did the Clinical Red Team challenge?",
        "What could change the decision?",
    ]
    if not st.session_state[hist_key]:
        cols = st.columns(2, gap="small")
        for i, prompt in enumerate(prompts):
            with cols[i % 2]:
                if st.button(prompt, key=f"{key_prefix}_smart_prompt_{i}", use_container_width=True):
                    response = answer_governed_question(prompt, result, case, history=[])
                    response["question"] = prompt
                    st.session_state[hist_key].append(response)
                    st.rerun()

    for row in st.session_state[hist_key][-6:]:
        _render_answer(row)

    question = st.chat_input("Ask a case-grounded tumor board question", key=f"{key_prefix}_smart_chat_input")
    if question:
        history = _history_for_model(st.session_state[hist_key])
        with st.spinner("Consulting the governed case and relevant specialist agents..."):
            response = answer_governed_question(question, result, case, history=history)
        response["question"] = question
        st.session_state[hist_key].append(response)
        st.rerun()
