from services.conflict_consistency import recover_explicit_conflicts
from services.document_parser import parse_text


def test_recovers_explicit_unresolved_stage_conflict():
    document = parse_text(
        "Clinic note lists stage III disease. PET/CT labels the disease stage IV. The staging discrepancy is unresolved.",
        document_id="TEST",
    )
    result = recover_explicit_conflicts(
        document=document,
        conflicts=[],
        missing_items=[
            {
                "field": "disease stage",
                "reason": "Staging discrepancy unresolved between stage III and stage IV",
            }
        ],
    )

    assert result.recovered is True
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict["field"] == "disease_stage"
    assert conflict["value_a"] == "stage III"
    assert conflict["value_b"] == "stage IV"
    assert conflict["source_segment_ids"] == ["S0001"]


def test_does_not_invent_conflict_from_single_stage_value():
    document = parse_text("PET/CT labels the disease stage IV.", document_id="TEST")
    result = recover_explicit_conflicts(document=document, conflicts=[], missing_items=[])
    assert result.recovered is False
    assert result.conflicts == []


def test_multiple_stage_values_without_discrepancy_cue_are_flagged_not_auto_created():
    document = parse_text(
        "Prior note documents stage III. Current summary states stage IV.",
        document_id="TEST",
    )
    result = recover_explicit_conflicts(document=document, conflicts=[], missing_items=[])
    assert result.recovered is False
    assert result.conflicts == []
    assert any("no conflict was auto-created" in warning for warning in result.warnings)


def test_existing_stage_conflict_is_not_duplicated():
    document = parse_text(
        "Clinic note lists stage III disease. PET/CT labels the disease stage IV. The discrepancy is unresolved.",
        document_id="TEST",
    )
    existing = [
        {
            "field": "stage",
            "value_a": "stage III",
            "value_b": "stage IV",
            "severity": "high",
            "source_segment_ids": ["S0001"],
        }
    ]
    result = recover_explicit_conflicts(document=document, conflicts=existing, missing_items=[])
    assert result.recovered is False
    assert result.conflicts == existing


def test_numeric_and_roman_stage_notation_normalize_to_same_value():
    document = parse_text(
        "One note says stage 3 disease. Another says stage III. No discrepancy is reported.",
        document_id="TEST",
    )
    result = recover_explicit_conflicts(document=document, conflicts=[], missing_items=[])
    assert result.recovered is False
    assert result.conflicts == []
