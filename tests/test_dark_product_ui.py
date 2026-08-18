from pathlib import Path


def test_shared_warm_editorial_theme_is_wired():
    theme = Path("app/xai_theme.py").read_text(encoding="utf-8")
    faculty = Path("app/faculty_ui.py").read_text(encoding="utf-8")
    workspace = Path("app/pages/00_Clinical_Workspace.py").read_text(encoding="utf-8")
    overview = Path("app/overview_ui.py").read_text(encoding="utf-8")
    assert "--x-canvas:#f7f7f4" in theme
    assert "--x-primary:#f54e00" in theme
    assert "--x-thinking:#dfa88f" in theme
    assert "WHAT TO DO HERE" in theme
    assert "inject_xai_theme()" in faculty
    assert "inject_xai_theme()" in workspace
    assert "inject_xai_theme()" in overview


def test_architecture_uses_warm_interactive_renderer():
    page = Path("app/pages/03_Architecture.py").read_text(encoding="utf-8")
    renderer = Path("app/architecture_warm_ui.py").read_text(encoding="utf-8")
    assert "architecture_warm_ui" in page
    assert "--canvas:#f7f7f4" in renderer
    assert "hover over a node" in renderer
    assert "Click or tap a node" in renderer
    assert "const DETAILS=" in renderer
    assert "HANDOFFS" in renderer
    assert "NODES" in renderer


def test_overview_explains_agents_and_guided_use():
    text = Path("app/overview_ui.py").read_text(encoding="utf-8")
    assert "What is an AI agent in this system?" in text
    assert "Five steps from case intake to tumor-board brief." in text
    assert "What remains with the clinicians?" in text
    assert "Try the synthetic demonstration" in text
    assert "Ask Tumor Board" in text
