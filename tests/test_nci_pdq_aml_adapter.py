from __future__ import annotations

from datetime import date, datetime

from agents.guideline import GuidelineAgent
from services.evidence_gateway import verify_evidence_package
from services.nci_pdq_aml_adapter import (
    NCIPDQSnapshot,
    attest_nci_aml_pdq_candidate,
    build_nci_aml_pdq_candidate,
    html_to_visible_text,
)
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, Provenance
from schemas.guideline import GuidanceSourceType


FIXTURE_TEXT = " ".join([
    "Acute Myeloid Leukemia Treatment (PDQ®)–Health Professional Version",
    "A peripheral blood or bone marrow blast count of 20% or greater is required to make the diagnosis, except for cases with certain chromosomal abnormalities (i.e., t(15;17), t(8;21), inv(16), or t(16;16)).",
    "Cytogenetic and molecular analyses provide the strongest prognostic information available, predicting outcome of both remission induction and consolidation therapy.",
    "Untreated AML is defined as newly diagnosed leukemia that has not been previously treated.",
    "No standard treatment regimen exists for patients with refractory or recurrent acute myeloid leukemia (AML).",
    "Updated: March 14, 2025",
])


def snapshot(text: str = FIXTURE_TEXT) -> NCIPDQSnapshot:
    from services.evidence_gateway import normalized_sha256
    return NCIPDQSnapshot(
        url="https://www.cancer.gov/types/leukemia/hp/adult-aml-treatment-pdq",
        fetched_utc=datetime(2026, 8, 15, 23, 0, 0),
        source_text=text,
        content_sha256=normalized_sha256(text),
        updated_date=date(2025, 3, 14),
    )


def case(state: str = "recurrent") -> CancerTumorBoardCase:
    prov = Provenance(document_id="T", source_excerpt="AML", source_segment_ids=["S1"], source_verified=True)
    return CancerTumorBoardCase(
        case_id="NCI-ADAPTER-TEST",
        diagnosis=Fact(field="diagnosis", value="acute myeloid leukemia", provenance=[prov]),
        disease_state=Fact(field="disease_state", value=state, provenance=[prov]),
        performance_status=Fact(field="ECOG", value="1", provenance=[prov]),
        clinical_question=ClinicalQuestion(question_type="management", question="What treatment should be discussed?"),
    )


def test_visible_text_parser_removes_script_and_normalizes_whitespace() -> None:
    html = "<html><body><h1>Acute Myeloid Leukemia Treatment</h1><script>bad()</script><p>A  B</p></body></html>"
    assert html_to_visible_text(html) == "Acute Myeloid Leukemia Treatment A B"


def test_candidate_is_authoritative_summary_and_not_auto_verified() -> None:
    build = build_nci_aml_pdq_candidate(snapshot())
    assert build.package.manifest.source_type == GuidanceSourceType.AUTHORITATIVE_EVIDENCE_SUMMARY
    assert build.package.manifest.human_verified is False
    assert len(build.package.recommendations) == 4
    assert all(r.human_verified is False for r in build.package.recommendations)
    assert build.package.manifest.updated_date == date(2025, 3, 14)


def test_unattested_candidate_fails_gateway() -> None:
    build = build_nci_aml_pdq_candidate(snapshot())
    result, store = verify_evidence_package(build.package, production_mode=True)
    assert result.status.value == "rejected"
    assert result.can_enter_guideline_store is False
    assert len(store.sources) == 0


def test_attested_candidate_enters_store_but_never_supports_guideline_claim() -> None:
    build = build_nci_aml_pdq_candidate(snapshot())
    ids = {r.recommendation_id for r in build.package.recommendations}
    package = attest_nci_aml_pdq_candidate(
        build,
        source_human_verified=True,
        verified_recommendation_ids=ids,
        verification_note="Reviewed against the live NCI page in test fixture.",
    )
    result, store = verify_evidence_package(package, production_mode=True)
    assert result.status.value == "accepted"
    assert result.can_enter_guideline_store is True

    report = GuidelineAgent(store, today=date(2026, 8, 15)).run(case())
    assert report.status == "completed_with_limitations"
    assert report.can_support_guideline_claim is False
    assert report.formal_guideline_matches == 0
    assert any(m.source_type == GuidanceSourceType.AUTHORITATIVE_EVIDENCE_SUMMARY for m in report.matched_guidance)


def test_changed_source_statement_fails_closed() -> None:
    changed = FIXTURE_TEXT.replace(
        "No standard treatment regimen exists for patients with refractory or recurrent acute myeloid leukemia (AML).",
        "This sentence was changed upstream.",
    )
    build = build_nci_aml_pdq_candidate(snapshot(changed))
    ids = {r.recommendation_id for r in build.package.recommendations}
    assert "NCI-PDQ-AML-RR-001" not in ids
    assert any("NCI-PDQ-AML-RR-001" in warning for warning in build.warnings)


def test_partial_reviewer_attestation_rejects_unreviewed_statement_only() -> None:
    build = build_nci_aml_pdq_candidate(snapshot())
    first = build.package.recommendations[0].recommendation_id
    package = attest_nci_aml_pdq_candidate(
        build,
        source_human_verified=True,
        verified_recommendation_ids={first},
    )
    result, store = verify_evidence_package(package, production_mode=True)
    assert result.status.value == "accepted_with_limitations"
    assert result.accepted_recommendation_ids == [first]
    assert len(store.recommendations) == 1
