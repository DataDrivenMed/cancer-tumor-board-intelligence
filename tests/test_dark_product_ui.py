from pathlib import Path


def test_shared_midnight_editorial_theme_is_wired():
    theme = Path("app/xai_theme.py").read_text(encoding="utf-8")
    faculty = Path("app/faculty_ui.py").read_text(encoding="utf-8")
    workspace = Path("app/pages/00_Clinical_Workspace.py").read_text(encoding="utf-8")
    overview = Path("app/overview_ui.py").read_text(encoding="utf-8")
    assert "--x-canvas:#12100f" in theme
    assert "--x-primary:#d9915f" in theme
    assert "--x-thinking:#d9915f" in theme
    assert "Midnight Editorial" in theme
    assert "inject_xai_theme()" in faculty
    assert "inject_xai_theme()" in workspace
    assert "inject_xai_theme()" in overview


def test_architecture_uses_warm_non_scroll_system_map():
    page = Path("app/pages/03_Architecture.py").read_text(encoding="utf-8")
    renderer = Path("app/architecture_warm_ui.py").read_text(encoding="utf-8")
    assert "architecture_warm_ui" in page
    assert "--canvas:#f7f7f4" in renderer
    assert "How to read this architecture" in renderer
    assert "Case understanding and safety" in renderer
    assert "Parallel specialist agents" in renderer
    assert "Challenge and consensus" in renderer
    assert "Tumor Board output and human decision support" in renderer
    assert "Click for details" in renderer
    assert "const DETAILS=" in renderer
    assert "NODES" in renderer
    assert "scrolling=False" in renderer
    assert "Open larger architecture view" not in renderer
    assert "overflow-x:auto" not in renderer


def test_overview_explains_agents_and_guided_use():
    text = Path("app/overview_ui.py").read_text(encoding="utf-8")
    assert "What is an AI agent in this system?" in text
    assert "Five steps from case intake to tumor-board brief." in text
    assert "What remains with the clinicians?" in text
    assert "Try the synthetic demonstration" in text
    assert "Ask Tumor Board" in text
