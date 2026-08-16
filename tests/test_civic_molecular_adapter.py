from __future__ import annotations

import json
from datetime import date

from schemas.molecular import ClinicalActionability, MolecularEvidenceDirection
from services.civic_molecular_adapter import CIViCMolecularClient, attest_civic_records


def test_civic_accepted_predictive_record_is_candidate_not_auto_admitted():
    payload = {
        "data": {
            "evidenceItems": {
                "totalCount": 1,
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {
                        "id": 123,
                        "status": "ACCEPTED",
                        "name": "EID123",
                        "significance": "SENSITIVITYRESPONSE",
                        "evidenceType": "PREDICTIVE",
                        "evidenceLevel": "A",
                        "evidenceRating": 5,
                        "evidenceDirection": "SUPPORTS",
                        "description": "Accepted curated evidence statement.",
                        "variantHgvs": "",
                        "molecularProfile": {"id": 1, "name": "FLT3 ITD"},
                        "disease": {
                            "id": 2,
                            "doid": "DOID:9119",
                            "name": "acute myeloid leukemia",
                            "displayName": "Acute Myeloid Leukemia",
                            "diseaseAliases": ["AML"],
                        },
                        "therapies": [
                            {"id": 3, "name": "example therapy", "ncitId": None, "therapyAliases": []}
                        ],
                        "source": {
                            "citationId": "12345678",
                            "sourceType": "PUBMED",
                            "title": "Example publication",
                            "pmcId": None,
                            "ascoAbstractId": None,
                        },
                    }
                ],
            }
        }
    }

    def transport(url, body, headers, timeout):
        assert url.startswith("https://civicdb.org/")
        request = json.loads(body.decode("utf-8"))
        assert request["variables"]["profile"] == "FLT3 ITD"
        assert request["variables"]["disease"] == "Acute myeloid leukemia"
        return json.dumps(payload).encode("utf-8")

    result = CIViCMolecularClient(transport=transport).fetch(
        gene="FLT3",
        alteration="ITD",
        disease="Acute myeloid leukemia",
        accessed_date=date(2026, 8, 16),
    )

    assert len(result.records) == 1
    record = result.records[0]
    assert record.evidence_id == "CIVIC-EID-123"
    assert record.source_verified is True
    assert record.human_verified is False
    assert record.direction == MolecularEvidenceDirection.SUPPORTS_SENSITIVITY
    assert record.actionability == ClinicalActionability.EMERGING
    assert record.therapy == "example therapy"

    store = attest_civic_records(result.records, verified_evidence_ids={"CIVIC-EID-123"})
    assert store.records[0].human_verified is True


def test_civic_graphql_errors_fail_closed():
    def transport(url, body, headers, timeout):
        return json.dumps({"errors": [{"message": "bad query"}]}).encode("utf-8")

    client = CIViCMolecularClient(transport=transport)
    try:
        client.fetch(gene="FLT3", alteration="ITD", disease="AML")
        assert False, "expected failure"
    except Exception as exc:
        assert "GraphQL returned errors" in str(exc)
