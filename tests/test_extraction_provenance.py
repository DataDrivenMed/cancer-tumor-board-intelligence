from agents.extraction import (
    SYSTEM_INSTRUCTIONS,
    _fact_requires_verified_provenance,
    _verified_provenance,
)
from schemas.case import DataStatus, Fact
from services.document_parser import parse_text


def test_parse_text_assigns_stable_segment_ids():
    document = parse_text("First fact.\nSecond fact.", document_id="TEST")
    assert [s.segment_id for s in document.segments] == ["S0001", "S0002"]
    assert document.segments[0].text == "First fact."


def test_exact_excerpt_verifies_against_segment():
    document = parse_text("FLT3-ITD detected with variant allele frequency 31%.", document_id="TEST")
    provenance, verified = _verified_provenance(
        document,
        ["S0001"],
        "FLT3-ITD detected with variant allele frequency 31%.",
    )
    assert verified is True
    assert provenance.source_verified is True


def test_paraphrased_excerpt_fails_verification():
    document = parse_text("FLT3-ITD detected with variant allele frequency 31%.", document_id="TEST")
    provenance, verified = _verified_provenance(
        document,
        ["S0001"],
        "FLT3 mutation is present at 31 percent.",
    )
    assert verified is False
    assert provenance.source_verified is False


def test_pending_results_must_be_represented_as_missing_items():
    instructions = SYSTEM_INSTRUCTIONS.lower()
    assert "must also appear in missing_items" in instructions
    assert "availability to 'pending'" in instructions
    assert "never convert a pending test into a positive or negative result" in instructions
    assert "completeness audit" in instructions


def test_explicit_current_disease_state_must_be_preserved():
    instructions = SYSTEM_INSTRUCTIONS.lower()
    assert "preserve explicit current disease-state qualifiers" in instructions
    assert "newly diagnosed" in instructions
    assert "remote historical conditions" in instructions


def test_provenance_metric_counts_supported_assertions_not_empty_unknown_placeholders():
    confirmed = Fact(field="diagnosis", value="mantle cell lymphoma", status=DataStatus.CONFIRMED)
    conflicting = Fact(field="stage", value="III vs IV", status=DataStatus.CONFLICTING)
    unknown = Fact(field="disease_state", value=None, status=DataStatus.NOT_DOCUMENTED)
    pending_without_value = Fact(field="molecular", value=None, status=DataStatus.PENDING)

    assert _fact_requires_verified_provenance(confirmed)
    assert _fact_requires_verified_provenance(conflicting)
    assert not _fact_requires_verified_provenance(unknown)
    assert not _fact_requires_verified_provenance(pending_without_value)
