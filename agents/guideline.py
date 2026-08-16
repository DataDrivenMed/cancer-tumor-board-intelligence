from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re

from schemas.case import CancerTumorBoardCase, DataStatus
from schemas.guideline import (
    GuidanceMatch,
    GuidanceRecommendation,
    GuidanceSource,
    GuidanceSourceType,
    GuidelineReport,
)
from services.oncology_programs import is_registered_oncology_program


AGENT_ID = "guideline"
AGENT_VERSION = "1.3.1"


@dataclass(frozen=True)
class GuidelineEvidenceStore:
    sources: tuple[GuidanceSource, ...] = ()
    recommendations: tuple[GuidanceRecommendation, ...] = ()


def _norm(value: object | None) -> str:
    return " ".join(str(value or "").lower().replace("-", " ").replace("/", " ").split())


def _tokens(value: object | None) -> set[str]:
    return {t for t in _norm(value).split() if len(t) >= 3}


def _text_match(case_value: object | None, allowed_terms: list[str]) -> bool:
    if not allowed_terms:
        return True
    case_text = _norm(case_value)
    case_tokens = _tokens(case_value)
    for term in allowed_terms:
        term_norm = _norm(term)
        if term_norm and term_norm in case_text:
            return True
        term_tokens = _tokens(term)
        if term_tokens and term_tokens.issubset(case_tokens):
            return True
    return False


_STAGE_LABEL_RE = re.compile(
    r"\bstage\s+(0|[1-4](?:[abc])?(?:[1-3])?|[ivx]{1,4}(?:[abc])?(?:[1-3])?)\b",
    flags=re.IGNORECASE,
)


def _canonical_stage_label(value: object | None) -> str | None:
    """Return an exact canonical stage label without deriving stage from other data."""
    text = _norm(value)
    match = _STAGE_LABEL_RE.search(text)
    if not match:
        return None
    raw = match.group(1).upper()
    roman_to_arabic = {"I": "1", "II": "2", "III": "3", "IV": "4"}
    for roman in ("IV", "III", "II", "I"):
        if raw.startswith(roman):
            return roman_to_arabic[roman] + raw[len(roman):]
    return raw


def _verified_stage_text(case: CancerTumorBoardCase) -> str:
    stage = case.stage
    if stage is None or stage.status != DataStatus.CONFIRMED or not stage.human_verified:
        return ""
    if not any(bool(getattr(p, "source_verified", False)) for p in (stage.provenance or [])):
        return ""
    return str(stage.value or "")


def _stage_requirements_match(case: CancerTumorBoardCase, stage_terms: list[str]) -> bool:
    """Match only explicit stage labels; never use generic token overlap.

    A disease pack that intends to support multiple substages must enumerate those
    substages explicitly. This conservative rule prevents Stage II from matching
    Stage III merely because both contain the word 'stage'.
    """
    if not stage_terms:
        return True
    represented = _canonical_stage_label(_verified_stage_text(case))
    if not represented:
        return False
    allowed = {
        label
        for term in stage_terms
        if (label := _canonical_stage_label(term)) is not None
    }
    return represented in allowed


def _verified_molecular_text(case: CancerTumorBoardCase) -> str:
    values: list[str] = []
    for finding in case.molecular_findings:
        if not finding.human_verified:
            continue
        if not any(bool(getattr(p, "source_verified", False)) for p in (finding.provenance or [])):
            continue
        values.extend(
            str(value)
            for value in (
                finding.gene,
                finding.alteration_type,
                finding.hgvs_c,
                finding.hgvs_p,
            )
            if value
        )
    return _norm(" ".join(values))


def _molecular_requirements_match(case: CancerTumorBoardCase, required_terms: list[str]) -> bool:
    if not required_terms:
        return True
    represented = _verified_molecular_text(case)
    if not represented:
        return False
    return all(_norm(term) and _norm(term) in represented for term in required_terms)


def _question_domain(case: CancerTumorBoardCase) -> str:
    text = _norm(case.clinical_question.question_type) + " " + _norm(case.clinical_question.question)
    if any(x in text for x in ("safety", "toxicity", "interaction", "contraindication")):
        return "safety"
    if any(x in text for x in ("trial", "study", "clinical trial")):
        return "clinical_trial"
    if any(x in text for x in ("molecular", "mutation", "genomic", "target", "biomarker")):
        return "molecular_management"
    if any(x in text for x in ("diagnos", "classification", "workup")):
        return "diagnosis_workup"
    if any(x in text for x in ("treatment", "therapy", "management", "relapsed", "refractory", "frontline", "first line")):
        return "treatment_management"
    return "general_tumor_board"


def _current_on(source: GuidanceSource, recommendation: GuidanceRecommendation, today: date) -> bool:
    if source.review_due_date and source.review_due_date < today:
        return False
    if recommendation.effective_from and recommendation.effective_from > today:
        return False
    if recommendation.effective_to and recommendation.effective_to < today:
        return False
    return True


def _label(source_type: GuidanceSourceType) -> str:
    return {
        GuidanceSourceType.FORMAL_GUIDELINE: "guideline_supported",
        GuidanceSourceType.CONSENSUS_GUIDELINE: "consensus_supported",
        GuidanceSourceType.AUTHORITATIVE_EVIDENCE_SUMMARY: "authoritative_evidence_summary",
        GuidanceSourceType.REGULATORY: "regulatory_supported",
        GuidanceSourceType.INSTITUTIONAL_POLICY: "institutional_policy_supported",
        GuidanceSourceType.SYNTHETIC_FIXTURE: "synthetic_fixture",
    }[source_type]


class GuidelineAgent:
    """Evidence-bounded pan-oncology guidance matcher with stage and molecular prerequisites."""

    agent_id = AGENT_ID
    agent_version = AGENT_VERSION

    def __init__(
        self,
        evidence_store: GuidelineEvidenceStore | None = None,
        *,
        allow_synthetic: bool = False,
        today: date | None = None,
    ) -> None:
        self.store = evidence_store or GuidelineEvidenceStore()
        self.allow_synthetic = allow_synthetic
        self.today = today or date.today()

    def run(self, case: CancerTumorBoardCase) -> GuidelineReport:
        if not is_registered_oncology_program(case.disease_program):
            return GuidelineReport(
                case_id=case.case_id,
                status="abstain_domain",
                summary="Guideline Agent received a case outside the registered oncology programs.",
                limitations=["The disease program must be classified into the governed pan-oncology registry before analysis."],
            )

        sources = list(self.store.sources)
        recommendations = list(self.store.recommendations)
        source_by_id = {s.source_id: s for s in sources}

        verified_sources = [
            s for s in sources
            if s.verified and (self.allow_synthetic or s.source_type != GuidanceSourceType.SYNTHETIC_FIXTURE)
        ]
        verified_source_ids = {s.source_id for s in verified_sources}
        verified_recommendations = [
            r for r in recommendations
            if r.source_verified and r.source_id in verified_source_ids
        ]

        if not sources:
            return GuidelineReport(
                case_id=case.case_id,
                status="source_unavailable",
                sources_considered=0,
                recommendations_considered=0,
                summary="No guidance evidence source is configured; no guideline claim can be generated.",
                limitations=["A verified, authorized disease-specific guidance source must be connected before guideline analysis can run."],
                can_support_guideline_claim=False,
            )

        if not verified_sources:
            return GuidelineReport(
                case_id=case.case_id,
                status="verification_failed",
                sources_considered=len(sources),
                verified_sources_considered=0,
                recommendations_considered=len(recommendations),
                verified_recommendations_considered=0,
                summary="Configured guidance sources failed verification or are not authorized for this execution.",
                warnings=["Unverified or synthetic-only sources were not propagated."],
                can_support_guideline_claim=False,
            )

        diagnosis = case.diagnosis.value
        disease_state = case.disease_state.value
        question_domain = _question_domain(case)
        matches: list[GuidanceMatch] = []
        expired_or_outdated = 0
        stage_prerequisite_misses = 0
        molecular_prerequisite_misses = 0

        for rec in verified_recommendations:
            source = source_by_id[rec.source_id]
            if not _current_on(source, rec, self.today):
                expired_or_outdated += 1
                continue
            if not _text_match(diagnosis, rec.disease_terms):
                continue
            if not _text_match(disease_state, rec.disease_states):
                continue
            if rec.question_domains and question_domain not in rec.question_domains:
                continue
            if not _stage_requirements_match(case, rec.stage_terms):
                stage_prerequisite_misses += 1
                continue
            if not _molecular_requirements_match(case, rec.required_molecular_terms):
                molecular_prerequisite_misses += 1
                continue

            dimensions: list[str] = []
            if rec.disease_terms:
                dimensions.append("diagnosis")
            if rec.disease_states:
                dimensions.append("disease_state")
            if rec.stage_terms:
                dimensions.append("verified_explicit_stage_prerequisite")
            if rec.question_domains:
                dimensions.append("question_domain")
            if rec.required_molecular_terms:
                dimensions.append("verified_molecular_prerequisite")

            matches.append(GuidanceMatch(
                recommendation_id=rec.recommendation_id,
                source_id=source.source_id,
                source_title=source.title,
                organization=source.organization,
                source_type=source.source_type,
                jurisdiction=source.jurisdiction,
                recommendation_text=rec.recommendation_text,
                source_excerpt=rec.source_excerpt,
                source_locator=rec.source_locator,
                strength=rec.strength,
                evidence_level=rec.evidence_level,
                match_dimensions=dimensions,
                stage_terms=rec.stage_terms,
                required_molecular_terms=rec.required_molecular_terms,
                therapy_terms=rec.therapy_terms,
                conditions=rec.conditions,
                exclusions=rec.exclusions,
                epistemic_label=_label(source.source_type),
                current_on=self.today,
            ))

        matches.sort(key=lambda m: (m.source_type.value, m.source_id, m.recommendation_id))
        formal_matches = sum(
            m.source_type in {GuidanceSourceType.FORMAL_GUIDELINE, GuidanceSourceType.CONSENSUS_GUIDELINE}
            for m in matches
        )

        warnings: list[str] = []
        limitations: list[str] = []
        if expired_or_outdated:
            warnings.append(f"{expired_or_outdated} verified recommendation(s) were excluded because the source/recommendation was not current on {self.today.isoformat()}.")
        if stage_prerequisite_misses:
            limitations.append(
                f"{stage_prerequisite_misses} stage-dependent recommendation(s) were excluded because the required explicit stage was not represented with verified provenance and clinician confirmation."
            )
        if molecular_prerequisite_misses:
            limitations.append(
                f"{molecular_prerequisite_misses} targeted recommendation(s) were excluded because required molecular prerequisites were not represented with verified case provenance."
            )
        if matches and formal_matches == 0:
            limitations.append(
                "Matched evidence does not include a formal or consensus guideline; it must not be described as a guideline recommendation."
            )

        if not matches:
            return GuidelineReport(
                case_id=case.case_id,
                status="no_evidence_found",
                sources_considered=len(sources),
                verified_sources_considered=len(verified_sources),
                recommendations_considered=len(recommendations),
                verified_recommendations_considered=len(verified_recommendations),
                formal_guideline_matches=0,
                warnings=warnings,
                limitations=limitations,
                summary="No current verified disease-specific guidance recommendation matched the represented diagnosis, disease state, explicit stage prerequisites, question domain, and required molecular prerequisites.",
                can_support_guideline_claim=False,
            )

        status = "completed" if formal_matches else "completed_with_limitations"
        return GuidelineReport(
            case_id=case.case_id,
            status=status,
            matched_guidance=matches,
            sources_considered=len(sources),
            verified_sources_considered=len(verified_sources),
            recommendations_considered=len(recommendations),
            verified_recommendations_considered=len(verified_recommendations),
            formal_guideline_matches=formal_matches,
            limitations=limitations,
            warnings=warnings,
            summary=(
                f"{len(matches)} current verified guidance statement(s) matched. "
                f"{formal_matches} are from formal or consensus guideline sources."
            ),
            can_support_guideline_claim=formal_matches > 0,
        )