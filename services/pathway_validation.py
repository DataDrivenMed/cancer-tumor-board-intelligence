from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from services.oncology_programs import PROGRAMS


ValidationState = Literal[
    "architecture_ready",
    "software_qualified",
    "clinically_validated_silent",
    "clinical_release",
]


@dataclass(frozen=True)
class PathwayValidationStatus:
    program_id: str
    state: ValidationState
    label: str
    note: str


# Pan-oncology architecture expansion is post-qualification work. Until a disease
# family completes the protocol in docs/PAN_ONCOLOGY_VALIDATION_PROTOCOL.md, the UI
# must not represent it as software-qualified or clinically validated.
PATHWAY_STATUS = {
    program.program_id: PathwayValidationStatus(
        program_id=program.program_id,
        state="architecture_ready",
        label="Architecture ready",
        note=(
            "This tumor-board program is supported by the shared pan-oncology workflow, "
            "but disease-specific software qualification and clinical validation are not yet complete."
        ),
    )
    for program in PROGRAMS
}


def get_pathway_validation_status(program_id: str | None) -> PathwayValidationStatus:
    if program_id in PATHWAY_STATUS:
        return PATHWAY_STATUS[program_id]
    return PathwayValidationStatus(
        program_id=str(program_id or "unclassified"),
        state="architecture_ready",
        label="Unclassified pathway",
        note="The disease program is not registered for validated oncology decision support.",
    )
