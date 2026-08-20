from __future__ import annotations

from fastapi.testclient import TestClient
from pathlib import Path
import pytest

from api.main import create_app
from schemas.case import CancerTumorBoardCase
from services.deployment_profile import allowed_case_types, validate_case_boundary


def _controlled_case() -> CancerTumorBoardCase:
    source = {
        "document_id": "PATH-001",
        "source_section": "Synthetic demonstration",
        "source_excerpt": "Controlled synthetic source text.",
        "source_segment_ids": ["path-diagnosis"],
        "source_verified": True,
        "author_role": "synthetic_fixture",
    }
    return CancerTumorBoardCase.model_validate(
        {
            "case_id": "TBI-AML-042",
            "case_type": "synthetic",
            "care_site": "Synthetic Research Center",
            "diagnosis": {
                "field": "diagnosis",
                "value": "acute myeloid leukemia",
                "provenance": [source],
            },
            "disease_state": {
                "field": "disease_state",
                "value": "first relapse",
                "provenance": [{**source, "document_id": "NOTE-001"}],
            },
            "clinical_question": {
                "question_type": "treatment_selection",
                "question": "Which strategies should be discussed for this synthetic case?",
            },
            "source_documents": ["PATH-001", "NOTE-001", "LAB-001"],
        }
    )


def test_synthetic_profile_accepts_only_the_controlled_fixture(monkeypatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "synthetic_evaluation")
    case = _controlled_case()

    assert allowed_case_types() == {"synthetic"}
    validate_case_boundary(case)

    with pytest.raises(ValueError, match="bundled AML teaching case"):
        validate_case_boundary(case.model_copy(update={"case_id": "UNCONTROLLED-001"}))


def test_synthetic_profile_rejects_deidentified_cases(monkeypatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "synthetic_evaluation")
    case = _controlled_case().model_copy(update={"case_type": "deidentified_research"})

    with pytest.raises(ValueError, match="only the controlled synthetic AML"):
        validate_case_boundary(case)


def test_synthetic_profile_disables_document_upload(monkeypatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_PROFILE", "synthetic_evaluation")
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/cases/extract",
            json={
                "case_id": "TBI-AML-042",
                "case_type": "synthetic",
                "document": {
                    "document_id": "PATH-001",
                    "filename": "synthetic.txt",
                    "content_base64": "U3ludGhldGljIHRleHQu",
                },
            },
        )

    assert response.status_code == 403
    assert "Document upload is disabled" in response.json()["detail"]


def test_default_render_blueprint_has_no_paid_resources() -> None:
    blueprint = (Path(__file__).resolve().parents[1] / "render.yaml").read_text()

    assert "plan: free" in blueprint
    assert "databases:" not in blueprint
    assert "DEPLOYMENT_PROFILE" in blueprint
    assert "synthetic_evaluation" in blueprint
