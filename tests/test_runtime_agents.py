from __future__ import annotations

from agents.clinical_trials import ClinicalTrialsAgent
from agents.literature import LiteratureAgent
from orchestration import workflow
from services import runtime_agents
from services.runtime_agents import build_runtime_registry, build_workflow_context


def test_runtime_registry_enables_clinicaltrials_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_LIVE_CLINICALTRIALS", raising=False)
    monkeypatch.delenv("PUBMED_EMAIL", raising=False)
    monkeypatch.delenv("ENABLE_LIVE_PUBMED", raising=False)
    registry, status = build_runtime_registry()
    assert isinstance(registry["clinical_trials"], ClinicalTrialsAgent)
    assert registry["clinical_trials"].client is not None
    assert status["clinical_trials"]["ready"] is True
    assert isinstance(registry["literature"], LiteratureAgent)
    assert registry["literature"].client is None
    assert status["pubmed"]["ready"] is False


def test_pubmed_requires_contact_email_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_PUBMED", "true")
    monkeypatch.delenv("PUBMED_EMAIL", raising=False)
    registry, status = build_runtime_registry()
    assert registry["literature"].client is None
    assert status["pubmed"]["enabled"] is True
    assert status["pubmed"]["ready"] is False
    assert "PUBMED_EMAIL" in status["pubmed"]["reason"]


def test_pubmed_client_is_configured_from_email(monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_PUBMED", "true")
    monkeypatch.setenv("PUBMED_EMAIL", "research@example.org")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    registry, status = build_runtime_registry()
    assert registry["literature"].client is not None
    assert status["pubmed"]["ready"] is True
    assert status["pubmed"]["api_key_configured"] is False


def test_clinicaltrials_can_be_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_LIVE_CLINICALTRIALS", "false")
    registry, status = build_runtime_registry()
    assert registry["clinical_trials"].client is None
    assert status["clinical_trials"]["ready"] is False


def test_workflow_context_fails_closed_instead_of_crashing(monkeypatch):
    def broken_registry(**kwargs):
        raise TypeError("simulated runtime constructor mismatch")

    monkeypatch.setattr(runtime_agents, "build_runtime_registry", broken_registry)
    original_registry = workflow.AGENT_REGISTRY
    context = build_workflow_context()
    status = context.runtime_status

    assert status["runtime"]["ready"] is False
    assert status["runtime"]["fail_closed"] is True
    assert status["runtime"]["error_type"] == "TypeError"
    assert "simulated runtime constructor mismatch" in status["runtime"]["error"]
    assert set(context.agent_registry) == {
        "guideline",
        "molecular",
        "translational",
        "literature",
        "clinical_trials",
        "safety",
    }
    assert workflow.AGENT_REGISTRY is original_registry
