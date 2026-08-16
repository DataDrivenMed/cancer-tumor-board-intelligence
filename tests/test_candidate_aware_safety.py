from __future__ import annotations

import json
from pathlib import Path

from schemas.case import CancerTumorBoardCase
from schemas.safety import SafetyEvidenceRecord, SafetyEvidenceStore, SafetyEvidenceType, SafetySeverity
from services.eln_aml_guidance import public_eln_aml_store
from services.runtime_agents import CandidateAwareSafetyAgent


ROOT = Path(__file__).resolve().parents[1]


def _case() -> CancerTumorBoardCase:
    payload = json.loads((ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))
    return CancerTumorBoardCase.model_validate(payload)


def _store() -> SafetyEvidenceStore:
    return SafetyEvidenceStore(records=[
        SafetyEvidenceRecord(
            evidence_id="FDA-TEST-GILT-001",
            source_id="SPL-TEST",
            source_title="FDA Structured Product Labeling: gilteritinib",
            source_locator="warnings_and_cautions; synthetic test span",
            source_excerpt="Reviewed source span for deterministic software testing.",
            source_verified=True,
            human_verified=True,
            synthetic=False,
            therapy_terms=["gilteritinib"],
            disease_terms=["acute myeloid leukemia"],
            evidence_type=SafetyEvidenceType.WARNING,
            severity=SafetySeverity.MODERATE,
            safety_issue="Reviewed warning context for test fixture.",
            contraindication=False,
        )
    ])


def test_candidate_aware_safety_matches_guideline_candidate_therapy():
    case = _case()
    report = CandidateAwareSafetyAgent(_store(), public_eln_aml_store()).run(case)

    assert report.status == "completed"
    assert report.can_support_safety_claim is True
    assert report.recommendation_blocking is False
    assert len(report.findings) == 1
    assert report.findings[0].therapy_terms_matched == ["gilteritinib"]


def test_candidate_aware_safety_does_not_invent_candidate_without_molecular_prerequisite():
    case = _case()
    case.molecular_findings[0].human_verified = False

    report = CandidateAwareSafetyAgent(_store(), public_eln_aml_store()).run(case)

    assert report.status == "no_evidence_found"
    assert report.can_support_safety_claim is False
    assert report.findings == []
