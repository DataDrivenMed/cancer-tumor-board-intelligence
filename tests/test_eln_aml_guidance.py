from __future__ import annotations

import json
from pathlib import Path

from agents.guideline import GuidelineAgent
from schemas.case import CancerTumorBoardCase
from services.eln_aml_guidance import public_eln_aml_store


ROOT = Path(__file__).resolve().parents[1]


def _case() -> CancerTumorBoardCase:
    payload = json.loads((ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))
    return CancerTumorBoardCase.model_validate(payload)


def test_eln_flt3_relapsed_aml_matches_verified_case_molecular_finding():
    case = _case()
    report = GuidelineAgent(public_eln_aml_store()).run(case)

    assert report.status == "completed"
    assert report.can_support_guideline_claim is True
    assert report.formal_guideline_matches == 1
    assert len(report.matched_guidance) == 1
    match = report.matched_guidance[0]
    assert match.recommendation_id == "ELN2022-RR-FLT3-GILTERITINIB"
    assert match.therapy_terms == ["gilteritinib"]
    assert "verified_molecular_prerequisite" in match.match_dimensions


def test_eln_targeted_guidance_does_not_match_unconfirmed_molecular_finding():
    case = _case()
    case.molecular_findings[0].human_verified = False

    report = GuidelineAgent(public_eln_aml_store()).run(case)

    assert report.status == "no_evidence_found"
    assert report.can_support_guideline_claim is False
    assert report.formal_guideline_matches == 0


def test_eln_targeted_guidance_does_not_match_different_gene():
    case = _case()
    case.molecular_findings[0].gene = "NPM1"
    case.molecular_findings[0].alteration_type = "mutation"

    report = GuidelineAgent(public_eln_aml_store()).run(case)

    assert report.status == "no_evidence_found"
    assert report.can_support_guideline_claim is False
