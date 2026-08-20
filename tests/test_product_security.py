from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from api.main import create_app
from services.case_versions import SQLiteCaseVersionStore
from services.deidentification import screen_deidentified_text


def _snapshot(case_id: str) -> dict:
    final_decision = {"decision_state": "abstain"}
    workflow = {
        "case_id": case_id,
        "request_id": f"run-{case_id}",
        "result": {"final_decision": final_decision},
    }
    human = {
        "case_id": case_id,
        "workflow_request_id": workflow["request_id"],
        "system_decision": final_decision,
        "decision_record_id": f"decision-{case_id}",
        "board_decision": {"status": "pending"},
    }
    return {"case": {"case_id": case_id}, "workflow": workflow, "human": human}


def test_oidc_mode_requires_bearer_token_but_keeps_readiness_public(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "oidc")
    with TestClient(create_app()) as client:
        protected = client.get("/api/v1/runtime/status")
        public = client.get("/api/v1/release/readiness")

    assert protected.status_code == 401
    assert protected.headers["WWW-Authenticate"] == "Bearer"
    assert public.status_code == 200


def test_production_readiness_requires_complete_identity_and_operations(monkeypatch) -> None:
    settings = {
        "DEPLOYMENT_ENV": "production",
        "AUTH_MODE": "oidc",
        "OIDC_ISSUER": "https://identity.example.test/",
        "OIDC_AUDIENCE": "https://api.example.test",
        "REQUIRE_HTTPS": "true",
        "CORS_ALLOWED_ORIGINS": "https://app.example.test",
        "TRUSTED_HOSTS": "api.example.test",
        "RATE_LIMITING_MODE": "managed-edge",
        "MONITORING_SINK": "security-operations",
        "BACKUP_POLICY": "daily-tested-restore",
        "DATABASE_URL": "postgresql://example.invalid/product",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)

    with TestClient(create_app(), base_url="https://api.example.test") as client:
        response = client.get("/api/v1/release/readiness")

    assert response.status_code == 200
    assert response.json()["production_research_ready"] is True


def test_real_case_extraction_requires_deidentification_attestation(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "none")
    document = base64.b64encode(b"Diagnosis: acute myeloid leukemia.").decode()
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/cases/extract",
            json={
                "case_id": "DEID-001",
                "case_type": "deidentified_research",
                "document": {"filename": "case.txt", "content_base64": document},
            },
        )

    assert response.status_code == 422
    assert "attestation" in response.text.lower()


def test_identifier_screen_blocks_before_model_extraction(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "none")
    monkeypatch.setenv("MODEL_BASE_URL", "http://model.invalid/v1")
    document = base64.b64encode(
        b"Diagnosis: acute myeloid leukemia. MRN: ABCD-1234. Contact patient@example.com."
    ).decode()
    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/cases/extract",
            json={
                "case_id": "DEID-002",
                "case_type": "deidentified_research",
                "deidentification_attested": True,
                "document": {"filename": "case.txt", "content_base64": document},
            },
        )

    assert response.status_code == 422
    assert "medical_record_number" in response.json()["detail"]
    assert "email" in response.json()["detail"]


def test_identifier_screen_returns_only_masked_context() -> None:
    result = screen_deidentified_text(["MRN: SECRET-1234 and patient@example.com"])

    assert result["status"] == "blocked"
    assert result["original_document_retained"] is False
    assert result["finding_count"] == 2
    assert all("SECRET-1234" not in item["masked_context"] for item in result["findings"])
    assert all("patient@example.com" not in item["masked_context"] for item in result["findings"])


def test_case_store_isolates_organizations_and_lists_latest_case(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "tenant-isolation.sqlite3")
    snapshot = _snapshot("CASE-001")
    saved_a, _ = store.save_version(
        case=snapshot["case"],
        raw_extraction=None,
        workflow=snapshot["workflow"],
        evidence_review={},
        human_decision=snapshot["human"],
        parent_version_id=None,
        trigger="initial_board_review",
        change_summary="Organization A case.",
        organization_id="org-a",
        created_by="user-a",
    )

    assert store.get_version(saved_a["version_id"], organization_id="org-a") is not None
    assert store.get_version(saved_a["version_id"], organization_id="org-b") is None
    assert len(store.list_cases(organization_id="org-a")) == 1
    assert store.list_cases(organization_id="org-b") == []
