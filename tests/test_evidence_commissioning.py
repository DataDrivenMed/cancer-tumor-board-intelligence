from __future__ import annotations

from datetime import date

from schemas.molecular import (
    ClinicalActionability,
    MolecularEvidenceDirection,
    MolecularEvidenceRecord,
    MolecularEvidenceTier,
)
from services.evidence_commissioning import (
    build_approved_molecular_store,
    build_approved_safety_store,
    safety_candidate_excerpt,
)
from services.fda_label_adapter import FDALabelSectionCandidate


def _molecular(evidence_id: str) -> MolecularEvidenceRecord:
    return MolecularEvidenceRecord(
        evidence_id=evidence_id,
        source_id=evidence_id,
        source_title="CIViC software-test evidence",
        source_url="https://civicdb.org/",
        source_type=MolecularEvidenceTier.CLINICAL,
        accessed_date=date(2026, 8, 16),
        disease_terms=["acute myeloid leukemia"],
        gene="FLT3",
        alteration_terms=["ITD"],
        direction=MolecularEvidenceDirection.SUPPORTS_SENSITIVITY,
        actionability=ClinicalActionability.EMERGING,
        therapy="gilteritinib",
        evidence_summary="Bounded software-test statement.",
        source_excerpt="Bounded software-test statement.",
        source_locator=evidence_id,
        source_verified=True,
        human_verified=False,
        synthetic=False,
    )


def test_only_explicitly_selected_civic_record_becomes_human_verified():
    store = build_approved_molecular_store(
        [_molecular("CIVIC-EID-1"), _molecular("CIVIC-EID-2")],
        {"CIVIC-EID-2"},
    )
    states = {record.evidence_id: record.human_verified for record in store.records}
    assert states == {"CIVIC-EID-1": False, "CIVIC-EID-2": True}


def test_fda_selection_attests_exact_displayed_span_without_patient_specific_contraindication():
    candidate = FDALabelSectionCandidate(
        therapy="gilteritinib",
        spl_set_id="SPL-1",
        spl_id="ID-1",
        application_number="NDA-TEST",
        effective_time="20260816",
        section="contraindications",
        text="Contraindications section source text used only for deterministic software testing.",
        source_url="https://api.fda.gov/drug/label.json",
        accessed_date=date(2026, 8, 16),
    )
    store = build_approved_safety_store([candidate], {0})
    assert len(store.records) == 1
    record = store.records[0]
    assert record.human_verified is True
    assert record.source_verified is True
    assert record.source_excerpt == safety_candidate_excerpt(candidate)
    assert record.contraindication is False


def test_unselected_fda_candidate_is_not_admitted():
    candidate = FDALabelSectionCandidate(
        therapy="gilteritinib",
        spl_set_id="SPL-2",
        spl_id="ID-2",
        application_number="NDA-TEST",
        effective_time="20260816",
        section="warnings_and_cautions",
        text="Warning section source text used only for deterministic software testing.",
        source_url="https://api.fda.gov/drug/label.json",
        accessed_date=date(2026, 8, 16),
    )
    store = build_approved_safety_store([candidate], set())
    assert store.records == []
