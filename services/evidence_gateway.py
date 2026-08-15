from __future__ import annotations

from hashlib import sha256

from agents.guideline import GuidelineEvidenceStore
from schemas.evidence_gateway import (
    EvidenceIngestionPackage,
    EvidenceIngestionResult,
    EvidenceIngestionStatus,
    EvidenceVerificationCode,
    EvidenceVerificationFinding,
)
from schemas.guideline import GuidanceRecommendation, GuidanceSource, GuidanceSourceType


GATEWAY_VERSION = "1.0.0"
_AUTHORIZED_LICENSES = {"public", "licensed", "institution_authorized", "synthetic"}


def normalized_sha256(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return sha256(normalized.encode("utf-8")).hexdigest()


def _finding(code: EvidenceVerificationCode, message: str, *, recommendation_id: str | None = None, severity: str = "error") -> EvidenceVerificationFinding:
    return EvidenceVerificationFinding(
        code=code,
        severity=severity,
        message=message,
        recommendation_id=recommendation_id,
    )


def verify_evidence_package(package: EvidenceIngestionPackage, *, production_mode: bool = True) -> tuple[EvidenceIngestionResult, GuidelineEvidenceStore]:
    """Verify one source package and convert only accepted records into a GuidelineEvidenceStore.

    The gateway is deliberately deterministic. It does not infer source type, licensing,
    recommendation meaning, or missing text. Exact excerpts must occur verbatim in the
    supplied source_text. A rejected package contributes no source or recommendations.
    """
    manifest = package.manifest
    findings: list[EvidenceVerificationFinding] = []
    content_hash = normalized_sha256(package.source_text)

    if not package.source_text.strip():
        findings.append(_finding(EvidenceVerificationCode.SOURCE_CONTENT_EMPTY, "Source text is empty."))

    if manifest.license_status not in _AUTHORIZED_LICENSES or manifest.license_status == "unknown":
        findings.append(_finding(EvidenceVerificationCode.LICENSE_NOT_AUTHORIZED, "Source license/authorization status does not permit ingestion."))

    if not manifest.human_verified:
        findings.append(_finding(EvidenceVerificationCode.SOURCE_NOT_HUMAN_VERIFIED, "Source manifest has not been human verified."))

    if content_hash != manifest.expected_content_sha256:
        findings.append(_finding(EvidenceVerificationCode.CONTENT_HASH_MISMATCH, "Source text SHA-256 does not match the frozen manifest digest."))

    if production_mode and manifest.source_type == GuidanceSourceType.SYNTHETIC_FIXTURE:
        findings.append(_finding(EvidenceVerificationCode.SYNTHETIC_SOURCE_PRODUCTION_BLOCK, "Synthetic evidence cannot enter the production evidence store."))

    source_errors = [f for f in findings if f.severity == "error"]
    if source_errors:
        result = EvidenceIngestionResult(
            source_id=manifest.source_id,
            status=EvidenceIngestionStatus.REJECTED,
            content_sha256=content_hash,
            source_verified=False,
            findings=findings,
            source_count=0,
            recommendation_count=0,
            can_enter_guideline_store=False,
        )
        return result, GuidelineEvidenceStore()

    accepted: list[GuidanceRecommendation] = []
    rejected_ids: list[str] = []

    for record in package.recommendations:
        rec_findings: list[EvidenceVerificationFinding] = []
        if record.source_id != manifest.source_id:
            rec_findings.append(_finding(
                EvidenceVerificationCode.RECOMMENDATION_SOURCE_MISMATCH,
                "Recommendation source_id does not match the package manifest source_id.",
                recommendation_id=record.recommendation_id,
            ))
        if not record.source_excerpt.strip():
            rec_findings.append(_finding(
                EvidenceVerificationCode.RECOMMENDATION_EXCERPT_MISSING,
                "Recommendation has no source excerpt.",
                recommendation_id=record.recommendation_id,
            ))
        elif record.source_excerpt not in package.source_text:
            rec_findings.append(_finding(
                EvidenceVerificationCode.RECOMMENDATION_EXCERPT_NOT_EXACT,
                "Recommendation excerpt is not an exact substring of the supplied source text.",
                recommendation_id=record.recommendation_id,
            ))
        if not record.source_locator.strip():
            rec_findings.append(_finding(
                EvidenceVerificationCode.SOURCE_LOCATOR_MISSING,
                "Recommendation requires a source locator.",
                recommendation_id=record.recommendation_id,
            ))
        if not record.human_verified:
            rec_findings.append(_finding(
                EvidenceVerificationCode.RECOMMENDATION_NOT_HUMAN_VERIFIED,
                "Recommendation record has not been human verified.",
                recommendation_id=record.recommendation_id,
            ))

        if rec_findings:
            findings.extend(rec_findings)
            rejected_ids.append(record.recommendation_id)
            continue

        accepted.append(GuidanceRecommendation(
            recommendation_id=record.recommendation_id,
            source_id=record.source_id,
            disease_terms=record.disease_terms,
            disease_states=record.disease_states,
            question_domains=record.question_domains,
            recommendation_text=record.recommendation_text,
            source_excerpt=record.source_excerpt,
            source_locator=record.source_locator,
            strength=record.strength,
            evidence_level=record.evidence_level,
            conditions=record.conditions,
            exclusions=record.exclusions,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            source_verified=True,
        ))

    source = GuidanceSource(
        source_id=manifest.source_id,
        title=manifest.title,
        organization=manifest.organization,
        source_type=manifest.source_type,
        jurisdiction=manifest.jurisdiction,
        url=str(manifest.url),
        version=manifest.version,
        publication_date=manifest.publication_date,
        updated_date=manifest.updated_date,
        review_due_date=manifest.review_due_date,
        accessed_date=manifest.accessed_date,
        license_status=manifest.license_status,
        verified=True,
        content_hash=content_hash,
    )

    status = EvidenceIngestionStatus.ACCEPTED if not rejected_ids else EvidenceIngestionStatus.ACCEPTED_WITH_LIMITATIONS
    store = GuidelineEvidenceStore(sources=(source,), recommendations=tuple(accepted))
    result = EvidenceIngestionResult(
        source_id=manifest.source_id,
        status=status,
        content_sha256=content_hash,
        source_verified=True,
        accepted_recommendation_ids=[r.recommendation_id for r in accepted],
        rejected_recommendation_ids=rejected_ids,
        findings=findings,
        source_count=1,
        recommendation_count=len(accepted),
        can_enter_guideline_store=True,
    )
    return result, store
