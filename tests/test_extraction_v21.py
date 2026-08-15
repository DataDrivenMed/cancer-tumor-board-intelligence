from agents.extraction_v21 import EXTRACTION_V21_VERSION, ExtractionPackageV21, _treatment_status
from schemas.case import TreatmentStatus


def test_v21_module_imports_and_version_is_explicit():
    assert EXTRACTION_V21_VERSION == "2.1.0"
    assert "raw_model_output" in ExtractionPackageV21.__dataclass_fields__
    assert "normalized_extraction" in ExtractionPackageV21.__dataclass_fields__
    assert "normalization_events" in ExtractionPackageV21.__dataclass_fields__


def test_treatment_status_preserves_planned_vs_started():
    assert _treatment_status({"treatment_status": "planned"}) == TreatmentStatus.PLANNED
    assert _treatment_status({"source_excerpt": "she started therapy yesterday"}) == TreatmentStatus.STARTED
    assert _treatment_status({"source_excerpt": "therapy is recommended but has not yet started"}) == TreatmentStatus.PLANNED
