from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

import pytest

from agents.guideline import GuidelineAgent
from orchestration.context import WorkflowContext
from orchestration import workflow
from orchestration.workflow import run_workflow
from schemas.case import CancerTumorBoardCase
from services.eln_aml_guidance import public_eln_aml_store


ROOT = Path(__file__).resolve().parents[1]


def _case(case_id: str) -> CancerTumorBoardCase:
    payload = json.loads(
        (ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8")
    )
    payload["case_id"] = case_id
    return CancerTumorBoardCase.model_validate(payload)


def _context(*, governed_guidance: bool) -> WorkflowContext:
    registry = dict(workflow.AGENT_REGISTRY)
    registry["guideline"] = (
        GuidelineAgent(public_eln_aml_store()) if governed_guidance else GuidelineAgent()
    )
    return WorkflowContext(
        agent_registry=registry,
        runtime_status={"test_context": "governed" if governed_guidance else "empty"},
    )


def test_context_mappings_are_read_only_copies() -> None:
    original = {"guideline": GuidelineAgent()}
    context = WorkflowContext(agent_registry=original, runtime_status={"ready": True})

    original["extra"] = GuidelineAgent()
    assert "extra" not in context.agent_registry
    with pytest.raises(TypeError):
        context.agent_registry["extra"] = GuidelineAgent()  # type: ignore[index]


def test_concurrent_workflows_keep_request_registries_isolated() -> None:
    governed = _context(governed_guidance=True)
    empty = _context(governed_guidance=False)

    def execute(index: int) -> tuple[bool, str]:
        context = governed if index % 2 == 0 else empty
        result = run_workflow(_case(f"CONTEXT-{index:03d}"), context=context)
        report = result["specialist_outputs"]["guideline"]
        return report.can_support_guideline_claim, context.runtime_status["test_context"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(execute, range(24)))

    for index, (can_support, context_name) in enumerate(outcomes):
        if index % 2 == 0:
            assert can_support is True
            assert context_name == "governed"
        else:
            assert can_support is False
            assert context_name == "empty"


def test_clinician_workspace_passes_context_through_workflow_and_chat() -> None:
    workspace = (ROOT / "app" / "pages" / "00_Clinical_Workspace.py").read_text(
        encoding="utf-8"
    )
    runtime = (ROOT / "services" / "runtime_agents.py").read_text(encoding="utf-8")

    assert "st.session_state.workflow_context = build_workflow_context(" in workspace
    assert "context=st.session_state.workflow_context" in workspace
    assert "workflow.AGENT_REGISTRY = registry" not in runtime
