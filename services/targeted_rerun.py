from __future__ import annotations

from typing import Any

from schemas.clinical_trials import ClinicalTrialsReport
from schemas.guideline import GuidelineReport
from schemas.literature import LiteratureReport
from schemas.molecular import MolecularReport
from schemas.safety import SafetyReport
from schemas.translational import TranslationalReport


REPORT_MODELS = {
    "guideline": GuidelineReport,
    "molecular": MolecularReport,
    "translational": TranslationalReport,
    "literature": LiteratureReport,
    "clinical_trials": ClinicalTrialsReport,
    "safety": SafetyReport,
}


def rehydrate_specialist_outputs(value: Any) -> dict[str, Any]:
    """Validate saved JSON before an unaffected specialist output can be reused."""

    if not isinstance(value, dict):
        return {}
    outputs: dict[str, Any] = {}
    for agent_id, payload in value.items():
        model = REPORT_MODELS.get(agent_id)
        if model is None or not isinstance(payload, dict):
            continue
        outputs[agent_id] = model.model_validate(payload)
    return outputs
