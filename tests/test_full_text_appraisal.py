from hashlib import sha256

from schemas.full_text_appraisal import (
    ApplicabilityAssessment,
    ApplicabilityJudgement,
    EffectEstimate,
    EndpointRecord,
    FullTextAppraisalCandidate,
    FullTextSourceSnapshot,
    PICOField,
    RiskOfBiasAssessment,
    RiskOfBiasJudgement,
    StructuredPICO,
)
from services.full_text_appraisal import appraise_full_text


TEXT = (
    "Adults with relapsed acute myeloid leukemia were randomized to regimen A or regimen B. "
    "The primary endpoint was overall survival. Median overall survival was 9.0 months with regimen A "
    "and 6.0 months with regimen B, hazard ratio 0.70, 95% CI 0.55-0.89."
)
HASH = sha256(TEXT.encode("utf-8")).hexdigest()


def source(**kwargs):
    base = dict(
        pmid="12345678",
        title="Synthetic randomized AML study",
        full_text=TEXT,
        full_text_sha256=HASH,
        source_type="synthetic_fixture",
        source_verified=True,
    )
    base.update(kwargs)
    return FullTextSourceSnapshot(**base)


def candidate(**kwargs):
    base = dict(
        appraisal_id="APP-001",
        pmid="12345678",
        study_design="randomized controlled trial",
        pico=StructuredPICO(
            population=PICOField(value="Adults with relapsed AML", source_excerpt="Adults with relapsed acute myeloid leukemia"),
            intervention=PICOField(value="regimen A", source_excerpt="regimen A"),
            comparator=PICOField(value="regimen B", source_excerpt="regimen B"),
            outcome=PICOField(value="overall survival", source_excerpt="The primary endpoint was overall survival"),
        ),
        endpoints=[EndpointRecord(name="overall survival", endpoint_type="primary", source_excerpt="The primary endpoint was overall survival")],
        effect_estimates=[EffectEstimate(
            endpoint_name="overall survival",
            effect_measure="hazard ratio",
            effect_value="0.70",
            confidence_interval="95% CI 0.55-0.89",
            source_excerpt="Median overall survival was 9.0 months with regimen A and 6.0 months with regimen B, hazard ratio 0.70, 95% CI 0.55-0.89",
        )],
        risk_of_bias=RiskOfBiasAssessment(
            randomization=RiskOfBiasJudgement.LOW,
            deviations_from_intervention=RiskOfBiasJudgement.LOW,
            missing_outcome_data=RiskOfBiasJudgement.LOW,
            outcome_measurement=RiskOfBiasJudgement.LOW,
            selective_reporting=RiskOfBiasJudgement.LOW,
            overall=RiskOfBiasJudgement.LOW,
            reviewer_rationale="Synthetic low-risk fixture.",
            human_verified=True,
        ),
        applicability=ApplicabilityAssessment(
            judgement=ApplicabilityJudgement.HIGH,
            disease_match="exact",
            disease_state_match="relapsed",
            population_match="adult",
            treatment_context_match="salvage",
            reviewer_rationale="Synthetic high-applicability fixture.",
            human_verified=True,
        ),
        linked_claim_ids=["CLM-001"],
        human_verified=True,
    )
    base.update(kwargs)
    return FullTextAppraisalCandidate(**base)


def test_fully_verified_appraisal_can_influence_synthesis():
    report = appraise_full_text(source(), candidate())
    assert report.status.value == "verified"
    assert report.can_influence_synthesis is True
    assert report.linked_claims_verified_for_full_text == ["CLM-001"]
    assert report.effect_estimates_verified == 1


def test_hash_mismatch_rejects():
    report = appraise_full_text(source(full_text_sha256="0" * 64), candidate())
    assert report.status.value == "rejected"
    assert report.can_influence_synthesis is False


def test_non_exact_pico_excerpt_rejects():
    bad = candidate()
    bad.pico.population.source_excerpt = "Adults with relapsed AML"
    report = appraise_full_text(source(), bad)
    assert report.status.value == "rejected"


def test_non_exact_effect_excerpt_rejects():
    bad = candidate()
    bad.effect_estimates[0].source_excerpt = "HR 0.70"
    report = appraise_full_text(source(), bad)
    assert report.status.value == "rejected"


def test_unverified_risk_of_bias_is_partial_and_claim_not_promoted():
    bad = candidate()
    bad.risk_of_bias.human_verified = False
    report = appraise_full_text(source(), bad)
    assert report.status.value == "partially_verified"
    assert report.can_influence_synthesis is False
    assert report.linked_claims_verified_for_full_text == []


def test_unverified_applicability_is_partial():
    bad = candidate()
    bad.applicability.judgement = ApplicabilityJudgement.UNCLEAR
    report = appraise_full_text(source(), bad)
    assert report.status.value == "partially_verified"
    assert report.can_influence_synthesis is False


def test_pmid_mismatch_rejects():
    report = appraise_full_text(source(), candidate(pmid="99999999"))
    assert report.status.value == "rejected"


def test_repeatability_is_deterministic():
    first = appraise_full_text(source(), candidate()).model_dump()
    second = appraise_full_text(source(), candidate()).model_dump()
    assert first == second
