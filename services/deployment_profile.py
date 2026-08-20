from __future__ import annotations

import os

from schemas.case import CancerTumorBoardCase


SYNTHETIC_EVALUATION = "synthetic_evaluation"
FULL_PRODUCT = "full_product"
SUPPORTED_PROFILES = {SYNTHETIC_EVALUATION, FULL_PRODUCT}


def deployment_profile() -> str:
    """Return the explicit product boundary for this deployment."""

    profile = os.getenv("DEPLOYMENT_PROFILE", FULL_PRODUCT).strip().lower()
    return profile if profile in SUPPORTED_PROFILES else FULL_PRODUCT


def synthetic_evaluation_enabled() -> bool:
    return deployment_profile() == SYNTHETIC_EVALUATION


def allowed_case_types() -> set[str]:
    if synthetic_evaluation_enabled():
        return {"synthetic"}
    return {"synthetic", "deidentified_research"}


def validate_case_boundary(case: CancerTumorBoardCase) -> None:
    """Reject case material outside the active deployment boundary."""

    if case.case_type not in allowed_case_types():
        if synthetic_evaluation_enabled():
            raise ValueError(
                "This evaluation accepts only the controlled synthetic AML teaching case. "
                "Document upload and de-identified clinical cases are disabled."
            )
        raise ValueError(
            "This research API accepts only synthetic or fully de-identified research cases."
        )

    if not synthetic_evaluation_enabled():
        return

    if case.case_id != "TBI-AML-042" or case.care_site != "Synthetic Research Center":
        raise ValueError("The synthetic evaluation accepts only the bundled AML teaching case.")
    if set(case.source_documents) != {"PATH-001", "NOTE-001", "LAB-001"}:
        raise ValueError("The synthetic evaluation case must retain its controlled source packet.")

    provenance = []
    for fact in [
        case.diagnosis,
        case.disease_state,
        case.stage,
        case.performance_status,
        *case.pathology,
        *case.imaging,
        *case.labs,
        *case.comorbidities,
        *case.toxicities,
        *case.transplant_cellular_therapy,
        *case.current_medications,
    ]:
        if fact is not None:
            provenance.extend(fact.provenance)
    for finding in case.molecular_findings:
        provenance.extend(finding.provenance)
    for treatment in case.treatments:
        provenance.extend(treatment.provenance)

    if not provenance or any(item.author_role != "synthetic_fixture" for item in provenance):
        raise ValueError("The synthetic evaluation case must retain controlled fixture provenance.")
