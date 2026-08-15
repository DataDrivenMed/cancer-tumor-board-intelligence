from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from agents.extraction import _fact_requires_verified_provenance, _safe_date, _verified_provenance
from agents.extraction_v21 import _to_fact_v21, _treatment_status
from agents.extraction_v24 import ExtractionPackageV24, extract_case_v24
from schemas.case import Provenance, TreatmentEpisode
from services.document_parser import ParsedDocument
from services.extraction_audit import serialize_events
from services.extraction_hardening_v25 import harden_extraction_v25


EXTRACTION_V25_VERSION = "2.5.0"


@dataclass
class ExtractionPackageV25:
    case: Any
    raw_model_output: dict[str, Any]
    normalized_extraction: dict[str, Any]
    normalization_events: list[dict[str, Any]]
    raw_extraction: dict[str, Any]
    provenance_total: int
    provenance_verified: int
    provenance_failures: list[str]
    warnings: list[str]
    diagnostic_certainty: str
    stage: dict[str, Any] | None
    treatment_completeness_performed: bool = False
    treatment_candidates_found: int = 0
    treatment_episodes_added: int = 0
    duplicate_treatments_removed: int = 0
    missing_categories_reclassified: int = 0
    extraction_version: str = EXTRACTION_V25_VERSION

    @property
    def provenance_rate(self) -> float:
        return self.provenance_verified / self.provenance_total if self.provenance_total else 0.0


def _recompute_provenance(case) -> tuple[int, int]:
    provenance_objects: list[Provenance] = []
    facts = [case.diagnosis, case.disease_state]
    if case.performance_status is not None:
        facts.append(case.performance_status)
    facts.extend(case.pathology)
    facts.extend(case.imaging)
    facts.extend(case.labs)
    facts.extend(case.comorbidities)
    facts.extend(case.toxicities)
    facts.extend(case.transplant_cellular_therapy)
    facts.extend(case.current_medications)
    for fact in facts:
        if fact is not None and _fact_requires_verified_provenance(fact):
            provenance_objects.extend(fact.provenance)
    for item in case.molecular_findings:
        provenance_objects.extend(item.provenance)
    for item in case.treatments:
        provenance_objects.extend(item.provenance)
    return len(provenance_objects), sum(1 for p in provenance_objects if p.source_verified)


def _rebuild_treatments(normalized: dict[str, Any], document: ParsedDocument, failures: list[str]) -> list[TreatmentEpisode]:
    out: list[TreatmentEpisode] = []
    for idx, item in enumerate(normalized.get("treatments", []) or [], start=1):
        prov, verified = _verified_provenance(
            document,
            item.get("source_segment_ids", []),
            item.get("source_excerpt"),
        )
        if not verified:
            failures.append(f"treatment:{item.get('regimen', idx)}")
        out.append(TreatmentEpisode(
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
        ))
    return out


def extract_case_v25(
    *,
    document: ParsedDocument,
    api_key: str,
    model: str = "openai/gpt-oss-120b:fireworks-ai",
    case_id: str = "EXTRACTED-001",
) -> ExtractionPackageV25:
    """Final pre-qualification hardening over v2.4.

    The v2.4 uncertainty/provenance architecture is preserved. v2.5 adds only
    deterministic treatment deduplication and missing-information ontology repair.
    """
    base: ExtractionPackageV24 = extract_case_v24(
        document=document,
        api_key=api_key,
        model=model,
        case_id=case_id,
    )
    hardened = harden_extraction_v25(document=document, payload=base.normalized_extraction)
    normalized = hardened.payload
    case = base.case.model_copy(deep=True)
    failures = list(base.provenance_failures)

    # v2.5 changes treatment representation, so rebuild the canonical treatment list
    # from the hardened normalized payload and recompute provenance from the final case.
    failures = [item for item in failures if not item.startswith("treatment:")]
    case.treatments = _rebuild_treatments(normalized, document, failures)

    total, verified = _recompute_provenance(case)
    events = list(base.normalization_events) + serialize_events(hardened.events)
    warnings = sorted(set(list(base.warnings) + list(hardened.warnings)))

    return ExtractionPackageV25(
        case=case,
        raw_model_output=deepcopy(base.raw_model_output),
        normalized_extraction=deepcopy(normalized),
        normalization_events=events,
        raw_extraction=deepcopy(normalized),
        provenance_total=total,
        provenance_verified=verified,
        provenance_failures=sorted(set(failures)),
        warnings=warnings,
        diagnostic_certainty=base.diagnostic_certainty,
        stage=deepcopy(base.stage),
        treatment_completeness_performed=base.treatment_completeness_performed,
        treatment_candidates_found=base.treatment_candidates_found,
        treatment_episodes_added=base.treatment_episodes_added,
        duplicate_treatments_removed=hardened.duplicate_treatments_removed,
        missing_categories_reclassified=hardened.missing_categories_reclassified,
    )
