from services.document_parser import parse_text
from services.extraction_hardening_v25 import classify_missing_information, harden_extraction_v25
from services.semantic_integrity_v25 import inspect_raw_semantic_integrity_v25


def test_molecular_missing_information_ontology():
    for field in ("FLT3 mutation testing", "NPM1 mutation testing", "cytogenetic testing", "FISH", "molecular sequencing"):
        assert classify_missing_information({"field": field, "reason": "result pending"}) == "molecular"


def test_primary_site_maps_to_diagnostic_clarification():
    assert classify_missing_information({"field": "primary site", "reason": "primary tumor site remains unknown"}) == "diagnostic_clarification"


def test_pathology_and_ecog_categories():
    assert classify_missing_information({"field": "bone biopsy", "reason": "pending"}) == "pathology"
    assert classify_missing_information({"field": "ECOG performance status", "reason": "not documented"}) == "performance_status"


def test_semantic_treatment_deduplication_same_source_event():
    doc = parse_text(
        "The patient received daratumumab-RVd induction, then transplant. At progression he started carfilzomib plus pomalidomide plus dexamethasone.",
        document_id="T", filename="t.txt"
    )
    payload = {
        "treatments": [
            {"regimen":"daratumumab-RVd induction","treatment_status":"unknown","agents":["daratumumab","lenalidomide","bortezomib","dexamethasone"],"source_segment_ids":["S0001"],"source_excerpt":"daratumumab-RVd induction","confidence":1.0},
            {"regimen":"daratumumab-RVd induction","treatment_status":"started","agents":["daratumumab-RVd"],"source_segment_ids":["S0001"],"source_excerpt":"received daratumumab-RVd induction","confidence":0.99},
            {"regimen":"carfilzomib/pomalidomide/dexamethasone","treatment_status":"unknown","agents":["carfilzomib","pomalidomide","dexamethasone"],"source_segment_ids":["S0001"],"source_excerpt":"carfilzomib plus pomalidomide plus dexamethasone","confidence":1.0},
            {"regimen":"carfilzomib plus pomalidomide plus dexamethasone","treatment_status":"started","agents":["carfilzomib","pomalidomide","dexamethasone"],"source_segment_ids":["S0001"],"source_excerpt":"started carfilzomib plus pomalidomide plus dexamethasone","confidence":0.99},
        ],
        "missing_items": [],
    }
    result = harden_extraction_v25(document=doc, payload=payload)
    assert result.duplicate_treatments_removed == 2
    assert len(result.payload["treatments"]) == 2
    assert all(t.get("treatment_status") == "started" for t in result.payload["treatments"])


def test_distinct_phases_are_not_deduplicated():
    doc = parse_text("She received lenalidomide induction and later lenalidomide maintenance.", document_id="T", filename="t.txt")
    payload = {"treatments":[
        {"regimen":"lenalidomide induction","treatment_status":"started","agents":["lenalidomide"],"source_segment_ids":["S0001"],"source_excerpt":"lenalidomide induction"},
        {"regimen":"lenalidomide maintenance","treatment_status":"started","agents":["lenalidomide"],"source_segment_ids":["S0001"],"source_excerpt":"lenalidomide maintenance"},
    ],"missing_items":[]}
    result = harden_extraction_v25(document=doc, payload=payload)
    assert result.duplicate_treatments_removed == 0
    assert len(result.payload["treatments"]) == 2


def test_hardening_is_idempotent():
    doc = parse_text("FLT3 testing is pending.", document_id="T", filename="t.txt")
    payload = {"treatments":[],"missing_items":[{"field":"FLT3 testing","reason":"pending","category":"treatment_history"}]}
    first = harden_extraction_v25(document=doc, payload=payload)
    second = harden_extraction_v25(document=doc, payload=first.payload)
    assert first.payload == second.payload
    assert second.duplicate_treatments_removed == 0
    assert second.missing_categories_reclassified == 0


def test_semantic_integrity_flags_duplicate_episode_and_category_mismatch():
    raw = {
        "treatments":[
            {"regimen":"daratumumab-RVd induction","agents":["daratumumab","lenalidomide","bortezomib","dexamethasone"],"source_segment_ids":["S0001"],"source_excerpt":"daratumumab-RVd induction"},
            {"regimen":"daratumumab-RVd induction","agents":["daratumumab-RVd"],"source_segment_ids":["S0001"],"source_excerpt":"received daratumumab-RVd induction"},
        ],
        "missing_items":[{"field":"NPM1 mutation testing","reason":"pending","category":"treatment_history"}],
    }
    codes = {f.code for f in inspect_raw_semantic_integrity_v25(raw)}
    assert "DUPLICATE_TREATMENT_EPISODE" in codes
    assert "MISSING_INFORMATION_CATEGORY_MISMATCH" in codes
