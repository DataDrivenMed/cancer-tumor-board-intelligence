from agents.safety import SafetyAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact
from services.safety_sources import synthetic_safety_store


def _case(*, medication="Synthetic Drug X", include_monitoring=True, hypersensitivity=False):
    labs = []
    if include_monitoring:
        labs = [
            Fact(field="potassium", value="4.1 mmol/L"),
            Fact(field="magnesium", value="2.0 mg/dL"),
            Fact(field="ECG", value="QTc documented"),
        ]
    comorbidities = [Fact(field="allergy", value="synthetic hypersensitivity")] if hypersensitivity else []
    return CancerTumorBoardCase(
        case_id="safety-test",
        diagnosis=Fact(field="diagnosis", value="acute myeloid leukemia"),
        disease_state=Fact(field="disease_state", value="relapsed"),
        current_medications=[Fact(field="medication", value=medication)],
        labs=labs,
        comorbidities=comorbidities,
        clinical_question=ClinicalQuestion(question_type="safety", question="Review treatment safety."),
    )


def test_production_store_empty_fails_safe():
    report = SafetyAgent().run(_case())
    assert report.status == "source_unavailable"
    assert report.can_support_safety_claim is False
    assert report.recommendation_blocking is False


def test_synthetic_store_blocked_in_production():
    report = SafetyAgent(synthetic_safety_store(), production_mode=True).run(_case())
    assert report.status == "source_unavailable"
    assert report.can_support_safety_claim is False


def test_verified_monitoring_record_with_parameters_resolved():
    report = SafetyAgent(synthetic_safety_store(), production_mode=False).run(_case())
    assert report.status == "completed"
    assert report.can_support_safety_claim is True
    assert report.recommendation_blocking is False
    assert report.findings[0].evidence_id == "SYN-SAFE-001"
    assert report.findings[0].unresolved_parameters == []


def test_missing_required_monitoring_blocks_recommendation():
    report = SafetyAgent(synthetic_safety_store(), production_mode=False).run(
        _case(include_monitoring=False)
    )
    assert report.status == "completed_with_limitations"
    assert report.recommendation_blocking is True
    assert set(report.findings[0].unresolved_parameters) == {"potassium", "magnesium", "ecg"}


def test_therapy_mismatch_does_not_generate_safety_claim():
    report = SafetyAgent(synthetic_safety_store(), production_mode=False).run(
        _case(medication="Unrelated Therapy")
    )
    assert report.status == "no_evidence_found"
    assert report.can_support_safety_claim is False


def test_conditional_contraindication_requires_patient_trigger():
    no_trigger = SafetyAgent(synthetic_safety_store(), production_mode=False).run(
        _case(medication="Synthetic Drug Y", hypersensitivity=False)
    )
    assert no_trigger.status == "no_evidence_found"

    triggered = SafetyAgent(synthetic_safety_store(), production_mode=False).run(
        _case(medication="Synthetic Drug Y", hypersensitivity=True)
    )
    assert triggered.status == "completed"
    assert triggered.recommendation_blocking is True
    assert triggered.findings[0].contraindication is True
    assert triggered.findings[0].trigger_terms_matched == ["synthetic hypersensitivity"]


def test_no_match_is_not_declared_safe():
    report = SafetyAgent(synthetic_safety_store(), production_mode=False).run(
        _case(medication="Unrelated Therapy")
    )
    assert "does not establish" in report.limitations[0].lower()


def test_repeatability():
    agent = SafetyAgent(synthetic_safety_store(), production_mode=False)
    first = agent.run(_case()).model_dump()
    second = agent.run(_case()).model_dump()
    assert first == second
