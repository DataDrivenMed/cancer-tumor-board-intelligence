from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

from agents.guideline import GuidelineEvidenceStore
from schemas.case import CancerTumorBoardCase
from services import fda_label_adapter
from services.civic_molecular_adapter import CIViCMolecularClient
from services.evidence_commissioning import collect_safety_candidates


ROOT = Path(__file__).resolve().parents[1]


def test_civic_query_does_not_request_brittle_variant_hgvs_field():
    captured = {}

    def transport(url, payload, headers, timeout):
        body = json.loads(payload.decode("utf-8"))
        captured["query"] = body["query"]
        return json.dumps({
            "data": {
                "evidenceItems": {
                    "totalCount": 1,
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [
                        {
                            "id": 123,
                            "status": "ACCEPTED",
                            "name": "FLT3 ITD predictive evidence",
                            "significance": "SENSITIVITYRESPONSE",
                            "evidenceType": "PREDICTIVE",
                            "evidenceLevel": "B",
                            "evidenceRating": 5,
                            "evidenceDirection": "SUPPORTS",
                            "description": "FLT3-ITD was associated with response in the represented study context.",
                            "molecularProfile": {"id": 10, "name": "FLT3 ITD"},
                            "disease": {
                                "id": 20,
                                "doid": "DOID:9119",
                                "name": "acute myeloid leukemia",
                                "displayName": "Acute Myeloid Leukemia",
                                "diseaseAliases": ["AML"],
                            },
                            "therapies": [{"id": 30, "name": "gilteritinib", "ncitId": None, "therapyAliases": []}],
                            "source": {"citationId": "12345678", "sourceType": "PUBMED", "title": "Synthetic source title", "pmcId": None, "ascoAbstractId": None},
                        }
                    ],
                }
            }
        }).encode("utf-8")

    result = CIViCMolecularClient(transport=transport).fetch(
        gene="FLT3",
        alteration="ITD",
        disease="Acute myeloid leukemia",
    )
    assert "variantHgvs" not in captured["query"]
    assert len(result.records) == 1
    assert result.records[0].gene == "FLT3"
    assert "FLT3 ITD" in result.records[0].alteration_terms


def test_openfda_404_is_normalized_to_empty_results(monkeypatch):
    def not_found(*args, **kwargs):
        raise HTTPError("https://api.fda.gov/drug/label.json", 404, "Not Found", hdrs=None, fp=None)

    monkeypatch.setattr(fda_label_adapter, "urlopen", not_found)
    payload = json.loads(fda_label_adapter._http_get("https://api.fda.gov/drug/label.json?search=x", 1).decode("utf-8"))
    assert payload == {"results": []}


def test_synthetic_placeholder_agents_are_not_sent_to_openfda(monkeypatch):
    payload = json.loads((ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))
    case = CancerTumorBoardCase.model_validate(payload)
    calls = []

    def fake_fetch(self, *, therapy, limit=5, accessed_date=None):
        calls.append(therapy)
        return []

    monkeypatch.setattr("services.evidence_commissioning.FDALabelClient.fetch_sections", fake_fetch)
    candidates, therapies, warnings = collect_safety_candidates(case, GuidelineEvidenceStore())
    assert candidates == ()
    assert therapies == ()
    assert warnings == ()
    assert calls == []
