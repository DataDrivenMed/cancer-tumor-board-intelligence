from __future__ import annotations

import os
from typing import Any

from agents.clinical_trials import ClinicalTrialsAgent
from agents.guideline import GuidelineAgent
from agents.literature import LiteratureAgent
from agents.molecular import MolecularInterpretationAgent
from agents.safety import SafetyAgent
from agents.translational import TranslationalBiologyAgent
from services.clinicaltrials_client import ClinicalTrialsClient
from services.production_evidence_config import bool_env
from services.pubmed_client import PubMedClient


def _pubmed_agent() -> tuple[LiteratureAgent, dict[str, Any]]:
    email = os.getenv("PUBMED_EMAIL", "").strip()
    enabled = bool_env("ENABLE_LIVE_PUBMED", default=bool(email))
    if not enabled:
        return LiteratureAgent(), {"enabled": False, "ready": False, "reason": "disabled"}
    if not email:
        return LiteratureAgent(), {
            "enabled": True,
            "ready": False,
            "reason": "PUBMED_EMAIL is required by the NCBI E-utilities client",
        }
    api_key = os.getenv("NCBI_API_KEY", "").strip() or None
    return LiteratureAgent(PubMedClient(email=email, api_key=api_key)), {
        "enabled": True,
        "ready": True,
        "api_key_configured": bool(api_key),
    }


def _trials_agent() -> tuple[ClinicalTrialsAgent, dict[str, Any]]:
    enabled = bool_env("ENABLE_LIVE_CLINICALTRIALS", default=True)
    if not enabled:
        return ClinicalTrialsAgent(), {"enabled": False, "ready": False, "reason": "disabled"}
    return ClinicalTrialsAgent(ClinicalTrialsClient()), {"enabled": True, "ready": True}


def _governed_stores():
    """Load governed stores at runtime after deployment secrets/env are available."""
    from services import guideline_sources, molecular_sources, safety_sources, translational_sources

    guideline_store, guideline_status = guideline_sources._load_production_guideline_store()
    molecular_store, molecular_status = molecular_sources._load_production_molecular_store()
    safety_store, safety_status = safety_sources._load_production_safety_store()
    translational_store, translational_status = translational_sources._load_production_translational_store()
    return (
        guideline_store,
        guideline_status,
        molecular_store,
        molecular_status,
        safety_store,
        safety_status,
        translational_store,
        translational_status,
    )


def build_runtime_registry() -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the specialist registry from governed stores and official public clients.

    This function intentionally reloads evidence configuration on every product
    initialization so Streamlit Secrets copied into environment variables immediately
    before this call are honored. No secret values are returned in status.
    """
    literature, pubmed_status = _pubmed_agent()
    trials, trials_status = _trials_agent()
    (
        guideline_store,
        guideline_status,
        molecular_store,
        molecular_status,
        safety_store,
        safety_status,
        translational_store,
        translational_status,
    ) = _governed_stores()

    registry = {
        "guideline": GuidelineAgent(guideline_store),
        "molecular": MolecularInterpretationAgent(molecular_store, production_mode=True),
        "translational": TranslationalBiologyAgent(translational_store, production_mode=True),
        "literature": literature,
        "clinical_trials": trials,
        "safety": SafetyAgent(safety_store, production_mode=True),
    }
    status = {
        "guideline": guideline_status.__dict__,
        "molecular": molecular_status.__dict__,
        "translational": translational_status.__dict__,
        "safety": safety_status.__dict__,
        "pubmed": pubmed_status,
        "clinical_trials": trials_status,
    }
    return registry, status


def configure_workflow_runtime() -> dict[str, Any]:
    """Install deployment-specific agents into the existing core orchestrator.

    Kept outside `orchestration.workflow` so product integration does not rewrite the
    qualified core workflow file. The safety gates and consensus logic are unchanged.
    """
    from orchestration import workflow

    registry, status = build_runtime_registry()
    workflow.AGENT_REGISTRY = registry
    return status
