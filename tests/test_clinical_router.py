from __future__ import annotations

from orchestration.router import route_case
from schemas.case import (
    CancerTumorBoardCase,
    ClinicalQuestion,
    Fact,
    MolecularFinding,
    Provenance,
    TreatmentEpisode,
    TreatmentStatus,
)


def _prov(text: str = "source") -> Provenance:
    return Provenance(
        document_id="DOC-1",
        source_excerpt=text,
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def _fact(field: str, value: str) -> Fact:
    return Fact(field=field, value=value, provenance=[_prov(value)])


def _case(question_type: str, question: str) -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="ROUTE-001",
        disease_program="hematologic_malignancy",
        diagnosis=_fact("diagnosis", "acute myeloid leukemia"),
        disease_state=_fact("disease_state", "newly diagnosed"),
        performance_status=_fact("ECOG", "1"),
        clinical_question=ClinicalQuestion(question_type=question_type, question=question),
    )


def test_management_route_includes_core_clinical_agents() -> None:
    route = route_case(_case("management", "What treatment should be discussed?"))
    assert route.router_version == "1.0.0"
    assert route.selected_agents == ["guideline", "literature", "clinical_trials", "safety"]
    assert set(route.required_agents) == {"guideline", "literature", "safety"}
    assert route.conditional_agents == ["clinical_trials"]
    assert route.safe_to_execute is True


def test_molecular_management_adds_molecular_and_translational() -> None:
    case = _case("management", "How should treatment be framed with this mutation?")
    case.molecular_findings = [MolecularFinding(
        gene="FLT3",
        alteration_type="ITD",
        provenance=[_prov("FLT3-ITD detected")],
    )]
    route = route_case(case)
    assert "molecular" in route.selected_agents
    assert "translational" in route.selected_agents
    assert "molecular" in route.required_agents
    assert "translational" in route.conditional_agents


def test_explicit_translational_question_requires_translational_agent() -> None:
    route = route_case(_case(
        "translational_biology",
        "What resistance mechanism and pathway biology should be reviewed?",
    ))
    assert "translational_biology" in route.question_domains
    assert "translational" in route.selected_agents
    assert "translational" in route.required_agents


def test_pure_safety_question_routes_only_to_safety() -> None:
    route = route_case(_case(
        "safety",
        "What toxicity, contraindication, and interaction issues should be reviewed?",
    ))
    assert route.question_domains == ["safety"]
    assert route.selected_agents == ["safety"]
    assert route.required_agents == ["safety"]
    assert set(route.omitted_agents) == {"guideline", "molecular", "translational", "literature", "clinical_trials"}


def test_multiline_heavily_pre_treated_case_is_high_complexity() -> None:
    case = _case("management", "What treatment and trial options should be discussed?")
    case.disease_state = _fact("disease_state", "relapsed refractory")
    case.molecular_findings = [MolecularFinding(
        gene="TP53", alteration_type="mutation", provenance=[_prov("TP53 mutation detected")]
    )]
    case.treatments = [
        TreatmentEpisode(episode_id=f"TX-{i:03d}", regimen=f"Regimen {i}", treatment_status=TreatmentStatus.COMPLETED, provenance=[_prov()])
        for i in range(1, 4)
    ]
    route = route_case(case)
    assert route.complexity == "high_complexity"
    assert route.requires_parallel_execution is True


def test_router_is_deterministic() -> None:
    case = _case("management", "What treatment should be discussed?")
    assert route_case(case).model_dump() == route_case(case).model_dump()


def test_selected_agent_order_is_stable() -> None:
    case = _case("management", "Review molecular treatment, trial, literature, and safety implications")
    case.molecular_findings = [MolecularFinding(
        gene="NPM1", alteration_type="mutation", provenance=[_prov("NPM1 mutation detected")]
    )]
    route = route_case(case)
    expected_order = ["guideline", "molecular", "translational", "literature", "clinical_trials", "safety"]
    assert route.selected_agents == expected_order
