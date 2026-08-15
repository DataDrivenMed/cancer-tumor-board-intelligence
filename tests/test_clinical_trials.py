from __future__ import annotations

from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MolecularFinding
from agents.clinical_trials import ClinicalTrialsAgent, build_trial_query
from schemas.clinical_trials import TrialRecord
from services.clinicaltrials_client import parse_study


def _case(*, diagnosis="Acute myeloid leukemia", gene="FLT3"):
    molecular = [MolecularFinding(gene=gene, alteration_type="ITD")] if gene else []
    return CancerTumorBoardCase(
        case_id="trial-test",
        diagnosis=Fact(field="diagnosis", value=diagnosis),
        disease_state=Fact(field="disease_state", value="relapsed"),
        molecular_findings=molecular,
        clinical_question=ClinicalQuestion(question_type="trial", question="What clinical trials may be relevant?"),
    )


class StubClient:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def search(self, *, condition, other_terms=None, page_size=10):
        self.calls.append((condition, list(other_terms or []), page_size))
        return "2026-08-15T14:00:00Z", list(self.records)


def _record(*, status="RECRUITING", condition="Acute myeloid leukemia", title="FLT3 study"):
    return TrialRecord(
        nct_id="NCT00000001",
        title=title,
        overall_status=status,
        conditions=[condition],
        interventions=["Investigational agent"],
        eligibility_criteria="Adults with FLT3-mutated AML may be screened. Additional criteria apply.",
        source_url="https://clinicaltrials.gov/study/NCT00000001",
    )


def test_bounded_query_uses_structured_diagnosis_and_gene_only():
    condition, terms = build_trial_query(_case())
    assert condition == "Acute myeloid leukemia"
    assert terms == ["FLT3"]


def test_no_client_fails_safe():
    report = ClinicalTrialsAgent().run(_case())
    assert report.status == "source_unavailable"
    assert report.can_support_trial_match_claim is False
    assert report.can_support_eligibility_claim is False


def test_active_matching_trial_is_possible_match_not_eligibility():
    client = StubClient([_record()])
    report = ClinicalTrialsAgent(client).run(_case())
    assert report.status == "completed_with_limitations"
    assert len(report.matches) == 1
    assert report.matches[0].eligibility_determined is False
    assert report.matches[0].eligible is None
    assert report.can_support_trial_match_claim is True
    assert report.can_support_eligibility_claim is False


def test_nonrecruiting_record_does_not_become_match():
    report = ClinicalTrialsAgent(StubClient([_record(status="COMPLETED")])).run(_case())
    assert report.status == "no_evidence_found"
    assert report.matches == []
    assert report.can_support_trial_match_claim is False


def test_disease_context_mismatch_does_not_match():
    report = ClinicalTrialsAgent(StubClient([_record(condition="Multiple myeloma", title="Myeloma study")])).run(_case())
    assert report.status == "no_evidence_found"
    assert report.matches == []


def test_no_results_does_not_claim_absence_of_trials():
    report = ClinicalTrialsAgent(StubClient([])).run(_case())
    assert report.status == "no_evidence_found"
    assert "does not establish" in report.limitations[0].lower()


def test_repeat_is_deterministic():
    agent = ClinicalTrialsAgent(StubClient([_record()]))
    a = agent.run(_case()).model_dump(mode="json")
    b = agent.run(_case()).model_dump(mode="json")
    assert a == b


def test_api_v2_parser_extracts_core_fields():
    raw = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT12345678", "briefTitle": "AML Trial"},
            "statusModule": {"overallStatus": "RECRUITING", "lastUpdatePostDateStruct": {"date": "2026-08-01"}},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE2"]},
            "conditionsModule": {"conditions": ["Acute Myeloid Leukemia"]},
            "armsInterventionsModule": {"interventions": [{"name": "Drug A"}]},
            "eligibilityModule": {"eligibilityCriteria": "Example criteria", "minimumAge": "18 Years", "sex": "ALL"},
            "contactsLocationsModule": {"locations": [{"facility": "Example Center", "city": "New Orleans", "state": "Louisiana", "country": "United States"}]},
        }
    }
    record = parse_study(raw)
    assert record is not None
    assert record.nct_id == "NCT12345678"
    assert record.overall_status == "RECRUITING"
    assert record.phases == ["PHASE2"]
    assert record.interventions == ["Drug A"]
    assert record.locations[0].state == "Louisiana"
