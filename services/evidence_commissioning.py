from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from agents.guideline import GuidelineAgent, GuidelineEvidenceStore
from schemas.case import CancerTumorBoardCase
from schemas.molecular import MolecularEvidenceRecord, MolecularEvidenceStore
from schemas.safety import SafetyEvidenceStore, SafetyEvidenceType, SafetySeverity
from services.civic_molecular_adapter import CIViCMolecularClient, attest_civic_records
from services.fda_label_adapter import (
    FDALabelClient,
    FDALabelSectionCandidate,
    SafetyRecordAttestation,
    build_attested_safety_store,
)


@dataclass(frozen=True)
class CommissioningCandidates:
    molecular_records: tuple[MolecularEvidenceRecord, ...] = ()
    safety_records: tuple[FDALabelSectionCandidate, ...] = ()
    candidate_therapies: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


_SAFETY_SECTIONS = {
    "boxed_warning",
    "contraindications",
    "warnings",
    "warnings_and_cautions",
    "drug_interactions",
    "adverse_reactions",
    "dosage_and_administration",
    "use_in_specific_populations",
}


def _dedupe_terms(values: Iterable[str | None]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        term = " ".join(str(value or "").split()).strip()
        key = term.lower()
        if term and key not in seen:
            seen.add(key)
            ordered.append(term)
    return tuple(ordered)


def _dedupe_molecular(records: Iterable[MolecularEvidenceRecord]) -> tuple[MolecularEvidenceRecord, ...]:
    out: dict[str, MolecularEvidenceRecord] = {}
    for record in records:
        out.setdefault(record.evidence_id, record)
    return tuple(out[key] for key in sorted(out))


def collect_molecular_candidates(
    case: CancerTumorBoardCase,
    *,
    api_key: str | None = None,
    limit_per_finding: int = 25,
) -> tuple[tuple[MolecularEvidenceRecord, ...], tuple[str, ...]]:
    """Retrieve accepted CIViC evidence candidates for represented case findings."""
    client = CIViCMolecularClient(api_key=api_key)
    disease = str(case.diagnosis.value or "").strip()
    records: list[MolecularEvidenceRecord] = []
    warnings: list[str] = []

    for finding in case.molecular_findings:
        try:
            result = client.fetch(
                gene=finding.gene,
                alteration=finding.alteration_type or finding.hgvs_p or finding.hgvs_c,
                disease=disease,
                limit=limit_per_finding,
            )
            records.extend(result.records)
            warnings.extend(result.warnings)
            if not result.records and finding.alteration_type:
                fallback = client.fetch(
                    gene=finding.gene,
                    alteration=None,
                    disease=disease,
                    limit=limit_per_finding,
                )
                records.extend(fallback.records)
                warnings.extend(fallback.warnings)
        except Exception as exc:
            warnings.append(f"CIViC retrieval failed for {finding.gene}: {type(exc).__name__}: {exc}")

    return _dedupe_molecular(records), tuple(dict.fromkeys(warnings))


def guideline_candidate_therapies(
    case: CancerTumorBoardCase,
    guideline_store: GuidelineEvidenceStore,
) -> tuple[str, ...]:
    report = GuidelineAgent(guideline_store).run(case)
    therapies: list[str] = []
    if report.can_support_guideline_claim:
        for match in report.matched_guidance:
            therapies.extend(match.therapy_terms)
    return _dedupe_terms(therapies)


def represented_therapy_terms(case: CancerTumorBoardCase) -> tuple[str, ...]:
    """Return explicit treatment concepts already represented in the canonical case.

    Individual agents are preferred. A regimen name is used only when no component
    agents were represented for that treatment episode. These terms are used solely
    for FDA label discovery and never create a treatment recommendation.
    """
    therapies: list[str] = []
    for episode in case.treatments:
        if episode.agents:
            therapies.extend(episode.agents)
        elif episode.regimen:
            therapies.append(episode.regimen)
    return _dedupe_terms(therapies)


def molecular_candidate_therapies(records: Iterable[MolecularEvidenceRecord]) -> tuple[str, ...]:
    """Return therapy concepts stated by retrieved CIViC candidate records.

    Retrieval alone does not admit the molecular evidence or establish actionability.
    The terms only widen bounded FDA-label discovery so safety review is not coupled
    to the presence of a disease-specific formal guideline package.
    """
    return _dedupe_terms(record.therapy for record in records if record.therapy)


def collect_safety_candidates(
    case: CancerTumorBoardCase,
    guideline_store: GuidelineEvidenceStore,
    *,
    additional_therapy_terms: Iterable[str] = (),
    api_key: str | None = None,
    limit_per_therapy: int = 5,
) -> tuple[tuple[FDALabelSectionCandidate, ...], tuple[str, ...], tuple[str, ...]]:
    therapies = _dedupe_terms([
        *guideline_candidate_therapies(case, guideline_store),
        *represented_therapy_terms(case),
        *additional_therapy_terms,
    ])
    warnings: list[str] = []
    candidates: list[FDALabelSectionCandidate] = []
    client = FDALabelClient(api_key=api_key)

    for therapy in therapies:
        try:
            fetched = client.fetch_sections(therapy=therapy, limit=limit_per_therapy)
            candidates.extend(candidate for candidate in fetched if candidate.section in _SAFETY_SECTIONS)
        except Exception as exc:
            warnings.append(f"FDA label retrieval failed for {therapy}: {type(exc).__name__}: {exc}")

    unique: dict[tuple[str | None, str, str], FDALabelSectionCandidate] = {}
    for candidate in candidates:
        unique.setdefault((candidate.spl_set_id, candidate.section, candidate.text), candidate)
    ordered = tuple(
        unique[key]
        for key in sorted(unique, key=lambda item: (str(item[0]), item[1], item[2]))
    )
    return ordered, therapies, tuple(dict.fromkeys(warnings))


def collect_case_candidates(
    case: CancerTumorBoardCase,
    guideline_store: GuidelineEvidenceStore,
    *,
    civic_api_key: str | None = None,
    openfda_api_key: str | None = None,
) -> CommissioningCandidates:
    molecular, mw = collect_molecular_candidates(case, api_key=civic_api_key)
    safety, therapies, sw = collect_safety_candidates(
        case,
        guideline_store,
        additional_therapy_terms=molecular_candidate_therapies(molecular),
        api_key=openfda_api_key,
    )
    return CommissioningCandidates(
        molecular_records=molecular,
        safety_records=safety,
        candidate_therapies=therapies,
        warnings=tuple(dict.fromkeys([*mw, *sw])),
    )


def build_approved_molecular_store(
    records: Iterable[MolecularEvidenceRecord],
    approved_ids: set[str],
) -> MolecularEvidenceStore:
    return attest_civic_records(tuple(records), verified_evidence_ids=set(approved_ids))


def safety_candidate_excerpt(candidate: FDALabelSectionCandidate, *, max_chars: int = 650) -> str:
    text = " ".join(candidate.text.split()).strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    sentence_end = max(cut.rfind(". "), cut.rfind("; "))
    if sentence_end >= 120:
        cut = cut[: sentence_end + 1]
    return cut.strip()


def _safety_type(section: str) -> SafetyEvidenceType:
    return {
        "contraindications": SafetyEvidenceType.CONTRAINDICATION,
        "drug_interactions": SafetyEvidenceType.INTERACTION,
        "adverse_reactions": SafetyEvidenceType.TOXICITY,
        "dosage_and_administration": SafetyEvidenceType.DOSE_CONSIDERATION,
        "use_in_specific_populations": SafetyEvidenceType.WARNING,
        "boxed_warning": SafetyEvidenceType.WARNING,
        "warnings": SafetyEvidenceType.WARNING,
        "warnings_and_cautions": SafetyEvidenceType.WARNING,
    }.get(section, SafetyEvidenceType.WARNING)


def _safety_severity(section: str) -> SafetySeverity:
    if section in {"boxed_warning", "contraindications"}:
        return SafetySeverity.CRITICAL
    if section in {"warnings", "warnings_and_cautions"}:
        return SafetySeverity.HIGH
    return SafetySeverity.MODERATE


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "record"


def build_approved_safety_store(
    candidates: list[FDALabelSectionCandidate] | tuple[FDALabelSectionCandidate, ...],
    approved_indices: set[int],
) -> SafetyEvidenceStore:
    """Create source-attested safety records from the exact FDA spans shown in UI.

    Selection attests that the displayed source span was reviewed and attributed to
    the represented product/section. It does not infer that a contraindication or
    warning applies to this patient. Patient-specific contraindication logic requires
    a separately structured trigger and therefore remains false in this generic
    commissioning path.
    """
    attestations: list[SafetyRecordAttestation] = []
    for index in sorted(approved_indices):
        if index < 0 or index >= len(candidates):
            raise ValueError(f"Invalid approved FDA candidate index: {index}")
        candidate = candidates[index]
        excerpt = safety_candidate_excerpt(candidate)
        issue_preview = excerpt[:180].strip()
        if len(excerpt) > 180:
            issue_preview = issue_preview.rstrip(" ,;:") + "..."
        source_token = candidate.spl_set_id or candidate.spl_id or candidate.therapy
        attestations.append(
            SafetyRecordAttestation(
                candidate_index=index,
                evidence_id=f"FDA-SPL-{_safe_id(source_token)}-{_safe_id(candidate.section)}-{index}",
                evidence_type=_safety_type(candidate.section),
                severity=_safety_severity(candidate.section),
                safety_issue=f"{candidate.section.replace('_', ' ').title()}: {issue_preview}",
                exact_excerpt=excerpt,
                therapy_terms=(candidate.therapy,),
                contraindication=False,
            )
        )
    return build_attested_safety_store(list(candidates), attestations)
