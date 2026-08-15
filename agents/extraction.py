from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from schemas.case import (
    CancerTumorBoardCase,
    ClinicalQuestion,
    Conflict,
    DataStatus,
    Fact,
    InformationType,
    MissingItem,
    MolecularFinding,
    Provenance,
    TreatmentEpisode,
)
from services.conflict_consistency import recover_explicit_conflicts
from services.document_parser import ParsedDocument
from services.model_gateway import structured_json_response


STATUS_VALUES = [
    "confirmed",
    "unknown",
    "not_documented",
    "not_assessed",
    "pending",
    "not_applicable",
    "conflicting",
    "unavailable",
]


_PLACEHOLDER_VALUES = {
    "",
    "unknown",
    "not documented",
    "not_documented",
    "pending",
    "unavailable",
    "not assessed",
    "not_assessed",
    "not applicable",
    "not_applicable",
}


def _nullable_string() -> dict[str, Any]:
    return {"type": ["string", "null"]}


def _nullable_number() -> dict[str, Any]:
    return {"type": ["number", "null"]}


def _fact_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["field", "value", "status", "confidence", "source_segment_ids", "source_excerpt"],
        "properties": {
            "field": {"type": "string"},
            "value": _nullable_string(),
            "status": {"type": "string", "enum": STATUS_VALUES},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "source_segment_ids": {"type": "array", "items": {"type": "string"}},
            "source_excerpt": _nullable_string(),
        },
    }


def _molecular_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "gene",
            "alteration_type",
            "hgvs_c",
            "hgvs_p",
            "variant_allele_frequency",
            "specimen_type",
            "assay",
            "laboratory_interpretation",
            "confidence",
            "source_segment_ids",
            "source_excerpt",
        ],
        "properties": {
            "gene": {"type": "string"},
            "alteration_type": _nullable_string(),
            "hgvs_c": _nullable_string(),
            "hgvs_p": _nullable_string(),
            "variant_allele_frequency": _nullable_number(),
            "specimen_type": _nullable_string(),
            "assay": _nullable_string(),
            "laboratory_interpretation": _nullable_string(),
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "source_segment_ids": {"type": "array", "items": {"type": "string"}},
            "source_excerpt": _nullable_string(),
        },
    }


def _treatment_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "regimen",
            "intent",
            "line_of_therapy",
            "start_date",
            "end_date",
            "agents",
            "reason_stopped",
            "best_response",
            "toxicities",
            "confidence",
            "source_segment_ids",
            "source_excerpt",
        ],
        "properties": {
            "regimen": {"type": "string"},
            "intent": _nullable_string(),
            "line_of_therapy": {"type": ["integer", "null"]},
            "start_date": _nullable_string(),
            "end_date": _nullable_string(),
            "agents": {"type": "array", "items": {"type": "string"}},
            "reason_stopped": _nullable_string(),
            "best_response": _nullable_string(),
            "toxicities": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "source_segment_ids": {"type": "array", "items": {"type": "string"}},
            "source_excerpt": _nullable_string(),
        },
    }


EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "age",
        "sex",
        "care_site",
        "diagnosis",
        "disease_state",
        "performance_status",
        "pathology",
        "molecular_findings",
        "imaging",
        "labs",
        "comorbidities",
        "treatments",
        "toxicities",
        "transplant_cellular_therapy",
        "current_medications",
        "clinical_question",
        "conflicts",
        "missing_items",
        "extraction_warnings",
    ],
    "properties": {
        "age": {"type": ["integer", "null"], "minimum": 0, "maximum": 130},
        "sex": _nullable_string(),
        "care_site": _nullable_string(),
        "diagnosis": _fact_schema(),
        "disease_state": _fact_schema(),
        "performance_status": _fact_schema(),
        "pathology": {"type": "array", "items": _fact_schema()},
        "molecular_findings": {"type": "array", "items": _molecular_schema()},
        "imaging": {"type": "array", "items": _fact_schema()},
        "labs": {"type": "array", "items": _fact_schema()},
        "comorbidities": {"type": "array", "items": _fact_schema()},
        "treatments": {"type": "array", "items": _treatment_schema()},
        "toxicities": {"type": "array", "items": _fact_schema()},
        "transplant_cellular_therapy": {"type": "array", "items": _fact_schema()},
        "current_medications": {"type": "array", "items": _fact_schema()},
        "clinical_question": {
            "type": "object",
            "additionalProperties": False,
            "required": ["question_type", "question", "urgency"],
            "properties": {
                "question_type": {"type": "string"},
                "question": {"type": "string"},
                "urgency": {"type": "string"},
            },
        },
        "conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "value_a", "value_b", "severity", "source_segment_ids"],
                "properties": {
                    "field": {"type": "string"},
                    "value_a": {"type": "string"},
                    "value_b": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "moderate", "high", "critical"]},
                    "source_segment_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "missing_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "importance", "reason", "availability", "recommendation_blocking"],
                "properties": {
                    "field": {"type": "string"},
                    "importance": {"type": "string", "enum": ["low", "moderate", "high", "critical"]},
                    "reason": {"type": "string"},
                    "availability": {"type": "string"},
                    "recommendation_blocking": {"type": "boolean"},
                },
            },
        },
        "extraction_warnings": {"type": "array", "items": {"type": "string"}},
    },
}


SYSTEM_INSTRUCTIONS = """You are a bounded clinical data extraction service for a cancer tumor-board research prototype.

Your task is extraction, not diagnosis or treatment recommendation.

Rules:
1. Extract only information explicitly supported by the supplied source segments.
2. Never infer an undocumented diagnosis, stage, disease state, treatment response, ECOG score, molecular alteration, laboratory value, medication, or clinical question as fact.
3. If a fact is absent, use status not_documented, unknown, pending, unavailable, not_assessed, or not_applicable as appropriate. Do not invent a value.
4. Preserve contradictions. Do not choose between conflicting source statements.
5. For every substantive non-null patient fact, regardless of whether its status is confirmed, conflicting, unknown, pending, or another uncertainty status, return one or more exact source_segment_ids and a short verbatim source_excerpt copied from those segments. Null/placeholder facts do not need provenance.
6. The source_excerpt must be an exact substring of the cited source segment text. Do not paraphrase inside source_excerpt.
7. Molecular findings must preserve the reported gene, alteration type, HGVS notation, VAF, specimen type, assay, and laboratory interpretation when present. Do not label an alteration clinically actionable.
8. Treatment episodes must preserve chronology, line of therapy only when documented or unambiguous from explicit sequencing, response, reason stopped, and toxicities. If line is not clear, return null.
9. Do not turn biological plausibility into clinical significance.
10. Do not use outside medical knowledge to fill missing patient facts.
11. Clinical question extraction should reflect the question explicitly asked in the source. If no question is stated, use question_type 'unspecified' and question 'Not explicitly documented'.
12. Confidence represents extraction confidence only, not clinical certainty.
13. Every decision-relevant result or fact that is explicitly pending, unavailable, not documented, not assessed, or otherwise unresolved must also appear in missing_items, even if its status is represented elsewhere in the structured case.
14. For an explicitly pending test, create a missing_items entry naming that test, set availability to 'pending', explain that the result is not yet available, and set recommendation_blocking according to whether the source indicates or the clinical question makes clear that the pending result could affect the decision. Never convert a pending test into a positive or negative result.
15. Before finalizing the JSON, perform a completeness audit of the source for the words or concepts pending, unavailable, not documented, not assessed, awaiting, sent, ordered, and not yet resulted. Ensure every decision-relevant unresolved item is represented in missing_items without inventing information.
16. Preserve explicit current disease-state qualifiers. If the source directly states that the current malignancy is newly diagnosed, relapsed, recurrent, refractory, progressive/progressing, in remission, or another explicit temporal disease state, populate disease_state with that supported wording and exact provenance. Do not drop a disease-state phrase merely because it appears adjacent to the diagnosis. Distinguish current-state qualifiers from remote historical conditions.
17. source_segment_ids must contain only the exact authoritative segment ID token shown in the first bracket, for example S0001. Never append page, paragraph, locator, punctuation, or other metadata to the segment ID.
18. A missing-information entry does not substitute for a conflict. If two available source statements disagree about the same clinical field, especially diagnosis, disease stage, pathology interpretation, biomarker status, or treatment response, populate conflicts with both source-supported values and keep the discrepancy unresolved. If the conflict is also decision-blocking, it may additionally appear in missing_items as something requiring resolution.
"""


@dataclass
class ExtractionPackage:
    case: CancerTumorBoardCase
    raw_extraction: dict[str, Any]
    provenance_total: int
    provenance_verified: int
    provenance_failures: list[str]
    warnings: list[str]

    @property
    def provenance_rate(self) -> float:
        if self.provenance_total == 0:
            return 0.0
        return self.provenance_verified / self.provenance_total


def _normalize(text: str | None) -> str:
    return " ".join((text or "").split()).strip()


def _is_substantive_value(value: str | None) -> bool:
    if value is None:
        return False
    normalized = _normalize(value).lower().replace("_", " ")
    return normalized not in {item.replace("_", " ") for item in _PLACEHOLDER_VALUES}


def _verified_provenance(
    document: ParsedDocument,
    source_segment_ids: list[str],
    source_excerpt: str | None,
) -> tuple[Provenance, bool]:
    segment_map = {segment.segment_id: segment for segment in document.segments}
    valid_segments = [segment_map[sid] for sid in source_segment_ids if sid in segment_map]
    ids_valid = bool(source_segment_ids) and len(valid_segments) == len(source_segment_ids)

    excerpt = _normalize(source_excerpt)
    excerpt_valid = False
    if excerpt and valid_segments:
        excerpt_valid = any(excerpt in _normalize(segment.text) for segment in valid_segments)

    verified = ids_valid and excerpt_valid
    page = valid_segments[0].page if valid_segments else None

    provenance = Provenance(
        document_id=document.document_id,
        document_type=document.document_type,
        source_section=None,
        source_excerpt=source_excerpt,
        source_segment_ids=source_segment_ids,
        source_verified=verified,
        page=page,
    )
    return provenance, verified


def _fact_requires_verified_provenance(fact: Fact) -> bool:
    return _is_substantive_value(fact.value)


def _to_fact(item: dict[str, Any], document: ParsedDocument, failures: list[str]) -> Fact:
    status = DataStatus(item["status"])
    provenance: list[Provenance] = []
    verified = False

    if item.get("source_segment_ids") or item.get("source_excerpt"):
        prov, verified = _verified_provenance(
            document,
            item.get("source_segment_ids", []),
            item.get("source_excerpt"),
        )
        provenance.append(prov)

    confidence = float(item.get("confidence", 0.0))
    if _is_substantive_value(item.get("value")) and not verified:
        confidence = min(confidence, 0.50)
        failures.append(item.get("field", "unknown_field"))

    return Fact(
        field=item["field"],
        value=item.get("value"),
        status=status,
        information_type=InformationType.OBSERVED,
        provenance=provenance,
        confidence=confidence,
        human_verified=False,
    )


def _safe_date(value: str | None):
    if not value:
        return None
    try:
        from datetime import date

        return date.fromisoformat(value)
    except Exception:
        return None


def extract_case(
    *,
    document: ParsedDocument,
    api_key: str,
    model: str = "gpt-5",
    case_id: str = "EXTRACTED-001",
) -> ExtractionPackage:
    if not document.segments:
        raise ValueError("The document contains no extractable text segments.")

    user_input = (
        "Extract the tumor-board case from the source below. Segment identifiers are authoritative provenance anchors. "
        "For source_segment_ids copy only the exact segment token in the first bracket, such as S0001; never include page/paragraph locator metadata. "
        "Preserve any explicit current disease-state wording such as newly diagnosed, relapsed, recurrent, refractory, progressive, or remission in disease_state with exact provenance. "
        "Before returning JSON, audit all explicitly pending, unavailable, not documented, not assessed, awaiting, ordered, sent, or not-yet-resulted decision-relevant items and include each in missing_items with the correct availability. "
        "Then audit contradictions separately: if two available source statements disagree on the same field, create a structured conflicts entry; a missing_items entry alone is not sufficient.\n\n"
        + document.numbered_text()
    )

    raw = structured_json_response(
        api_key=api_key,
        model=model,
        system_instructions=SYSTEM_INSTRUCTIONS,
        user_input=user_input,
        schema_name="tumor_board_case_extraction",
        json_schema=EXTRACTION_SCHEMA,
    )

    failures: list[str] = []
    warnings = list(raw.get("extraction_warnings", []))

    consistency = recover_explicit_conflicts(
        document=document,
        conflicts=raw.get("conflicts", []),
        missing_items=raw.get("missing_items", []),
    )
    raw["conflicts"] = consistency.conflicts
    warnings.extend(consistency.warnings)
    if consistency.warnings:
        raw.setdefault("extraction_warnings", []).extend(consistency.warnings)

    diagnosis = _to_fact(raw["diagnosis"], document, failures)
    disease_state = _to_fact(raw["disease_state"], document, failures)
    performance_status = _to_fact(raw["performance_status"], document, failures)

    def facts(key: str) -> list[Fact]:
        return [_to_fact(item, document, failures) for item in raw.get(key, [])]

    molecular: list[MolecularFinding] = []
    for item in raw.get("molecular_findings", []):
        prov, verified = _verified_provenance(
            document,
            item.get("source_segment_ids", []),
            item.get("source_excerpt"),
        )
        if not verified:
            failures.append(f"molecular:{item.get('gene', 'unknown')}")
        molecular.append(
            MolecularFinding(
                gene=item["gene"],
                alteration_type=item.get("alteration_type"),
                hgvs_c=item.get("hgvs_c"),
                hgvs_p=item.get("hgvs_p"),
                variant_allele_frequency=item.get("variant_allele_frequency"),
                specimen_type=item.get("specimen_type"),
                assay=item.get("assay"),
                laboratory_interpretation=item.get("laboratory_interpretation"),
                provenance=[prov],
                human_verified=False,
            )
        )

    treatments: list[TreatmentEpisode] = []
    for idx, item in enumerate(raw.get("treatments", []), start=1):
        prov, verified = _verified_provenance(
            document,
            item.get("source_segment_ids", []),
            item.get("source_excerpt"),
        )
        if not verified:
            failures.append(f"treatment:{item.get('regimen', idx)}")
        treatments.append(
            TreatmentEpisode(
                episode_id=f"TX-{idx:03d}",
                regimen=item["regimen"],
                intent=item.get("intent"),
                line_of_therapy=item.get("line_of_therapy"),
                start_date=_safe_date(item.get("start_date")),
                end_date=_safe_date(item.get("end_date")),
                agents=item.get("agents", []),
                reason_stopped=item.get("reason_stopped"),
                best_response=item.get("best_response"),
                toxicities=item.get("toxicities", []),
                provenance=[prov],
                human_verified=False,
            )
        )

    conflicts = [
        Conflict(
            conflict_id=f"CON-{idx:03d}",
            field=item["field"],
            value_a=item["value_a"],
            value_b=item["value_b"],
            severity=item["severity"],
            resolution_status="unresolved",
            source_segment_ids=item.get("source_segment_ids", []),
        )
        for idx, item in enumerate(raw.get("conflicts", []), start=1)
    ]

    missing = [
        MissingItem(
            field=item["field"],
            importance=item["importance"],
            reason=item["reason"],
            availability=item["availability"],
            recommendation_blocking=item["recommendation_blocking"],
        )
        for item in raw.get("missing_items", [])
    ]

    case = CancerTumorBoardCase(
        case_id=case_id,
        case_type="synthetic",
        care_site=raw.get("care_site"),
        age=raw.get("age"),
        sex=raw.get("sex"),
        diagnosis=diagnosis,
        disease_state=disease_state,
        performance_status=performance_status,
        pathology=facts("pathology"),
        molecular_findings=molecular,
        imaging=facts("imaging"),
        labs=facts("labs"),
        comorbidities=facts("comorbidities"),
        treatments=treatments,
        toxicities=facts("toxicities"),
        transplant_cellular_therapy=facts("transplant_cellular_therapy"),
        current_medications=facts("current_medications"),
        clinical_question=ClinicalQuestion(**raw["clinical_question"]),
        conflicts=conflicts,
        missing_items=missing,
        source_documents=[document.document_id],
    )

    provenance_objects: list[Provenance] = []
    for fact in [diagnosis, disease_state, performance_status, *case.pathology, *case.imaging, *case.labs, *case.comorbidities, *case.toxicities, *case.transplant_cellular_therapy, *case.current_medications]:
        if fact is not None and _fact_requires_verified_provenance(fact):
            provenance_objects.extend(fact.provenance)
    for item in case.molecular_findings:
        provenance_objects.extend(item.provenance)
    for item in case.treatments:
        provenance_objects.extend(item.provenance)

    total = len(provenance_objects)
    verified = sum(1 for p in provenance_objects if p.source_verified)

    if failures:
        warnings.append(
            "One or more extracted substantive assertions failed exact provenance verification and were automatically confidence-capped at 0.50 where applicable."
        )

    return ExtractionPackage(
        case=case,
        raw_extraction=raw,
        provenance_total=total,
        provenance_verified=verified,
        provenance_failures=sorted(set(failures)),
        warnings=warnings,
    )
