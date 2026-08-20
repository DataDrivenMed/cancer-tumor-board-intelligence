from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import json
import os
from typing import Any, Iterable, Literal

from agents.guideline import GuidelineAgent, GuidelineEvidenceStore
from schemas.case import CancerTumorBoardCase
from schemas.molecular import (
    ClinicalActionability,
    MolecularEvidenceDirection,
    MolecularEvidenceRecord,
    MolecularEvidenceTier,
)
from services.evidence_commissioning import (
    CommissioningCandidates,
    build_approved_molecular_store,
    build_approved_safety_store,
    collect_case_candidates,
    safety_candidate_excerpt,
)
from services.fda_label_adapter import FDALabelSectionCandidate
from services.runtime_agents import build_workflow_context, resolve_product_guideline_store


EvidenceMode = Literal["guided_fixture", "live"]


@dataclass(frozen=True)
class EvidenceCommissioningSnapshot:
    case_id: str
    mode: EvidenceMode
    guideline_store: GuidelineEvidenceStore
    molecular_records: tuple[MolecularEvidenceRecord, ...]
    safety_records: tuple[FDALabelSectionCandidate, ...]
    candidates: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...] = ()

    @property
    def candidate_set_id(self) -> str:
        payload = {
            "case_id": self.case_id,
            "mode": self.mode,
            "candidates": self.candidates,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return sha256(canonical.encode("utf-8")).hexdigest()


def _guided_candidates() -> CommissioningCandidates:
    molecular = MolecularEvidenceRecord(
        evidence_id="FIXTURE-CIVIC-FLT3-001",
        source_id="FIXTURE-CIVIC-FLT3-001",
        source_title="Controlled molecular evidence review fixture",
        source_url="https://civicdb.org/",
        source_type=MolecularEvidenceTier.SYNTHETIC,
        accessed_date=date(2026, 8, 19),
        disease_terms=["acute myeloid leukemia"],
        gene="FLT3",
        alteration_terms=["ITD"],
        direction=MolecularEvidenceDirection.SUPPORTS_SENSITIVITY,
        actionability=ClinicalActionability.INVESTIGATIONAL,
        therapy="synthetic therapy concept",
        evidence_summary=(
            "Controlled software fixture used to demonstrate molecular evidence review. "
            "It cannot support a production clinical actionability claim."
        ),
        source_excerpt="Controlled molecular evidence review fixture.",
        source_locator="Synthetic qualification record",
        source_verified=True,
        human_verified=False,
        synthetic=True,
    )
    safety = FDALabelSectionCandidate(
        therapy="synthetic therapy concept",
        spl_set_id="FIXTURE-SPL-001",
        spl_id="FIXTURE-SPL-ID-001",
        application_number=None,
        effective_time="20260819",
        section="warnings_and_cautions",
        text=(
            "Controlled safety evidence review fixture. This text is synthetic and must not be used "
            "as prescribing information or as evidence of patient-specific risk."
        ),
        source_url="https://api.fda.gov/drug/label.json",
        accessed_date=date(2026, 8, 19),
        synthetic=True,
    )
    return CommissioningCandidates(
        molecular_records=(molecular,),
        safety_records=(safety,),
        candidate_therapies=("synthetic therapy concept",),
        warnings=(
            "Molecular and safety candidates are controlled synthetic review fixtures. Production agents remain fail-closed for these records.",
        ),
    )


def _guideline_candidates(case: CancerTumorBoardCase, store: GuidelineEvidenceStore) -> list[dict[str, Any]]:
    report = GuidelineAgent(store).run(case)
    sources = {source.source_id: source for source in store.sources}
    out: list[dict[str, Any]] = []
    for match in report.matched_guidance:
        source = sources.get(match.source_id)
        out.append({
            "candidate_id": f"guideline:{match.recommendation_id}",
            "channel": "guideline",
            "title": "Consensus guidance match",
            "source_title": match.source_title,
            "source_organization": match.organization,
            "source_url": source.url if source else "",
            "source_locator": match.source_locator,
            "exact_excerpt": match.source_excerpt,
            "summary": match.recommendation_text,
            "source_type": match.source_type.value,
            "source_date": source.publication_date.isoformat() if source and source.publication_date else None,
            "therapy_terms": list(match.therapy_terms),
            "gene": None,
            "section": None,
            "verification_status": "source_verified",
            "synthetic": False,
            "metadata": {"recommendation_id": match.recommendation_id},
        })
    return out


def _molecular_candidates(records: Iterable[MolecularEvidenceRecord]) -> list[dict[str, Any]]:
    return [{
        "candidate_id": f"molecular:{record.evidence_id}",
        "channel": "molecular",
        "title": f"{record.gene} molecular evidence candidate",
        "source_title": record.source_title,
        "source_organization": "CIViC" if not record.synthetic else "Controlled fixture",
        "source_url": record.source_url,
        "source_locator": record.source_locator,
        "exact_excerpt": record.source_excerpt,
        "summary": record.evidence_summary,
        "source_type": record.source_type.value,
        "source_date": record.publication_date.isoformat() if record.publication_date else record.accessed_date.isoformat(),
        "therapy_terms": [record.therapy] if record.therapy else [],
        "gene": record.gene,
        "section": None,
        "verification_status": "source_verified" if record.source_verified else "verification_required",
        "synthetic": record.synthetic,
        "metadata": {"evidence_id": record.evidence_id, "actionability": record.actionability.value},
    } for record in records]


def _safety_candidates(records: Iterable[FDALabelSectionCandidate]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        source_token = record.spl_set_id or record.spl_id or "unidentified"
        out.append({
            "candidate_id": f"safety:{index}:{source_token}:{record.section}",
            "channel": "safety",
            "title": f"{record.therapy} · {record.section.replace('_', ' ').title()}",
            "source_title": "FDA Structured Product Labeling" if not record.synthetic else "Controlled safety review fixture",
            "source_organization": "U.S. Food and Drug Administration" if not record.synthetic else "Controlled fixture",
            "source_url": record.source_url,
            "source_locator": f"SPL set {source_token}; section {record.section}",
            "exact_excerpt": safety_candidate_excerpt(record),
            "summary": safety_candidate_excerpt(record, max_chars=280),
            "source_type": "regulatory_label" if not record.synthetic else "synthetic_fixture",
            "source_date": record.effective_time or record.accessed_date.isoformat(),
            "therapy_terms": [record.therapy],
            "gene": None,
            "section": record.section,
            "verification_status": "source_verified" if not record.synthetic else "controlled_fixture",
            "synthetic": record.synthetic,
            "metadata": {"candidate_index": index, "spl_set_id": record.spl_set_id},
        })
    return out


def collect_commissioning_snapshot(
    case: CancerTumorBoardCase,
    *,
    mode: EvidenceMode = "guided_fixture",
) -> EvidenceCommissioningSnapshot:
    guideline_store, _ = resolve_product_guideline_store()
    if mode == "guided_fixture":
        collected = _guided_candidates()
    else:
        collected = collect_case_candidates(
            case,
            guideline_store,
            civic_api_key=os.getenv("CIVIC_API_KEY") or None,
            openfda_api_key=os.getenv("OPENFDA_API_KEY") or None,
        )
    public_candidates = tuple([
        *_guideline_candidates(case, guideline_store),
        *_molecular_candidates(collected.molecular_records),
        *_safety_candidates(collected.safety_records),
    ])
    return EvidenceCommissioningSnapshot(
        case_id=case.case_id,
        mode=mode,
        guideline_store=guideline_store,
        molecular_records=collected.molecular_records,
        safety_records=collected.safety_records,
        candidates=public_candidates,
        warnings=collected.warnings,
    )


def build_commissioned_context(
    snapshot: EvidenceCommissioningSnapshot,
    *,
    candidate_set_id: str,
    decisions: Iterable[dict[str, str]],
    attested: bool,
) -> tuple[Any, dict[str, Any]]:
    if candidate_set_id != snapshot.candidate_set_id:
        raise ValueError("The evidence candidate set changed. Retrieve and review the current set before analysis.")

    decision_rows = list(decisions)
    decision_ids = [row.get("candidate_id", "") for row in decision_rows]
    candidate_ids = [candidate["candidate_id"] for candidate in snapshot.candidates]
    if len(decision_ids) != len(set(decision_ids)):
        raise ValueError("Duplicate evidence decisions are not allowed.")
    if set(decision_ids) != set(candidate_ids):
        raise ValueError("Every current evidence candidate must receive exactly one decision.")

    by_id = {row["candidate_id"]: row for row in decision_rows}
    for candidate_id, row in by_id.items():
        decision = row.get("decision")
        if decision not in {"approved", "rejected"}:
            raise ValueError(f"Unsupported evidence decision for {candidate_id}.")
        if decision == "rejected" and not row.get("reason", "").strip():
            raise ValueError(f"A rejection reason is required for {candidate_id}.")

    approved_ids = {candidate_id for candidate_id, row in by_id.items() if row["decision"] == "approved"}
    if approved_ids and not attested:
        raise ValueError("Human evidence-review attestation is required before approved records can be admitted.")

    approved_guideline_ids = {candidate_id.split(":", 1)[1] for candidate_id in approved_ids if candidate_id.startswith("guideline:")}
    approved_recommendations = tuple(
        recommendation
        for recommendation in snapshot.guideline_store.recommendations
        if recommendation.recommendation_id in approved_guideline_ids
    )
    approved_source_ids = {recommendation.source_id for recommendation in approved_recommendations}
    approved_guideline_store = GuidelineEvidenceStore(
        sources=tuple(source for source in snapshot.guideline_store.sources if source.source_id in approved_source_ids),
        recommendations=approved_recommendations,
    )

    approved_molecular_ids = {candidate_id.split(":", 1)[1] for candidate_id in approved_ids if candidate_id.startswith("molecular:")}
    approved_molecular_store = build_approved_molecular_store(snapshot.molecular_records, approved_molecular_ids)

    safety_index_by_id = {
        candidate["candidate_id"]: int(candidate["metadata"]["candidate_index"])
        for candidate in snapshot.candidates
        if candidate["channel"] == "safety"
    }
    approved_safety_indices = {safety_index_by_id[candidate_id] for candidate_id in approved_ids if candidate_id in safety_index_by_id}
    approved_safety_store = build_approved_safety_store(snapshot.safety_records, approved_safety_indices)

    context = build_workflow_context(
        guideline_store_override=approved_guideline_store,
        molecular_store_override=approved_molecular_store,
        safety_store_override=approved_safety_store,
    )
    receipt = {
        "candidate_set_id": snapshot.candidate_set_id,
        "mode": snapshot.mode,
        "candidate_count": len(candidate_ids),
        "approved_count": len(approved_ids),
        "rejected_count": len(candidate_ids) - len(approved_ids),
        "approved_candidate_ids": sorted(approved_ids),
        "attested": bool(attested),
        "fail_closed": True,
    }
    return context, receipt
