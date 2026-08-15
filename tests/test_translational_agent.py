from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MolecularFinding
from schemas.translational import TranslationalEvidenceStore
from agents.translational import TranslationalBiologyAgent
from services.translational_sources import SYNTHETIC_TRANSLATIONAL_STORE


def _case(gene="FLT3", alteration="FLT3-ITD", diagnosis="acute myeloid leukemia"):
    return CancerTumorBoardCase(
        case_id="translational-test",
        diagnosis=Fact(field="diagnosis", value=diagnosis, human_verified=True),
        disease_state=Fact(field="disease_state", value="relapsed", human_verified=True),
        molecular_findings=[MolecularFinding(gene=gene, alteration_type=alteration, human_verified=True)],
        clinical_question=ClinicalQuestion(question_type="molecular", question="What is the translational significance?"),
    )


def test_production_store_empty_fails_safe():
    report = TranslationalBiologyAgent(TranslationalEvidenceStore(), production_mode=True).run(_case())
    assert report.status == "source_unavailable"
    assert report.can_support_mechanistic_claim is False
    assert report.can_support_clinical_actionability_claim is False


def test_synthetic_store_blocked_in_production():
    report = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=True).run(_case())
    assert report.status == "source_unavailable"
    assert report.can_support_mechanistic_claim is False


def test_verified_synthetic_flt3_itd_supports_mechanistic_claim_only():
    report = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False).run(_case())
    assert report.status == "completed"
    assert report.can_support_mechanistic_claim is True
    assert report.can_support_clinical_actionability_claim is False
    assert report.findings[0].human_translational_support is True
    assert report.findings[0].clinical_actionability_claim is False


def test_gene_match_wrong_alteration_does_not_match():
    report = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False).run(_case(alteration="TKD point mutation"))
    assert report.status == "no_evidence_found"
    assert report.can_support_mechanistic_claim is False


def test_disease_context_mismatch_does_not_match():
    report = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False).run(_case(diagnosis="multiple myeloma"))
    assert report.status == "no_evidence_found"
    assert report.can_support_mechanistic_claim is False


def test_preclinical_resistance_does_not_become_actionability():
    report = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False).run(_case(gene="TP53", alteration="mutation"))
    assert report.status == "completed"
    assert report.can_support_mechanistic_claim is True
    assert report.can_support_clinical_actionability_claim is False
    assert report.findings[0].clinical_actionability_claim is False


def test_no_molecular_findings_is_not_negative_test_result():
    case = _case()
    case.molecular_findings = []
    report = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False).run(case)
    assert report.status == "no_evidence_found"
    assert "does not establish a negative molecular evaluation" in report.limitations[0]


def test_repeat_execution_is_deterministic():
    agent = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False)
    first = agent.run(_case()).model_dump()
    second = agent.run(_case()).model_dump()
    assert first == second
