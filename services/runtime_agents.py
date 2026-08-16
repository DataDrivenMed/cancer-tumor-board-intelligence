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
from services.guideline_sources import PRODUCTION_GUIDELINE_STATUS, PRODUCTION_GUIDELINE_STORE
from services.molecular_sources import PRODUCTION_MOLECULAR_STATUS, PRODUCTION_MOLECULAR_STORE
from services.production_evidence_config import bool_env
from services.pubmed_client import PubMedClient
from services.safety_sources import PRODUCTION_SAFETY_STATUS, PRODUCTION_SAFETY_STORE
from services.translational_sources import PRODUCTION_TRANSLATIONAL_STATUS, PRODUCTION_TRANSLATIONAL_STORE


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


def build_runtime_registry() -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the clinical specialist registry from governed stores and public clients.

    No secret values are returned in status. Evidence stores remain empty and fail
    closed when deployment configuration is absent or invalid.
    """
    literature, pubmed_status = _pubmed_agent()
    trials, trials_status = _trials_agent()

    registry = {
        "guideline": GuidelineAgent(PRODUCTION_GUIDELINE_STORE),
        "molecular": MolecularInterpretationAgent(PRODUCTION_MOLECULAR_STORE, production_mode=True),
        "translational": TranslationalBiologyAgent(PRODUCTION_TRANSLATIONAL_STORE, production_mode=True),
        "literature": literature,
        "clinical_trials": trials,
        "safety": SafetyAgent(PRODUCTION_SAFETY_STORE, production_mode=True),
    }
    status = {
        "guideline": PRODUCTION_GUIDELINE_STATUS.__dict__,
        "molecular": PRODUCTION_MOLECULAR_STATUS.__dict__,
        "translational": PRODUCTION_TRANSLATIONAL_STATUS.__dict__,
        "safety": PRODUCTION_SAFETY_STATUS.__dict__,
        "pubmed": pubmed_status,
        "clinical_trials": trials_status,
    }
    return registry, status


def configure_workflow_runtime() -> dict[str, Any]:
    """Install the deployment-specific registry into the existing orchestrator.

    Kept outside orchestration.workflow to preserve the qualified core workflow file
    while allowing product deployments to opt into current public retrieval and
    authorized evidence packages.
    """
    from orchestration import workflow

    registry, status = build_runtime_registry()
    workflow.AGENT_REGISTRY = registry
    return status
