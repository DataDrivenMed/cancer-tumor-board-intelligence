from pathlib import Path


def test_architecture_uses_interactive_html_asset():
    ui = Path("app/architecture_ui.py").read_text(encoding="utf-8")
    asset = Path("app/assets/architecture_interactive.html").read_text(encoding="utf-8")
    assert "components.html" in ui
    assert "architecture_interactive.html" in ui
    assert "Hover over any node" in ui
    assert "data-id=\"intake\"" in asset
    assert "Case Intake /" in asset
    assert "Purpose:" in asset
    assert "Safety boundary:" in asset
    assert "Handoff:" in asset
    assert "pathology · imaging" not in asset


def test_old_static_card_graph_is_not_rendered():
    ui = Path("app/architecture_ui.py").read_text(encoding="utf-8")
    start = ui.index("def render_architecture_graph")
    end = ui.index("def render_agent_explorer")
    block = ui[start:end]
    assert "_node_html(\"intake\")" not in block
    assert "Parallel bounded specialist work" not in block
