from __future__ import annotations

from schemas.case import DataStatus
from services.document_parser import parse_text
from services.explicit_stage_extraction import extract_explicit_stage


def test_explicit_stage_is_admitted_with_exact_provenance():
    document = parse_text(
        "Pathology confirms breast carcinoma.\nClinical stage IIIA is documented after staging workup.",
        document_id="DOC-STAGE-001",
    )
    result = extract_explicit_stage(document)
    assert result.fact is not None
    assert result.fact.status == DataStatus.CONFIRMED
    assert result.fact.value == "Clinical stage IIIA"
    assert result.fact.provenance[0].source_verified is True
    assert result.fact.provenance[0].source_excerpt == "Clinical stage IIIA"
    assert result.fact.provenance[0].source_segment_ids == ["S0002"]


def test_tnm_without_explicit_stage_is_not_converted_into_stage():
    document = parse_text(
        "Pathology: adenocarcinoma. TNM is documented as T2N1M0.",
        document_id="DOC-STAGE-002",
    )
    result = extract_explicit_stage(document)
    assert result.fact is None
    assert result.candidate_count == 0


def test_distinct_explicit_stage_labels_fail_closed_as_conflicting():
    document = parse_text(
        "Outside note lists stage II disease.\nCurrent oncology note lists stage III disease.",
        document_id="DOC-STAGE-003",
    )
    result = extract_explicit_stage(document)
    assert result.fact is not None
    assert result.fact.status == DataStatus.CONFLICTING
    assert result.fact.value is None
    assert len(result.fact.provenance) == 2
    assert all(item.source_verified for item in result.fact.provenance)
    assert result.warnings


def test_equivalent_roman_and_arabic_stage_labels_do_not_create_false_conflict():
    document = parse_text(
        "The operative note states stage III disease.\nThe oncology summary also records stage 3.",
        document_id="DOC-STAGE-004",
    )
    result = extract_explicit_stage(document)
    assert result.fact is not None
    assert result.fact.status == DataStatus.CONFIRMED
    assert result.candidate_count == 2
