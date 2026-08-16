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


def _runtime_error(channel: str, exc: Exception) -> dict[str, Any]:
    """Return a non-secret runtime status for a channel that failed to initialize."""
    return {
        "channel": channel,
        "configured": False,
        "loaded": False,
        "ready": False,
        "fail_closed": True,
        "error_type": type(exc).__name__,
        "error": str(exc)[:500],
    }


def _pubmed_agent() -> tuple[LiteratureAgent, dict[str, Any]]:
    try:
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
    except Exception as exc:
        status = _runtime_error("pubmed", exc)
        status["enabled"] = True
        return LiteratureAgent(), status


def _trials_agent() -> tuple[ClinicalTrialsAgent, dict[str, Any]]:
    try:
        enabled = bool_env("ENABLE_LIVE_CLINICALTRIALS", default=True)
        if not enabled:
            return ClinicalTrialsAgent(), {"enabled": False, "ready": False, "reason": "disabled"}
        return ClinicalTrialsAgent(ClinicalTrialsClient()), {"enabled": True, "ready": True}
    except Exception as exc:
        status = _runtime_error("clinical_trials", exc)
        status["enabled"] = True
        return ClinicalTrialsAgent(), status


def _safe_status(channel: str, loader, empty_store):
    try:
        return loader()
    except Exception as exc:
        return empty_store(), EvidenceConfigStatus(
            channel=channel,
            configured=False,
            loaded=False,
            error=f"{type(exc).__name__}: {str(exc)[:500]}",
            configuration_origin="runtime_fail_closed",
        )


def _governed_stores():
    """Load governed stores independently so one channel cannot crash the product."""
    try:
        from services import guideline_sources
        guideline_store, guideline_status = _safe_status(
            "guideline",
            guideline_sources._load_production_guideline_store,
            GuidelineEvidenceStore,
        )
    except Exception as exc:
        guideline_store = GuidelineEvidenceStore()
        guideline_status = EvidenceConfigStatus(
            channel="guideline",
            configured=False,
            loaded=False,
            error=f"{type(exc).__name__}: {str(exc)[:500]}",
            configuration_origin="runtime_import_fail_closed",
        )

    try:
        from services import molecular_sources
        molecular_store, molecular_status = _safe_status(
            "molecular",
            molecular_sources._load_production_molecular_store,
            MolecularEvidenceStore,
        )
    except Exception as exc:
        molecular_store = MolecularEvidenceStore()
        molecular_status = EvidenceConfigStatus(
            channel="molecular",
            configured=False,
            loaded=False,
            error=f"{type(exc).__name__}: {str(exc)[:500]}",
            configuration_origin="runtime_import_fail_closed",
        )

    try:
        from services import safety_sources
        safety_store, safety_status = _safe_status(
            "safety",
            safety_sources._load_production_safety_store,
            SafetyEvidenceStore,
        )
    except Exception as exc:
        safety_store = SafetyEvidenceStore()
        safety_status = EvidenceConfigStatus(
            channel="safety",
            configured=False,
            loaded=False,
            error=f"{type(exc).__name__}: {str(exc)[:500]}",
            configuration_origin="runtime_import_fail_closed",
        )

    try:
        from services import translational_sources
        translational_store, translational_status = _safe_status(
            "translational",
            translational_sources._load_production_translational_store,
            TranslationalEvidenceStore,
        )
    except Exception as exc:
        translational_store = TranslationalEvidenceStore()
        translational_status = EvidenceConfigStatus(
            channel="translational",
            configured=False,
            loaded=False,
            error=f"{type(exc).__name__}: {str(exc)[:500]}",
            configuration_origin="runtime_import_fail_closed",
        )

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


def resolve_product_guideline_store() -> tuple[GuidelineEvidenceStore, EvidenceConfigStatus]:
    """Resolve the guideline store for the clinician product.

    An explicitly configured governed deployment package always takes precedence.
    If none is configured, the product falls back to its deliberately narrow bundled
    open-access ELN AML consensus record. The core backend itself remains fail-closed
    by default, which preserves existing backend and historical regression semantics.
    """
    try:
        from services import guideline_sources
        configured_store, configured_status = guideline_sources._load_production_guideline_store()
        if configured_status.loaded and configured_store.sources and configured_store.recommendations:
            return configured_store, configured_status
    except Exception:
        pass

    from services.eln_aml_guidance import public_eln_aml_store

    store = public_eln_aml_store()
    return store, EvidenceConfigStatus(
        channel="guideline",
        configured=True,
        loaded=True,
        source_count=len(store.sources),
        record_count=len(store.recommendations),
        configuration_origin="bundled_public_eln_2022",
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

    registry: dict[str, Any] = {
        "guideline": GuidelineAgent(guideline_store),
        "molecular": MolecularInterpretationAgent(molecular_store, production_mode=True),
        "translational": TranslationalBiologyAgent(translational_store, production_mode=True),
        "literature": literature,
        "clinical_trials": trials,
    }

    try:
        registry["safety"] = CandidateAwareSafetyAgent(
            safety_store,
            guideline_store,
            production_mode=True,
        )
        safety_runtime_status: dict[str, Any] = safety_status.__dict__
    except Exception as exc:
        registry["safety"] = SafetyAgent()
        safety_runtime_status = _runtime_error("safety", exc)

    status = {
        "guideline": guideline_status.__dict__,
        "molecular": molecular_status.__dict__,
        "translational": translational_status.__dict__,
        "safety": safety_runtime_status,
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
        "runtime": {
            "ready": True,
            "fail_closed": True,
        },
    }
    return registry, status


def _fallback_registry() -> dict[str, Any]:
    """Return a fully fail-closed registry that is safe to install after startup failure."""
    return {
        "guideline": GuidelineAgent(),
        "molecular": MolecularInterpretationAgent(production_mode=True),
        "translational": TranslationalBiologyAgent(production_mode=True),
        "literature": LiteratureAgent(),
        "clinical_trials": ClinicalTrialsAgent(),
        "safety": SafetyAgent(production_mode=True),
    }


def configure_workflow_runtime(
    *,
    guideline_store_override: GuidelineEvidenceStore | None = None,
    molecular_store_override: MolecularEvidenceStore | None = None,
    safety_store_override: SafetyEvidenceStore | None = None,
    translational_store_override: TranslationalEvidenceStore | None = None,
) -> dict[str, Any]:
    """Install deployment/session-specific agents into the existing core orchestrator.

    Startup must never convert an optional evidence-source problem into a full product
    outage. If initialization fails unexpectedly, a fail-closed empty registry is
    installed and the non-secret error type/message is returned in runtime status.
    """
    from orchestration import workflow

    try:
        registry, status = build_runtime_registry(
            guideline_store_override=guideline_store_override,
            molecular_store_override=molecular_store_override,
            safety_store_override=safety_store_override,
            translational_store_override=translational_store_override,
        )
    except Exception as exc:
        registry = _fallback_registry()
        status = {
            "runtime": {
                "ready": False,
                "fail_closed": True,
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            },
            "guideline": {"ready": False, "fail_closed": True},
            "molecular": {"ready": False, "fail_closed": True},
            "translational": {"ready": False, "fail_closed": True},
            "safety": {"ready": False, "fail_closed": True},
            "pubmed": {"enabled": False, "ready": False},
            "clinical_trials": {"enabled": False, "ready": False},
            "civic": {
                "enabled": True,
                "ready": bool(os.getenv("CIVIC_API_KEY", "").strip()),
                "api_key_configured": bool(os.getenv("CIVIC_API_KEY", "").strip()),
            },
            "openfda": {
                "enabled": True,
                "ready": bool(os.getenv("OPENFDA_API_KEY", "").strip()),
                "api_key_configured": bool(os.getenv("OPENFDA_API_KEY", "").strip()),
            },
        }

    workflow.AGENT_REGISTRY = registry
    return status
