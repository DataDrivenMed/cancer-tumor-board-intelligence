from __future__ import annotations

from hashlib import sha256

from schemas.evidence_verifier import (
    EvidenceClaimCandidate,
    EvidenceClaimStatus,
    EvidenceDirection,
    EvidenceSourceSnapshot,
    EvidenceVerificationFinding,
    EvidenceVerifierReport,
    VerificationFindingCode,
    VerifiedEvidenceClaim,
)


VERIFIER_VERSION = "1.0.0"


def normalized_sha256(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return sha256(normalized.encode("utf-8")).hexdigest()


def _finding(code: VerificationFindingCode, message: str, *, severity: str = "error") -> EvidenceVerificationFinding:
    return EvidenceVerificationFinding(code=code, severity=severity, message=message)


def verify_claim(
    candidate: EvidenceClaimCandidate,
    source: EvidenceSourceSnapshot | None,
) -> VerifiedEvidenceClaim:
    findings: list[EvidenceVerificationFinding] = []

    if source is None or source.pmid != candidate.pmid:
        findings.append(_finding(VerificationFindingCode.PMID_NOT_RETRIEVED, "Claim PMID is not present in the supplied verified source set."))
        status = EvidenceClaimStatus.REJECTED
        return VerifiedEvidenceClaim(
            claim_id=candidate.claim_id,
            claim_text=candidate.claim_text,
            claim_type=candidate.claim_type,
            pmid=candidate.pmid,
            status=status,
            direction=candidate.direction,
            source_excerpt=candidate.source_excerpt,
            study_design=candidate.study_design,
            population=candidate.population,
            intervention=candidate.intervention,
            comparator=candidate.comparator,
            endpoints=candidate.endpoints,
            numeric_results=candidate.numeric_results,
            applicability=candidate.applicability,
            findings=findings,
            can_influence_synthesis=False,
        )

    if not source.source_verified:
        findings.append(_finding(VerificationFindingCode.SOURCE_NOT_VERIFIED, "PubMed source record is not marked source_verified."))
    if not source.abstract_text.strip():
        findings.append(_finding(VerificationFindingCode.ABSTRACT_UNAVAILABLE, "No abstract text is available for exact claim verification."))
    if not source.abstract_sha256.strip():
        findings.append(_finding(VerificationFindingCode.ABSTRACT_HASH_MISSING, "Source abstract SHA-256 is missing."))
    else:
        actual_hash = normalized_sha256(source.abstract_text)
        if actual_hash != source.abstract_sha256 or actual_hash != candidate.abstract_sha256:
            findings.append(_finding(VerificationFindingCode.ABSTRACT_HASH_MISMATCH, "Candidate/source abstract hash does not match the supplied frozen abstract text."))
    if not candidate.source_excerpt.strip():
        findings.append(_finding(VerificationFindingCode.SOURCE_EXCERPT_MISSING, "Claim has no exact supporting source excerpt."))
    elif candidate.source_excerpt not in source.abstract_text:
        findings.append(_finding(VerificationFindingCode.SOURCE_EXCERPT_NOT_EXACT, "Claim excerpt is not an exact substring of the frozen abstract text."))
    if not candidate.human_verified:
        findings.append(_finding(VerificationFindingCode.HUMAN_REVIEW_REQUIRED, "Claim candidate has not been human verified."))
    if not (candidate.study_design or "").strip():
        findings.append(_finding(VerificationFindingCode.STUDY_DESIGN_MISSING, "Study design has not been explicitly characterized."))
    if not (candidate.population or "").strip():
        findings.append(_finding(VerificationFindingCode.POPULATION_MISSING, "Study population has not been explicitly characterized."))
    if not candidate.endpoints:
        findings.append(_finding(VerificationFindingCode.ENDPOINTS_MISSING, "Relevant endpoint(s) have not been explicitly captured."))
    if candidate.claim_type.value in {"efficacy", "safety", "prognostic", "diagnostic", "biomarker"} and not candidate.numeric_results:
        findings.append(_finding(VerificationFindingCode.NUMERIC_RESULTS_MISSING, "Quantitative result(s) required for this claim type were not captured.", severity="warning"))
    if not (candidate.applicability or "").strip():
        findings.append(_finding(VerificationFindingCode.APPLICABILITY_NOT_ASSESSED, "Applicability to the represented clinical question has not been assessed.", severity="warning"))
    if candidate.direction in {EvidenceDirection.CONTRADICTS, EvidenceDirection.MIXED}:
        findings.append(_finding(VerificationFindingCode.CONTRADICTION_PRESENT, "Evidence direction is contradictory or mixed and requires explicit synthesis handling.", severity="warning"))

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    if errors:
        hard_reject_codes = {
            VerificationFindingCode.PMID_NOT_RETRIEVED,
            VerificationFindingCode.SOURCE_NOT_VERIFIED,
            VerificationFindingCode.ABSTRACT_UNAVAILABLE,
            VerificationFindingCode.ABSTRACT_HASH_MISSING,
            VerificationFindingCode.ABSTRACT_HASH_MISMATCH,
            VerificationFindingCode.SOURCE_EXCERPT_MISSING,
            VerificationFindingCode.SOURCE_EXCERPT_NOT_EXACT,
        }
        status = EvidenceClaimStatus.REJECTED if any(f.code in hard_reject_codes for f in errors) else EvidenceClaimStatus.UNVERIFIED
    elif candidate.direction in {EvidenceDirection.CONTRADICTS, EvidenceDirection.MIXED}:
        status = EvidenceClaimStatus.CONFLICTING
    elif warnings:
        status = EvidenceClaimStatus.PARTIALLY_VERIFIED
    else:
        status = EvidenceClaimStatus.VERIFIED

    can_influence = status in {
        EvidenceClaimStatus.VERIFIED,
        EvidenceClaimStatus.PARTIALLY_VERIFIED,
        EvidenceClaimStatus.CONFLICTING,
    }

    return VerifiedEvidenceClaim(
        claim_id=candidate.claim_id,
        claim_text=candidate.claim_text,
        claim_type=candidate.claim_type,
        pmid=candidate.pmid,
        status=status,
        direction=candidate.direction,
        source_excerpt=candidate.source_excerpt,
        study_design=candidate.study_design,
        population=candidate.population,
        intervention=candidate.intervention,
        comparator=candidate.comparator,
        endpoints=candidate.endpoints,
        numeric_results=candidate.numeric_results,
        applicability=candidate.applicability,
        findings=findings,
        can_influence_synthesis=can_influence,
    )


def verify_evidence_claims(
    candidates: list[EvidenceClaimCandidate],
    sources: list[EvidenceSourceSnapshot],
) -> EvidenceVerifierReport:
    source_by_pmid = {source.pmid: source for source in sources}
    claims = [verify_claim(candidate, source_by_pmid.get(candidate.pmid)) for candidate in candidates]

    counts = {
        EvidenceClaimStatus.VERIFIED: 0,
        EvidenceClaimStatus.PARTIALLY_VERIFIED: 0,
        EvidenceClaimStatus.CONFLICTING: 0,
        EvidenceClaimStatus.REJECTED: 0,
        EvidenceClaimStatus.UNVERIFIED: 0,
    }
    for claim in claims:
        counts[claim.status] += 1

    any_hard_failure = any(claim.status in {EvidenceClaimStatus.REJECTED, EvidenceClaimStatus.UNVERIFIED} for claim in claims)
    any_limited = any(claim.status in {EvidenceClaimStatus.PARTIALLY_VERIFIED, EvidenceClaimStatus.CONFLICTING} for claim in claims)

    if not claims or all(claim.status in {EvidenceClaimStatus.REJECTED, EvidenceClaimStatus.UNVERIFIED} for claim in claims):
        report_status = "verification_failed"
    elif any_hard_failure or any_limited:
        report_status = "completed_with_limitations"
    else:
        report_status = "completed"

    can_support = bool(claims) and all(
        claim.status in {EvidenceClaimStatus.VERIFIED, EvidenceClaimStatus.PARTIALLY_VERIFIED, EvidenceClaimStatus.CONFLICTING}
        for claim in claims
    ) and any(claim.can_influence_synthesis for claim in claims)

    limitations = [
        "Verification is limited to the supplied frozen source text and structured human-reviewed claim record.",
        "Abstract-level verification does not substitute for full-text appraisal when full-text methods or results are needed.",
        "A verified source span establishes provenance, not causal validity, guideline status, or patient-specific treatment appropriateness.",
    ]
    if counts[EvidenceClaimStatus.CONFLICTING]:
        limitations.append("Contradictory or mixed evidence must remain visible to downstream synthesis and cannot be silently resolved by vote counting.")

    return EvidenceVerifierReport(
        verifier_version=VERIFIER_VERSION,
        status=report_status,
        claims=claims,
        verified_count=counts[EvidenceClaimStatus.VERIFIED],
        partially_verified_count=counts[EvidenceClaimStatus.PARTIALLY_VERIFIED],
        conflicting_count=counts[EvidenceClaimStatus.CONFLICTING],
        rejected_count=counts[EvidenceClaimStatus.REJECTED],
        unverified_count=counts[EvidenceClaimStatus.UNVERIFIED],
        can_support_clinical_synthesis=can_support,
        limitations=limitations,
        summary=(
            f"Verified {counts[EvidenceClaimStatus.VERIFIED]} claim(s), partially verified "
            f"{counts[EvidenceClaimStatus.PARTIALLY_VERIFIED]}, conflicting {counts[EvidenceClaimStatus.CONFLICTING]}, "
            f"unverified {counts[EvidenceClaimStatus.UNVERIFIED]}, rejected {counts[EvidenceClaimStatus.REJECTED]}."
        ),
    )
