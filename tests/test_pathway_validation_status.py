from __future__ import annotations

from services.oncology_programs import PROGRAMS
from services.pathway_validation import COMMON_CORE_QUALIFICATION, get_pathway_validation_status


def test_common_core_qualification_record_is_machine_readable():
    assert COMMON_CORE_QUALIFICATION["result"] == "pass"
    assert COMMON_CORE_QUALIFICATION["qualified_build"] == "b62217a3bc65321193195d782a593e093139d406"
    assert COMMON_CORE_QUALIFICATION["workflow_run_id"] == 31964312857
    assert COMMON_CORE_QUALIFICATION["matrix_executions"] == 210
    assert COMMON_CORE_QUALIFICATION["dedicated_pan_oncology_tests_passed"] == 261
    assert COMMON_CORE_QUALIFICATION["full_regression_tests_passed"] == 555


def test_no_program_is_silently_promoted_to_clinical_validation():
    for program in PROGRAMS:
        status = get_pathway_validation_status(program.program_id)
        assert status.common_core_qualified is True
        assert status.disease_specific_software_qualified is False
        assert status.clinically_validated is False
        assert status.state == "architecture_ready"


def test_unregistered_program_is_not_marked_qualified():
    status = get_pathway_validation_status("not_registered")
    assert status.common_core_qualified is False
    assert status.disease_specific_software_qualified is False
    assert status.clinically_validated is False
