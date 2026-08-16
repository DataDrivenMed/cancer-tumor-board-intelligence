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


COMMON_CORE_QUALIFICATION = {
    "result": "pass",
    "qualified_build": "b62217a3bc65321193195d782a593e093139d406",
    "workflow_run_id": 31964312857,
    "matrix_executions": 210,
    "dedicated_pan_oncology_tests_passed": 261,
    "full_regression_tests_passed": 555,
    "qualification_date": "2026-08-16",
}


@dataclass(frozen=True)
class PathwayValidationStatus:
    program_id: str
    state: ValidationState
    label: str
    common_core_qualified: bool
    disease_specific_software_qualified: bool
    clinically_validated: bool
    note: str


# The shared pan-oncology common core has passed its automated qualification gate.
# Disease-specific management correctness has not yet been independently qualified
# against a disease-specific reference standard, so the program-level state remains
# architecture_ready rather than software_qualified or clinically validated.
PATHWAY_STATUS = {
    program.program_id: PathwayValidationStatus(
        program_id=program.program_id,
        state="architecture_ready",
        label="Architecture ready",
        common_core_qualified=True,
        disease_specific_software_qualified=False,
        clinically_validated=False,
        note=(
            "The shared pan-oncology core passed the automated common-core qualification gate. "
            "Disease-specific software qualification and independent clinical validation remain required before this pathway can receive a higher validation label."
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
        common_core_qualified=False,
        disease_specific_software_qualified=False,
        clinically_validated=False,
        note="The disease program is not registered for validated oncology decision support.",
    )
