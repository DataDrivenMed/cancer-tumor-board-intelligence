from __future__ import annotations

import os
from typing import Any

from agents.clinical_trials import ClinicalTrialsAgent
from agents.guideline import GuidelineAgent, GuidelineEvidenceStore
from agents.literature import LiteratureAgent
from agents.molecular import MolecularInterpretationAgent
from agents.safety import SafetyAgent
from agents.translational import TranslationalBiologyAgent
from schemas.molecular import MolecularEvidenceStore
from schemas.safety import SafetyEvidenceStore
from schemas.translational import TranslationalEvidenceStore
from services.clinicaltrials_client import ClinicalTrialsClient
from services.production_evidence_config import EvidenceConfigStatus, bool_env
from services.pubmed_client import PubMedClient


class CandidateAwareSafetyAgent:
    """Run the existing Safety Agent against represented and guideline-candidate therapies.

    Therapy concepts are taken from structured ``therapy_terms`` on verified guidance
    matches. No therapy name is guessed from free-text recommendation prose.
    """

    agent_id = "safety"
    agent_version = "1.1.0"

    def __init__(
        self,
        safety_store: SafetyEvidenceStore,
        guideline_store: GuidelineEvidenceStore,
        *,
        production_mode: bool = True,
    ) -> None:
        self.safety_agent = SafetyAgent(safety_store, production_mode=production_mode)
        self.guideline_agent = GuidelineAgent(guideline_store)

    def run(self, case):
        guideline_report = self.guideline_agent.run(case)
        therapy_terms: list[str] = []
        if guideline_report.can_support_guideline_claim:
            for match in guideline_report.matched_guidance:
                therapy_terms.extend(match.therapy_terms)
        therapy_terms = list(dict.fromkeys(term for term in therapy_terms if term))
        return self.safety_agent.run(case, candidate_therapy_terms=therapy_terms)


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


def _override_status(channel: str, store: Any) -> EvidenceConfigStatus:
    records = list(getattr(store, "records", []) or [])
    sources = list(getattr(store, "sources", []) or [])
    recommendations = list(getattr(store, "recommendations", []) or [])
    return EvidenceConfigStatus(
        channel=channel,
        configured=True,
        loaded=True,
        source_count=len(sources),
        record_count=len(records) if records else len(recommendations),
        configuration_origin="session_human_attested",
    )


def build_runtime_registry(
    *,
    guideline_store_override: GuidelineEvidenceStore | None = None,
    molecular_store_override: MolecularEvidenceStore | None = None,
    safety_store_override: SafetyEvidenceStore | None = None,
    translational_store_override: TranslationalEvidenceStore | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the specialist registry from governed stores and official public clients.

    Session overrides are used only after explicit human evidence approval in the
    clinician workspace. They do not alter files, environment secrets, or the frozen
    historical qualification artifacts.
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

    if guideline_store_override is not None:
        guideline_store = guideline_store_override
        guideline_status = _override_status("guideline", guideline_store)
    if molecular_store_override is not None:
        molecular_store = molecular_store_override
        molecular_status = _override_status("molecular", molecular_store)
    if safety_store_override is not None:
        safety_store = safety_store_override
        safety_status = _override_status("safety", safety_store)
    if translational_store_override is not None:
        translational_store = translational_store_override
        translational_status = _override_status("translational", translational_store)

    registry = {
        "guideline": GuidelineAgent(guideline_store),
        "molecular": MolecularInterpretationAgent(molecular_store, production_mode=True),
        "translational": TranslationalBiologyAgent(translational_store, production_mode=True),
        "literature": literature,
        "clinical_trials": trials,
        "safety": CandidateAwareSafetyAgent(
            safety_store,
            guideline_store,
            production_mode=True,
        ),
    }
    status = {
        "guideline": guideline_status.__dict__,
        "molecular": molecular_status.__dict__,
        "translational": translational_status.__dict__,
        "safety": safety_status.__dict__,
        "pubmed": pubmed_status,
        "clinical_trials": trials_status,
        "civic": {
            "enabled": True,
            "ready": bool(os.getenv("CIVIC_API_KEY", "").strip()),
            "api_key_configured": bool(os.getenv("CIVIC_API_KEY", "").strip()),
            "note": "Anonymous reads remain possible if no key is configured.",
        },
        "openfda": {
            "enabled": True,
            "ready": bool(os.getenv("OPENFDA_API_KEY", "").strip()),
            "api_key_configured": bool(os.getenv("OPENFDA_API_KEY", "").strip()),
        },
    }
    return registry, status


def configure_workflow_runtime(
    *,
    guideline_store_override: GuidelineEvidenceStore | None = None,
    molecular_store_override: MolecularEvidenceStore | None = None,
    safety_store_override: SafetyEvidenceStore | None = None,
    translational_store_override: TranslationalEvidenceStore | None = None,
) -> dict[str, Any]:
    """Install deployment/session-specific agents into the existing core orchestrator."""
    from orchestration import workflow

    registry, status = build_runtime_registry(
        guideline_store_override=guideline_store_override,
        molecular_store_override=molecular_store_override,
        safety_store_override=safety_store_override,
        translational_store_override=translational_store_override,
    )
    workflow.AGENT_REGISTRY = registry
    return status
