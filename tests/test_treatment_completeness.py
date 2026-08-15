from services.document_parser import parse_text
from services.treatment_completeness import merge_treatment_candidates


def _episode(regimen, excerpt, status=None):
    item = {
        "regimen": regimen,
        "intent": None,
        "line_of_therapy": None,
        "start_date": None,
        "end_date": None,
        "agents": [],
        "reason_stopped": None,
        "best_response": None,
        "toxicities": [],
        "confidence": 1.0,
        "source_segment_ids": ["S0001"],
        "source_excerpt": excerpt,
    }
    if status is not None:
        item["treatment_status"] = status
    return item


def test_adds_missing_intermediate_maintenance_episode_and_restores_source_order():
    text = (
        "He received VRd induction in 2021, then lenalidomide maintenance. "
        "At first relapse in 2024, he received daratumumab, bortezomib and dexamethasone. "
        "At progression in 2026 he started carfilzomib, pomalidomide and dexamethasone."
    )
    doc = parse_text(text)
    payload = {
        "treatments": [
            _episode("VRd induction", "received VRd induction in 2021", "started"),
            _episode(
                "daratumumab, bortezomib and dexamethasone",
                "received daratumumab, bortezomib and dexamethasone",
                "started",
            ),
            _episode(
                "carfilzomib, pomalidomide and dexamethasone",
                "started carfilzomib, pomalidomide and dexamethasone",
                "started",
            ),
        ],
        "extraction_warnings": [],
    }
    candidates = [
        _episode("lenalidomide maintenance", "lenalidomide maintenance", "started")
    ]
    result = merge_treatment_candidates(document=doc, payload=payload, candidates=candidates)
    regimens = [item["regimen"] for item in result.payload["treatments"]]
    assert regimens == [
        "VRd induction",
        "lenalidomide maintenance",
        "daratumumab, bortezomib and dexamethasone",
        "carfilzomib, pomalidomide and dexamethasone",
    ]
    assert result.added_count == 1
    assert len(result.events) == 1


def test_does_not_merge_planned_not_started_therapy():
    doc = parse_text("Pembrolizumab has been recommended but has not yet started.")
    payload = {"treatments": [], "extraction_warnings": []}
    candidates = [
        _episode(
            "pembrolizumab",
            "Pembrolizumab has been recommended but has not yet started",
            "planned",
        )
    ]
    result = merge_treatment_candidates(document=doc, payload=payload, candidates=candidates)
    assert result.payload["treatments"] == []
    assert result.added_count == 0


def test_rejects_candidate_without_exact_source_provenance():
    doc = parse_text("He received FOLFOX.")
    payload = {"treatments": [], "extraction_warnings": []}
    candidates = [_episode("FOLFIRI", "He received FOLFIRI.", "started")]
    result = merge_treatment_candidates(document=doc, payload=payload, candidates=candidates)
    assert result.payload["treatments"] == []
    assert result.added_count == 0
    assert any("provenance verification failed" in warning for warning in result.warnings)
