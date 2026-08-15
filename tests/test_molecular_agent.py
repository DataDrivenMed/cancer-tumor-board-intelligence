from datetime import date

from agents.molecular import MolecularInterpretationAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MolecularFinding
from schemas.molecular import ClinicalActionability
from services.molecular_sources import build_synthetic_molecular_store


def _case(*, gene="FLT3", alteration="ITD", diagnosis="acute myeloid leukemia"):
    return CancerTumorBoardCase(
        case_id="mol-test",
        diagnosis=Fact(field="diagnosis", value=diagnosis),
        disease_state=Fact(field="disease_state", value="relapsed"),
        molecular_findings=[MolecularFinding(gene=gene, alteration_type=alteration)],
        clinical_question=ClinicalQuestion(question_type="molecular", question="What is the molecular significance?"),
    )


def test_production_store_empty_fails_safe():
    report = MolecularInterpretationAgent().run(_case())
    assert report.status == "source_unavailable"
    assert report.can_support_clinical_actionability_claim is False


def test_synthetic_store_blocked_in_production():
    report = MolecularInterpretationAgent(build_synthetic_molecular_store(), production_mode=True).run(_case())
    assert report.status == "source_unavailable"
    assert report.can_support_clinical_actionability_claim is False


def test_exact_gene_and_alteration_match_in_test_mode():
    report = MolecularInterpretationAgent(build_synthetic_molecular_store(), production_mode=False).run(_case())
    assert report.status == "completed"
    assert report.interpretations[0].clinical_actionability == ClinicalActionability.ESTABLISHED
    assert report.interpretations[0].can_support_clinical_actionability_claim is True
    assert report.interpretations[0].matched_evidence_ids == ["syn-flt3-001"]


def test_gene_match_without_alteration_match_does_not_infer_actionability():
    report = MolecularInterpretationAgent(build_synthetic_molecular_store(), production_mode=False).run(_case(alteration="D835"))
    assert report.status == "no_evidence_found"
    assert report.interpretations[0].clinical_actionability == ClinicalActionability.UNKNOWN
    assert report.interpretations[0].can_support_clinical_actionability_claim is False


def test_disease_context_mismatch_does_not_match():
    report = MolecularInterpretationAgent(build_synthetic_molecular_store(), production_mode=False).run(
        _case(diagnosis="multiple myeloma")
    )
    assert report.status == "no_evidence_found"
    assert report.can_support_clinical_actionability_claim is False


def test_prognostic_record_does_not_become_therapy_actionability():
    report = MolecularInterpretationAgent(build_synthetic_molecular_store(), production_mode=False).run(
        _case(gene="TP53", alteration="mutation")
    )
    assert report.status == "completed"
    item = report.interpretations[0]
    assert item.prognostic_signal is True
    assert item.clinical_actionability == ClinicalActionability.NOT_ESTABLISHED
    assert item.can_support_clinical_actionability_claim is False


def test_no_molecular_findings_is_not_interpreted_as_negative_test():
    case = _case()
    case.molecular_findings = []
    report = MolecularInterpretationAgent(build_synthetic_molecular_store(), production_mode=False).run(case)
    assert report.status == "no_evidence_found"
    assert "does not establish a negative molecular evaluation" in report.limitations[0]


def test_repeatability():
    agent = MolecularInterpretationAgent(build_synthetic_molecular_store(), production_mode=False)
    first = agent.run(_case()).model_dump()
    second = agent.run(_case()).model_dump()
    assert first == second
