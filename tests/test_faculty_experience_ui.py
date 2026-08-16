from pathlib import Path

from services.governed_chat import answer_governed_question


def test_faculty_landing_page_replaces_auto_redirect():
    text = Path("app/main.py").read_text(encoding="utf-8")
    assert "render_final_overview" in text
    assert "switch_page" not in text


def test_workspace_contains_governed_chat_and_thirty_second_view():
    text = Path("app/pages/00_Clinical_Workspace.py").read_text(encoding="utf-8")
    assert "render_thirty_second_view(result, case)" in text
    # The final integration patch replaces the older keyword-router chat with
    # the governed reasoning UI.
    assert "Ram Paragi · rparag@lsuhsc.edu" in text


def test_chat_abstains_outside_governed_record():
    response = answer_governed_question("What is the weather?", {}, object())
    assert response["status"] == "Unable to answer from current case evidence"
    assert response["evidence_used"] == []


def test_expandable_affordance_is_explicit():
    text = Path("app/faculty_ui.py").read_text(encoding="utf-8")
    assert "View details" in text
    assert "Synthetic demonstration case" in text
