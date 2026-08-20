from __future__ import annotations

import base64
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from orchestration import workflow
from orchestration.context import WorkflowContext
from schemas.case import CancerTumorBoardCase
from services.case_versions import SQLiteCaseVersionStore


ROOT = Path(__file__).resolve().parents[1]
api_main = importlib.import_module("api.main")


def _case_payload() -> dict:
    return json.loads((ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))


def _test_context(*, marker: int = 1) -> WorkflowContext:
    return WorkflowContext(
        agent_registry=dict(workflow.AGENT_REGISTRY),
        runtime_status={"runtime": {"ready": True, "fail_closed": True}, "context_number": marker},
    )


def _client(*, marker: int = 1, version_store: SQLiteCaseVersionStore | None = None) -> TestClient:
    application = api_main.create_app()
    application.dependency_overrides[api_main.get_workflow_context] = lambda: _test_context(
        marker=marker
    )
    if version_store is not None:
        application.dependency_overrides[api_main.get_case_version_store] = lambda: version_store
    return TestClient(application)


def test_health_endpoint_is_small_and_does_not_build_runtime() -> None:
    with _client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "tumor-board-intelligence-api",
        "api_version": "0.6.0",
    }
    assert response.headers["X-Request-ID"]


def test_readiness_endpoint_checks_case_store(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "ready.sqlite3")
    with _client(version_store=store) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_runtime_status_is_non_secret_and_request_scoped() -> None:
    with _client(marker=7) as client:
        response = client.get(
            "/api/v1/runtime/status",
            headers={"X-Request-ID": "phase1-runtime-check"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["request_id"] == "phase1-runtime-check"
    assert body["runtime_status"]["context_number"] == 7
    assert body["research_use_only"] is True
    assert response.headers["X-Request-ID"] == "phase1-runtime-check"


def test_extraction_endpoint_returns_segments_and_auditable_package(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_BASE_URL", "http://local-model.test/v1")
    captured = {}

    def fake_extraction_runner(*, document, api_key, model, case_id):
        captured.update(
            document=document,
            api_key=api_key,
            model=model,
            case_id=case_id,
        )
        case = CancerTumorBoardCase.model_validate(_case_payload())
        return SimpleNamespace(
            case=case,
            extraction_version="2.5.2",
            raw_extraction={"diagnosis": {"value": "acute myeloid leukemia"}},
            provenance_total=3,
            provenance_verified=3,
            provenance_failures=[],
            warnings=[],
            normalization_events=[{"event": "normalization_complete"}],
            diagnostic_certainty="explicit",
        )

    application = api_main.create_app()
    application.dependency_overrides[api_main.get_extraction_runner] = lambda: fake_extraction_runner
    document = "Diagnosis: acute myeloid leukemia.\nDisease state: first relapse."
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/cases/extract",
            json={
                "case_id": "PHASE4-001",
                "case_type": "synthetic",
                "document": {
                    "document_id": "NOTE-001",
                    "filename": "synthetic-note.txt",
                    "content_base64": base64.b64encode(document.encode()).decode(),
                },
            },
            headers={"X-Request-ID": "phase4-extraction-check"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["request_id"] == "phase4-extraction-check"
    assert body["api_version"] == "0.6.0"
    assert body["extraction_version"] == "2.5.2"
    assert body["case"]["case_id"] == "PHASE4-001"
    assert body["source_segments"][0]["segment_id"] == "S0001"
    assert body["source_segments"][0]["text"] == "Diagnosis: acute myeloid leukemia."
    assert body["provenance_verified"] == 3
    assert body["deidentification_screen"]["status"] == "clear"
    assert body["deidentification_screen"]["original_document_retained"] is False
    assert captured["case_id"] == "PHASE4-001"


def test_extraction_endpoint_fails_closed_without_model_configuration(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    with _client() as client:
        response = client.post(
            "/api/v1/cases/extract",
            json={
                "document": {
                    "filename": "synthetic-note.txt",
                    "content_base64": base64.b64encode(b"Synthetic text").decode(),
                }
            },
        )

    assert response.status_code == 503
    assert "Live extraction is not configured" in response.json()["detail"]


def test_guided_evidence_candidates_are_case_bound_and_explicitly_labeled() -> None:
    case = _case_payload()
    with _client() as client:
        response = client.post(
            "/api/v1/evidence/candidates",
            json={"case": case, "mode": "guided_fixture"},
            headers={"X-Request-ID": "phase5-candidate-check"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["request_id"] == "phase5-candidate-check"
    assert body["api_version"] == "0.6.0"
    assert body["case_id"] == case["case_id"]
    assert len(body["candidate_set_id"]) == 64
    assert {candidate["channel"] for candidate in body["candidates"]} == {
        "guideline",
        "molecular",
        "safety",
    }
    assert any(candidate["synthetic"] for candidate in body["candidates"])
    assert {item["channel"] for item in body["downstream_channels"]} == {
        "literature",
        "clinical_trials",
        "translational",
    }


def test_commissioned_workflow_revalidates_and_records_evidence_decisions() -> None:
    case = _case_payload()
    with _client() as client:
        candidate_body = client.post(
            "/api/v1/evidence/candidates",
            json={"case": case, "mode": "guided_fixture"},
        ).json()
        decisions = [
            {
                "candidate_id": candidate["candidate_id"],
                "decision": "approved" if candidate["channel"] == "guideline" else "rejected",
                "reason": "Controlled fixture is not admitted to production reasoning." if candidate["synthetic"] else "",
            }
            for candidate in candidate_body["candidates"]
        ]
        response = client.post(
            "/api/v1/workflows/run-commissioned",
            json={
                "case": case,
                "evidence_commission": {
                    "mode": "guided_fixture",
                    "candidate_set_id": candidate_body["candidate_set_id"],
                    "decisions": decisions,
                    "attested": True,
                },
            },
            headers={"X-Request-ID": "phase5-workflow-check"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["request_id"] == "phase5-workflow-check"
    assert body["evidence_commission"]["candidate_count"] == len(decisions)
    assert body["evidence_commission"]["approved_count"] == 1
    assert body["evidence_commission"]["rejected_count"] == len(decisions) - 1
    assert body["evidence_commission"]["attested"] is True
    assert body["result"]["red_team_report"]["disposition"] in {"clear", "challenged", "blocked"}
    assert body["result"]["consensus_report"]["decision_state"] in {
        "preferred_conditional",
        "multiple_reasonable_options",
        "abstain",
    }
    assert isinstance(body["result"]["consensus_report"]["evidence_channels"], list)
    assert body["result"]["final_decision"]["decision_support_strength"]
    assert body["events"][-1]["source_event"] == "workflow_complete"


def test_commissioned_workflow_rejects_stale_candidate_set() -> None:
    case = _case_payload()
    with _client() as client:
        response = client.post(
            "/api/v1/workflows/run-commissioned",
            json={
                "case": case,
                "evidence_commission": {
                    "mode": "guided_fixture",
                    "candidate_set_id": "0" * 64,
                    "decisions": [],
                    "attested": False,
                },
            },
        )

    assert response.status_code == 409
    assert "candidate set changed" in response.json()["detail"].lower()


def _human_decision_payload() -> dict:
    return {
        "case_id": "SYN-AML-001",
        "case_type": "synthetic",
        "workflow_request_id": "workflow-phase7-001",
        "system_decision": {
            "decision_state": "multiple_reasonable_options",
            "decision_support_strength": "moderate",
            "safe_to_render_decision_support": True,
        },
        "clinician_judgment": {
            "position": "agree",
            "reason_codes": [],
            "rationale": "",
            "attested": True,
        },
        "board_decision": {"status": "pending"},
    }


def test_human_decision_receipt_preserves_system_output_and_pending_board_state() -> None:
    payload = _human_decision_payload()
    original_system_decision = dict(payload["system_decision"])

    with _client() as client:
        response = client.post(
            "/api/v1/decisions/record",
            json=payload,
            headers={"X-Request-ID": "phase7-human-decision"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["request_id"] == "phase7-human-decision"
    assert body["api_version"] == "0.6.0"
    assert body["system_decision"] == original_system_decision
    assert body["board_decision"]["status"] == "pending"
    assert body["persisted"] is False
    assert len(body["decision_record_id"]) == 64
    assert [event["event"] for event in body["decision_events"]] == [
        "system_synthesis_preserved",
        "clinician_judgment_attested",
        "board_decision_pending",
    ]


def test_human_decision_receipt_records_disagreement_and_board_decision() -> None:
    payload = _human_decision_payload()
    payload["clinician_judgment"] = {
        "position": "disagree",
        "reason_codes": ["patient_preference", "safety_concern"],
        "rationale": "The board reviewed context that was outside the system package.",
        "attested": True,
    }
    payload["board_decision"] = {
        "status": "recorded",
        "outcome": "selected_alternative",
        "decision": "Discuss the alternative strategy with the patient.",
        "rationale": "Patient goals and safety considerations changed the balance.",
        "board_date": "2026-08-19",
        "attested": True,
    }

    with _client() as client:
        response = client.post("/api/v1/decisions/record", json=payload)

    body = response.json()
    assert response.status_code == 200
    assert body["clinician_judgment"]["position"] == "disagree"
    assert body["board_decision"]["outcome"] == "selected_alternative"
    assert body["decision_events"][-1]["event"] == "board_decision_attested"


def test_human_decision_rejects_unexplained_disagreement() -> None:
    payload = _human_decision_payload()
    payload["clinician_judgment"] = {
        "position": "disagree",
        "reason_codes": [],
        "rationale": "",
        "attested": True,
    }

    with _client() as client:
        response = client.post("/api/v1/decisions/record", json=payload)

    assert response.status_code == 422
    assert "reason code" in response.text.lower()


def test_human_decision_rejects_unattested_recorded_board_decision() -> None:
    payload = _human_decision_payload()
    payload["board_decision"] = {
        "status": "recorded",
        "outcome": "endorsed_system_supported_option",
        "decision": "Proceed to clinical discussion.",
        "rationale": "The evidence package supports discussion.",
        "attested": False,
    }

    with _client() as client:
        response = client.post("/api/v1/decisions/record", json=payload)

    assert response.status_code == 422
    assert "board attestation" in response.text.lower()


def test_human_decision_rejects_non_research_case() -> None:
    payload = _human_decision_payload()
    payload["case_type"] = "clinical"

    with _client() as client:
        response = client.post("/api/v1/decisions/record", json=payload)

    assert response.status_code == 403
    assert "synthetic or fully de-identified" in response.json()["detail"]


def _governed_snapshot(client: TestClient, case: dict) -> tuple[dict, dict, dict]:
    candidates = client.post(
        "/api/v1/evidence/candidates",
        json={"case": case, "mode": "guided_fixture"},
    ).json()
    decisions = [
        {
            "candidate_id": candidate["candidate_id"],
            "decision": "approved" if candidate["channel"] == "guideline" else "rejected",
            "reason": "Controlled fixture is excluded from governed reasoning." if candidate["synthetic"] else "",
        }
        for candidate in candidates["candidates"]
    ]
    workflow_response = client.post(
        "/api/v1/workflows/run-commissioned",
        json={
            "case": case,
            "evidence_commission": {
                "mode": "guided_fixture",
                "candidate_set_id": candidates["candidate_set_id"],
                "decisions": decisions,
                "attested": True,
            },
        },
    ).json()
    human_response = client.post(
        "/api/v1/decisions/record",
        json={
            "case_id": case["case_id"],
            "case_type": case["case_type"],
            "workflow_request_id": workflow_response["request_id"],
            "system_decision": workflow_response["result"]["final_decision"],
            "clinician_judgment": {
                "position": "agree",
                "reason_codes": [],
                "rationale": "",
                "attested": True,
            },
            "board_decision": {"status": "pending"},
        },
    ).json()
    evidence_review = {
        "mode": "guided_fixture",
        "candidate_set_id": candidates["candidate_set_id"],
        "decisions": decisions,
        "attested": True,
    }
    return workflow_response, evidence_review, human_response


def _save_initial_version(client: TestClient, case: dict) -> dict:
    workflow_response, evidence_review, human_response = _governed_snapshot(client, case)
    response = client.post(
        "/api/v1/cases/versions",
        json={
            "case": case,
            "workflow": workflow_response,
            "evidence_review": evidence_review,
            "human_decision": human_response,
            "trigger": "initial_board_review",
            "change_summary": "Initial governed tumor-board review.",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_case_versions_are_durable_immutable_and_idempotent(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "phase8.sqlite3")
    case = _case_payload()
    with _client(version_store=store) as client:
        first = _save_initial_version(client, case)
        version = first["version"]
        duplicate = client.post(
            "/api/v1/cases/versions",
            json={
                "case": case,
                "workflow": version["workflow"],
                "evidence_review": version["evidence_review"],
                "human_decision": version["human_decision"],
                "trigger": "initial_board_review",
                "change_summary": "Duplicate submission should not create another version.",
            },
        ).json()
        listed = client.get(f"/api/v1/cases/{case['case_id']}/versions").json()
        detail = client.get(
            f"/api/v1/cases/{case['case_id']}/versions/{version['version_id']}"
        ).json()

    assert first["persisted"] is True
    assert first["storage"] == "sqlite"
    assert first["created"] is True
    assert version["version_number"] == 1
    assert duplicate["created"] is False
    assert duplicate["version"]["version_id"] == version["version_id"]
    assert len(listed["versions"]) == 1
    assert detail["version"]["case"]["case_id"] == case["case_id"]
    assert detail["version"]["case"]["diagnosis"]["value"] == case["diagnosis"]["value"]
    assert detail["version"]["human_decision"]["persisted"] is False


def test_update_assessment_maps_changed_fields_to_rerun_scope(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "phase8-assessment.sqlite3")
    case = _case_payload()
    with _client(version_store=store) as client:
        saved = _save_initial_version(client, case)
        updated = dict(case)
        updated["care_site"] = "Synthetic academic cancer center"
        response = client.post(
            "/api/v1/case-version-updates/assess",
            json={
                "base_version_id": saved["version"]["version_id"],
                "updated_case": updated,
                "trigger": "clinical_change",
                "change_summary": "Care site changed for the synthetic case.",
                "attested": True,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["changed_paths"] == ["care_site"]
    assert body["specialist_agents_to_rerun"] == ["clinical_trials"]
    assert "guideline" in body["specialist_agents_eligible_for_reuse"]
    assert "clinical_red_team" in body["always_rerun_controls"]
    assert body["prior_decision_status"] == "historical_only"
    assert body["evidence_review_required"] is True


def test_targeted_rerun_reuses_only_unaffected_specialist_outputs(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "phase8-rerun.sqlite3")
    case = _case_payload()
    with _client(version_store=store) as client:
        saved = _save_initial_version(client, case)
        updated = dict(case)
        updated["care_site"] = "Synthetic academic cancer center"
        candidates = client.post(
            "/api/v1/evidence/candidates",
            json={"case": updated, "mode": "guided_fixture"},
        ).json()
        decisions = [
            {
                "candidate_id": candidate["candidate_id"],
                "decision": "approved" if candidate["channel"] == "guideline" else "rejected",
                "reason": "Controlled fixture is excluded from governed reasoning." if candidate["synthetic"] else "",
            }
            for candidate in candidates["candidates"]
        ]
        response = client.post(
            "/api/v1/workflows/rerun-targeted",
            json={
                "base_version_id": saved["version"]["version_id"],
                "case": updated,
                "evidence_commission": {
                    "mode": "guided_fixture",
                    "candidate_set_id": candidates["candidate_set_id"],
                    "decisions": decisions,
                    "attested": True,
                },
                "trigger": "clinical_change",
                "change_summary": "Care site changed for the synthetic case.",
                "update_attested": True,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["rerun"]["base_version_id"] == saved["version"]["version_id"]
    assert "clinical_trials" in body["rerun"]["specialist_agents_executed"]
    assert body["rerun"]["specialist_agents_reused"]
    assert "clinical_red_team" in body["rerun"]["always_rerun_controls"]
    assert any(event["source_event"] == "agent_output_reused" for event in body["events"])
    assert body["result"]["final_decision"]


def test_workflow_endpoint_returns_result_and_real_activity_events() -> None:
    payload = {"case": _case_payload()}
    with _client() as client:
        response = client.post(
            "/api/v1/workflows/run",
            json=payload,
            headers={"X-Request-ID": "phase1-workflow-check"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "phase1-workflow-check"
    assert body["case_id"] == payload["case"]["case_id"]
    assert body["research_use_only"] is True
    assert body["result"]["final_decision"]["decision_state"]

    audit_names = [event["event"] for event in body["result"]["audit_events"]]
    activity_names = [event["source_event"] for event in body["events"]]
    assert activity_names == audit_names
    assert body["events"][0]["source_event"] == "workflow_started"
    assert body["events"][0]["event_id"] == "phase1-workflow-check:1"
    assert body["events"][-1]["source_event"] == "workflow_complete"
    assert any(event["source_event"] == "agent_complete" for event in body["events"])


def test_public_api_rejects_non_research_case_types() -> None:
    case = _case_payload()
    case["case_type"] = "clinical"

    with _client() as client:
        response = client.post("/api/v1/workflows/run", json={"case": case})

    assert response.status_code == 403
    assert "synthetic or fully de-identified" in response.json()["detail"]


def test_request_contract_rejects_unknown_top_level_fields() -> None:
    with _client() as client:
        response = client.post(
            "/api/v1/workflows/run",
            json={"case": _case_payload(), "unreviewed_override": True},
        )

    assert response.status_code == 422


def test_dependency_builds_a_fresh_context_for_each_request(monkeypatch) -> None:
    built = 0

    def fresh_context() -> WorkflowContext:
        nonlocal built
        built += 1
        return _test_context(marker=built)

    monkeypatch.setattr(api_main, "build_workflow_context", fresh_context)
    application = api_main.create_app()
    with TestClient(application) as client:
        first = client.get("/api/v1/runtime/status").json()
        second = client.get("/api/v1/runtime/status").json()

    assert first["runtime_status"]["context_number"] == 1
    assert second["runtime_status"]["context_number"] == 2
    assert built == 2


def test_invalid_request_id_is_replaced() -> None:
    with _client() as client:
        response = client.get("/health", headers={"X-Request-ID": "contains spaces"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "contains spaces"
    assert len(response.headers["X-Request-ID"]) == 32


def test_phase9_security_headers_are_applied_to_api_responses() -> None:
    with _client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_phase9_request_size_limit_rejects_oversized_payload(monkeypatch) -> None:
    monkeypatch.setenv("MAX_REQUEST_BYTES", "1024")
    with _client() as client:
        response = client.post(
            "/api/v1/workflows/run",
            content=b"{}",
            headers={"Content-Type": "application/json", "Content-Length": "2048"},
        )

    assert response.status_code == 413
    assert "configured service limit" in response.json()["detail"]


def test_phase9_trusted_host_rejects_unrecognized_host() -> None:
    with _client() as client:
        response = client.get("/health", headers={"Host": "untrusted.example"})

    assert response.status_code == 400


def test_phase9_workflow_evaluation_passes_governed_package(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "phase9-evaluation.sqlite3")
    case = _case_payload()
    with _client(version_store=store) as client:
        workflow_response, evidence_review, human_response = _governed_snapshot(client, case)
        response = client.post(
            "/api/v1/evaluations/workflow",
            json={
                "workflow": workflow_response,
                "case_type": case["case_type"],
                "evidence_review": evidence_review,
                "human_decision": human_response,
            },
        )

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "pass"
    assert body["release_eligible"] is True
    assert body["metrics"]["critical_gate_failures"] == 0
    assert all(gate["status"] == "pass" for gate in body["gates"])


def test_phase9_evaluation_detects_decision_lineage_tampering(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "phase9-lineage.sqlite3")
    case = _case_payload()
    with _client(version_store=store) as client:
        workflow_response, evidence_review, human_response = _governed_snapshot(client, case)
        human_response["system_decision"] = {"decision_state": "tampered"}
        response = client.post(
            "/api/v1/evaluations/workflow",
            json={
                "workflow": workflow_response,
                "case_type": case["case_type"],
                "evidence_review": evidence_review,
                "human_decision": human_response,
            },
        )

    body = response.json()
    lineage = next(gate for gate in body["gates"] if gate["gate_id"] == "human_decision_separation")
    assert response.status_code == 200
    assert body["status"] == "fail"
    assert body["release_eligible"] is False
    assert lineage["status"] == "fail"


def test_phase9_evaluation_detects_unsafe_strategy_render(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "phase9-render.sqlite3")
    case = _case_payload()
    with _client(version_store=store) as client:
        workflow_response, evidence_review, human_response = _governed_snapshot(client, case)
        workflow_response["result"]["final_decision"]["primary_strategy"] = "Unsafe injected strategy"
        workflow_response["result"]["consensus_report"]["safe_to_render_decision_support"] = False
        human_response["system_decision"] = workflow_response["result"]["final_decision"]
        response = client.post(
            "/api/v1/evaluations/workflow",
            json={
                "workflow": workflow_response,
                "case_type": case["case_type"],
                "evidence_review": evidence_review,
                "human_decision": human_response,
            },
        )

    unsafe = next(gate for gate in response.json()["gates"] if gate["gate_id"] == "unsafe_strategy_render")
    assert response.status_code == 200
    assert unsafe["status"] == "fail"


def test_phase9_evaluation_summary_moves_from_pending_to_pass(tmp_path) -> None:
    store = SQLiteCaseVersionStore(tmp_path / "phase9-summary.sqlite3")
    case = _case_payload()
    with _client(version_store=store) as client:
        pending = client.get("/api/v1/evaluations/summary").json()
        _save_initial_version(client, case)
        complete = client.get("/api/v1/evaluations/summary").json()

    assert pending["current_state"] == "baseline_pending"
    assert pending["versions_evaluated"] == 0
    assert pending["primary_metrics"][0]["value"] is None
    assert complete["current_state"] == "pass"
    assert complete["versions_evaluated"] == 1
    assert all(metric["value"] == 1.0 for metric in complete["primary_metrics"])
    assert all(guardrail["value"] == 0 for guardrail in complete["guardrails"])


def test_phase9_release_readiness_separates_local_production_and_clinical(monkeypatch) -> None:
    for name in (
        "DEPLOYMENT_ENV",
        "AUTH_MODE",
        "REQUIRE_HTTPS",
        "CORS_ALLOWED_ORIGINS",
        "TRUSTED_HOSTS",
        "RATE_LIMITING_MODE",
        "MONITORING_SINK",
        "BACKUP_POLICY",
        "TUMOR_BOARD_STATE_DB",
        "DATABASE_URL",
        "OIDC_ISSUER",
        "OIDC_AUDIENCE",
    ):
        monkeypatch.delenv(name, raising=False)
    with _client() as client:
        response = client.get("/api/v1/release/readiness")

    body = response.json()
    assert response.status_code == 200
    assert body["local_research_ready"] is True
    assert body["production_research_ready"] is False
    assert body["overall_state"] == "production_research_blocked"
    assert body["clinical_release_authorized"] is False
    assert any(check["level"] == "clinical_release" and check["status"] == "blocked" for check in body["checks"])
