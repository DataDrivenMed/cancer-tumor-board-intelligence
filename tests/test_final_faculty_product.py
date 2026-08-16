from pathlib import Path

from services.governed_chat import answer_governed_question


def test_main_uses_final_overview():
    text = Path("app/main.py").read_text(encoding="utf-8")
    assert "render_final_overview" in text
    assert "Pan-Oncology Tumor Board Intelligence" in Path("app/overview_ui.py").read_text(encoding="utf-8")


def test_architecture_page_and_agent_explorer_exist():
    text = Path("app/architecture_ui.py").read_text(encoding="utf-8")
    assert "Agent Explorer" in text
    assert "Agent-to-agent handoffs and criteria" in text
    assert "Clinical Red Team" in text
    assert "Consensus Engine" in text
    assert "Click an agent" in text
    assert Path("app/pages/03_Architecture.py").exists()


def test_workspace_uses_governed_chat_ui():
    text = Path("app/pages/00_Clinical_Workspace.py").read_text(encoding="utf-8")
    assert "from app.chat_ui import render_governed_chat" in text
    assert "render_governed_chat(" in text
    assert "render_case_chat(" not in text


def test_governed_chat_fallback_treatment_question_does_not_invent():
    class Fact:
        value = "Acute myeloid leukemia"
    class Q:
        question = "What is the best treatment?"
    class Case:
        diagnosis = Fact()
        disease_state = Fact()
        stage = None
        molecular_findings = []
        clinical_question = Q()
    out = answer_governed_question("what is the best treatment", {}, Case())
    assert out["status"] in {"Evidence incomplete", "Unable to answer from current case evidence"}
    assert "cannot establish" in out["answer"].lower() or "does not establish" in out["answer"].lower()


def test_governed_chat_trial_question_never_invents_trial():
    class Fact:
        value = "Acute myeloid leukemia"
    class Q:
        question = "Relevant trials"
    class Case:
        diagnosis = Fact()
        disease_state = Fact()
        stage = None
        molecular_findings = []
        clinical_question = Q()
    out = answer_governed_question("relevant clinical trials", {}, Case())
    assert "clinical-trial" in out["answer"].lower() or "trial" in out["answer"].lower()
    assert not any(str(x).startswith("NCT") for x in out.get("evidence_used", []))
