from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from agents.extraction import _fact_requires_verified_provenance
from agents.extraction_v21 import ExtractionPackageV21, _to_fact_v21, extract_case_v21
from schemas.case import Provenance
from services.clinical_canonicalization_v22 import canonicalize_clinical_fields_v22
from services.document_parser import ParsedDocument
from services.extraction_audit import serialize_events


EXTRACTION_V22_VERSION = "2.2.0"


@dataclass
class ExtractionPackageV22:
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
    extraction_version: str = EXTRACTION_V22_VERSION

    @property
    def provenance_rate(self) -> float:
        if self.provenance_total == 0:
            return 0.0
        return self.provenance_verified / self.provenance_total


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

    return len(provenance_objects), sum(1 for item in provenance_objects if item.source_verified)


def extract_case_v22(
    *,
    document: ParsedDocument,
    api_key: str,
    model: str = "openai/gpt-oss-120b:fireworks-ai",
    case_id: str = "EXTRACTED-001",
) -> ExtractionPackageV22:
    """Extraction v2.2.

    v2.2 deliberately builds on the already-tested v2.1 extraction pipeline, then
    applies deterministic source-grounded canonicalization before final scoring.
    No external medical knowledge is introduced by this layer.
    """

    base: ExtractionPackageV21 = extract_case_v21(
        document=document,
        api_key=api_key,
        model=model,
        case_id=case_id,
    )

    canonical = canonicalize_clinical_fields_v22(
        document=document,
        payload=base.normalized_extraction,
    )
    normalized = canonical.payload
    case = base.case.model_copy(deep=True)
    failures = list(base.provenance_failures)

    # Rebuild only the canonical disease-state fact after deterministic repair.
    # Other v2.1 fields remain byte-for-byte behaviorally inherited.
    disease_failures: list[str] = []
    case.disease_state = _to_fact_v21(normalized["disease_state"], document, disease_failures)
    failures = [item for item in failures if item not in {"disease_state", "disease state"}]
    failures.extend(disease_failures)

    total, verified = _recompute_provenance(case)
    warnings = sorted(set(list(base.warnings) + list(canonical.warnings)))
    events = list(base.normalization_events) + serialize_events(canonical.events)

    return ExtractionPackageV22(
        case=case,
        raw_model_output=deepcopy(base.raw_model_output),
        normalized_extraction=deepcopy(normalized),
        normalization_events=events,
        raw_extraction=deepcopy(normalized),
        provenance_total=total,
        provenance_verified=verified,
        provenance_failures=sorted(set(failures)),
        warnings=warnings,
        diagnostic_certainty=canonical.diagnostic_certainty,
        stage=deepcopy(canonical.stage),
        treatment_completeness_performed=base.treatment_completeness_performed,
        treatment_candidates_found=base.treatment_candidates_found,
        treatment_episodes_added=base.treatment_episodes_added,
    )
