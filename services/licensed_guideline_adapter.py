from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256

from agents.guideline import GuidelineEvidenceStore
from schemas.guideline import (
    GuidanceRecommendation,
    GuidanceSource,
    GuidanceSourceType,
    GuidanceStrength,
)


class SourceUseProhibitedError(ValueError):
    """Raised when the supplied source text explicitly prohibits AI/tool use."""


@dataclass(frozen=True)
class LicensedGuidelineMetadata:
    source_id: str
    title: str
    organization: str
    jurisdiction: str
    version: str
    accessed_date: date
    publication_date: date | None = None
    updated_date: date | None = None
    review_due_date: date | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class GuidelineRecommendationAttestation:
    recommendation_id: str
    disease_terms: tuple[str, ...]
    disease_states: tuple[str, ...]
    question_domains: tuple[str, ...]
    recommendation_text: str
    exact_source_excerpt: str
    source_locator: str
    strength: GuidanceStrength = GuidanceStrength.NOT_STATED
    evidence_level: str | None = None
    conditions: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = ()
    effective_from: date | None = None
    effective_to: date | None = None


def normalized_text_hash(text: str) -> str:
    normalized = " ".join((text or "").split())
    return sha256(normalized.encode("utf-8")).hexdigest()


def _assert_source_allows_ai_processing(source_text: str) -> None:
    """Fail closed when the source itself states that AI/tool use is prohibited.

    Institutional access is not interpreted as permission to process a source with
    an AI system. If separate written authorization is later obtained, the operator
    should commission that source under a separately reviewed integration contract
    rather than bypassing this control.
    """
    normalized = " ".join((source_text or "").lower().split())
    prohibited_markers = (
        "may not distribute this content or use it with any artificial intelligence model or tool",
        "may not use it with any artificial intelligence model or tool",
        "may not use this content with any artificial intelligence model or tool",
        "prohibited from use with artificial intelligence",
    )
    if any(marker in normalized for marker in prohibited_markers):
        raise SourceUseProhibitedError(
            "The supplied guideline source explicitly prohibits use with artificial-intelligence models/tools. "
            "It cannot be ingested by this application without a separately reviewed authorization path."
        )


def build_licensed_guideline_store(
    *,
    source_text: str,
    metadata: LicensedGuidelineMetadata,
    attestations: list[GuidelineRecommendationAttestation],
) -> GuidelineEvidenceStore:
    """Build a verified deployment-time store from an institution-authorized source.

    The source document itself should remain outside the public repository. Every
    recommendation must carry an exact source span that is present in the supplied
    source text. Sources that explicitly prohibit AI/tool use are rejected before
    any content is transformed or admitted.
    """
    normalized_source = " ".join((source_text or "").split())
    if not normalized_source:
        raise ValueError("licensed guideline source_text is empty")

    _assert_source_allows_ai_processing(source_text)

    source = GuidanceSource(
        source_id=metadata.source_id,
        title=metadata.title,
        organization=metadata.organization,
        source_type=GuidanceSourceType.FORMAL_GUIDELINE,
        jurisdiction=metadata.jurisdiction,
        url=metadata.source_url,
        version=metadata.version,
        publication_date=metadata.publication_date,
        updated_date=metadata.updated_date,
        review_due_date=metadata.review_due_date,
        accessed_date=metadata.accessed_date,
        license_status="institution_authorized",
        verified=True,
        content_hash=normalized_text_hash(source_text),
    )

    recommendations: list[GuidanceRecommendation] = []
    seen_ids: set[str] = set()

    for item in attestations:
        if item.recommendation_id in seen_ids:
            raise ValueError(f"Duplicate recommendation_id: {item.recommendation_id}")
        excerpt = " ".join((item.exact_source_excerpt or "").split())
        if not excerpt or excerpt not in normalized_source:
            raise ValueError(
                f"Exact source excerpt for {item.recommendation_id} is not present in the licensed source text"
            )
        if not item.recommendation_text.strip():
            raise ValueError(f"recommendation_text is empty for {item.recommendation_id}")

        recommendations.append(
            GuidanceRecommendation(
                recommendation_id=item.recommendation_id,
                source_id=metadata.source_id,
                disease_terms=list(item.disease_terms),
                disease_states=list(item.disease_states),
                question_domains=list(item.question_domains),
                recommendation_text=item.recommendation_text.strip(),
                source_excerpt=excerpt,
                source_locator=item.source_locator.strip(),
                strength=item.strength,
                evidence_level=item.evidence_level,
                conditions=list(item.conditions),
                exclusions=list(item.exclusions),
                effective_from=item.effective_from,
                effective_to=item.effective_to,
                source_verified=True,
            )
        )
        seen_ids.add(item.recommendation_id)

    return GuidelineEvidenceStore(
        sources=(source,),
        recommendations=tuple(recommendations),
    )


def serialize_guideline_store(store: GuidelineEvidenceStore) -> dict:
    """Serialize for secure deployment as GUIDELINE_EVIDENCE_JSON/PATH."""
    return {
        "sources": [source.model_dump(mode="json") for source in store.sources],
        "recommendations": [rec.model_dump(mode="json") for rec in store.recommendations],
    }
