from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from agents.extraction import (
    EXTRACTION_SCHEMA,
    SYSTEM_INSTRUCTIONS,
    _fact_requires_verified_provenance,
    _is_substantive_value,
    _safe_date,
    _verified_provenance,
)
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
    TreatmentStatus,
)
from services.conflict_consistency import recover_explicit_conflicts
from services.disease_state_resolver import resolve_disease_state
from services.document_parser import ParsedDocument
from services.extraction_audit import NormalizationEvent, make_normalization_event, serialize_events
from services.model_gateway import ModelGatewayError, structured_json_response_raw
from services.normalization_pipeline import normalize_primary_extraction
from services.treatment_completeness import (
    extract_treatment_candidates,
    merge_treatment_candidates,
    needs_treatment_completeness_pass,
)


EXTRACTION_V21_VERSION = "2.1.0"


@dataclass
class ExtractionPackageV21:
    case: CancerTumorBoardCase
    raw_model_output: dict[str, Any]
    normalized_extraction: dict[str, Any]
    normalization_events: list[dict[str, Any]]
    raw_extraction: dict[str, Any]
    provenance_total: int
    provenance_verified: int
    provenance_failures: list[str]
    warnings: list[str]
    treatment_completeness_performed: bool = False
    treatment_candidates_found: int = 0
    treatment_episodes_added: int = 0
    extraction_version: str = EXTRACTION_V21_VERSION

    @property
    def provenance_rate(self) -> float:
        if self.provenance_total == 0:
            return 0.0
        return self.provenance_verified / self.provenance_total


def _information_type(item: dict[str, Any]) -> InformationType:
    value = str(item.get("information_type") or "observed").lower()
    try:
        return InformationType(value)
    except ValueError:
        return InformationType.OBSERVED


def _to_fact_v21(item: dict[str, Any], document: ParsedDocument, failures: list[str]) -> Fact:
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
        information_type=_information_type(item),
        provenance=provenance,
        confidence=confidence,
        human_verified=False,
    )


def _treatment_status(item: dict[str, Any]) -> TreatmentStatus:
    explicit = str(item.get("treatment_status") or "").lower()
    if explicit:
        try:
            return TreatmentStatus(explicit)
        except ValueError:
            pass

    excerpt = " ".join(str(item.get("source_excerpt") or "").lower().split())
    if any(term in excerpt for term in ("not yet started", "not started", "recommended", "planned")):
        return TreatmentStatus.PLANNED
    if "ordered" in excerpt:
        return TreatmentStatus.ORDERED
    if any(term in excerpt for term in ("stopped", "discontinued")):
        return TreatmentStatus.STOPPED
    if any(term in excerpt for term in ("completed", "finished")):
        return TreatmentStatus.COMPLETED
    if any(term in excerpt for term in ("received", "started", "initiated", "underwent", "now receiving", "currently receiving")):
        return TreatmentStatus.STARTED
    return TreatmentStatus.UNKNOWN


def extract_case_v21(
    *,
    document: ParsedDocument,
    api_key: str,
    model: str = "openai/gpt-oss-120b:fireworks-ai",
    case_id: str = "EXTRACTED-001",
) -> ExtractionPackageV21:
    """Extraction v2.1 with explicit raw/normalized audit layers and bounded repairs."""

    if not document.segments:
        raise ValueError("The document contains no extractable text segments.")

    user_input = (
        "Extract the tumor-board case from the source below. Segment identifiers are authoritative provenance anchors. "
        "For source_segment_ids copy only the exact segment token in the first bracket, such as S0001; never include page/paragraph locator metadata. "
        "Preserve any explicit current disease-state wording such as newly diagnosed, relapsed, recurrent, refractory, progressive, persistent, metastatic, or remission in disease_state with exact provenance. "
        "Preserve every explicit administered treatment phase in chronological order, including induction, consolidation, maintenance, salvage, transplant, cellular therapy, and later regimens. "
        "Before returning JSON, audit all explicitly pending, unavailable, not documented, not assessed, awaiting, ordered, sent, or not-yet-resulted decision-relevant items and include each in missing_items with the correct availability. "
        "Then audit contradictions separately: if two available source statements disagree on the same field, create a structured conflicts entry; a missing_items entry alone is not sufficient.\n\n"
        + document.numbered_text()
    )

    raw_model_output = structured_json_response_raw(
        api_key=api_key,
        model=model,
        system_instructions=SYSTEM_INSTRUCTIONS,
        user_input=user_input,
        schema_name="tumor_board_case_extraction",
        json_schema=EXTRACTION_SCHEMA,
    )
    immutable_raw = deepcopy(raw_model_output)

    normalized, normalization_events = normalize_primary_extraction(immutable_raw)
    warnings = list(normalized.get("extraction_warnings", []) or [])

    before_conflicts = deepcopy(normalized.get("conflicts", []))
    consistency = recover_explicit_conflicts(
        document=document,
        conflicts=normalized.get("conflicts", []),
        missing_items=normalized.get("missing_items", []),
    )
    normalized["conflicts"] = consistency.conflicts
    warnings.extend(consistency.warnings)
    if consistency.warnings:
        normalized.setdefault("extraction_warnings", [])
        for warning in consistency.warnings:
            if warning not in normalized["extraction_warnings"]:
                normalized["extraction_warnings"].append(warning)
    if before_conflicts != normalized.get("conflicts", []):
        normalization_events.append(
            make_normalization_event(
                rule="explicit_conflict_recovery",
                field_path="conflicts",
                before=before_conflicts,
                after=normalized.get("conflicts", []),
                reason="Deterministic source scan recovered an explicit unresolved conflict omitted by primary extraction.",
            )
        )

    disease_resolution = resolve_disease_state(document=document, payload=normalized)
    normalized = disease_resolution.payload
    normalization_events.extend(disease_resolution.events)
    warnings.extend(disease_resolution.warnings)

    treatment_completeness_performed = False
    treatment_candidates_found = 0
    treatment_episodes_added = 0
    if needs_treatment_completeness_pass(document):
        treatment_completeness_performed = True
        try:
            candidates = extract_treatment_candidates(
                document=document,
                api_key=api_key,
                model=model,
            )
            treatment_candidates_found = len(candidates)
            completeness = merge_treatment_candidates(
                document=document,
                payload=normalized,
                candidates=candidates,
            )
            normalized = completeness.payload
            normalization_events.extend(completeness.events)
            warnings.extend(completeness.warnings)
            treatment_episodes_added = completeness.added_count
        except ModelGatewayError as exc:
            warning = (
                "Treatment completeness second pass was unavailable; primary extraction was preserved without speculative repair: "
                + str(exc)
            )
            warnings.append(warning)
            normalized.setdefault("extraction_warnings", [])
            if warning not in normalized["extraction_warnings"]:
                normalized["extraction_warnings"].append(warning)

    failures: list[str] = []
    diagnosis = _to_fact_v21(normalized["diagnosis"], document, failures)
    disease_state = _to_fact_v21(normalized["disease_state"], document, failures)
    performance_status = _to_fact_v21(normalized["performance_status"], document, failures)

    def facts(key: str) -> list[Fact]:
        return [_to_fact_v21(item, document, failures) for item in normalized.get(key, [])]

    molecular: list[MolecularFinding] = []
    for item in normalized.get("molecular_findings", []):
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
    for idx, item in enumerate(normalized.get("treatments", []), start=1):
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
                treatment_status=_treatment_status(item),
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
        for idx, item in enumerate(normalized.get("conflicts", []), start=1)
    ]

    missing = [
        MissingItem(
            field=item["field"],
            importance=item["importance"],
            reason=item["reason"],
            availability=item["availability"],
            recommendation_blocking=item["recommendation_blocking"],
        )
        for item in normalized.get("missing_items", [])
    ]

    case = CancerTumorBoardCase(
        case_id=case_id,
        case_type="synthetic",
        care_site=normalized.get("care_site"),
        age=normalized.get("age"),
        sex=normalized.get("sex"),
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
        clinical_question=ClinicalQuestion(**normalized["clinical_question"]),
        conflicts=conflicts,
        missing_items=missing,
        source_documents=[document.document_id],
    )

    provenance_objects: list[Provenance] = []
    for fact in [
        diagnosis,
        disease_state,
        performance_status,
        *case.pathology,
        *case.imaging,
        *case.labs,
        *case.comorbidities,
        *case.toxicities,
        *case.transplant_cellular_therapy,
        *case.current_medications,
    ]:
        if fact is not None and _fact_requires_verified_provenance(fact):
            provenance_objects.extend(fact.provenance)
    for item in case.molecular_findings:
        provenance_objects.extend(item.provenance)
    for item in case.treatments:
        provenance_objects.extend(item.provenance)

    total = len(provenance_objects)
    verified = sum(1 for provenance in provenance_objects if provenance.source_verified)

    if failures:
        warning = (
            "One or more extracted substantive assertions failed exact provenance verification and were automatically confidence-capped at 0.50 where applicable."
        )
        warnings.append(warning)

    # Keep a compatibility alias for existing scoring/diagnostic code while the
    # explicit raw_model_output and normalized_extraction fields remove ambiguity.
    compatibility_raw_extraction = deepcopy(normalized)

    return ExtractionPackageV21(
        case=case,
        raw_model_output=deepcopy(immutable_raw),
        normalized_extraction=deepcopy(normalized),
        normalization_events=serialize_events(normalization_events),
        raw_extraction=compatibility_raw_extraction,
        provenance_total=total,
        provenance_verified=verified,
        provenance_failures=sorted(set(failures)),
        warnings=sorted(set(warnings)),
        treatment_completeness_performed=treatment_completeness_performed,
        treatment_candidates_found=treatment_candidates_found,
        treatment_episodes_added=treatment_episodes_added,
    )
