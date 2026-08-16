from __future__ import annotations

from agents.clinical_trials import ClinicalTrialsAgent
from agents.literature import LiteratureAgent
from services.runtime_agents import build_runtime_registry


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
