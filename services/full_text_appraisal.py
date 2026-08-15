from __future__ import annotations

from hashlib import sha256

from schemas.full_text_appraisal import (
    AppraisalStatus,
    FullTextAppraisalCandidate,
    FullTextAppraisalFinding,
    FullTextAppraisalReport,
    FullTextFindingCode,
    FullTextSourceSnapshot,
    RiskOfBiasJudgement,
)


APPRAISER_VERSION = "1.0.0"


def normalized_sha256(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return sha256(normalized.encode("utf-8")).hexdigest()


def _finding(code: FullTextFindingCode, message: str, *, field_path: str | None = None, severity: str = "error") -> FullTextAppraisalFinding:
    return FullTextAppraisalFinding(code=code, severity=severity, message=message, field_path=field_path)


def _exact(text: str, excerpt: str) -> bool:
    return bool(excerpt.strip()) and excerpt in text


def appraise_full_text(source: FullTextSourceSnapshot, candidate: FullTextAppraisalCandidate) -> FullTextAppraisalReport:
    """Deterministically verify a human-authored full-text appraisal package.

    This service does not infer PICO, risk of bias, applicability, or effect sizes.
    It verifies that a reviewed appraisal is internally complete and that every
    asserted evidence span is an exact substring of the frozen full-text snapshot.
    """
    findings: list[FullTextAppraisalFinding] = []
    text = source.full_text

    if not text.strip():
        findings.append(_finding(FullTextFindingCode.FULL_TEXT_EMPTY, "Full-text source is empty."))

    observed_hash = normalized_sha256(text)
    if observed_hash != source.full_text_sha256:
        findings.append(_finding(FullTextFindingCode.FULL_TEXT_HASH_MISMATCH, "Full-text SHA-256 does not match the frozen source snapshot."))

    if source.pmid != candidate.pmid:
        findings.append(_finding(FullTextFindingCode.PMID_MISMATCH, "Candidate PMID does not match the full-text source PMID."))

    if not source.source_verified or not candidate.human_verified:
        findings.append(_finding(FullTextFindingCode.HUMAN_REVIEW_REQUIRED, "Source and appraisal candidate must both be explicitly human verified."))

    pico_fields = {
        "population": candidate.pico.population,
        "intervention": candidate.pico.intervention,
        "comparator": candidate.pico.comparator,
        "outcome": candidate.pico.outcome,
    }
    pico_verified = True
    for name, field in pico_fields.items():
        if field is None:
            if name in {"intervention", "comparator"}:
                continue
            pico_verified = False
            findings.append(_finding(FullTextFindingCode.PICO_INCOMPLETE, f"PICO field {name} is missing.", field_path=f"pico.{name}"))
            continue
        if not _exact(text, field.source_excerpt):
            pico_verified = False
            findings.append(_finding(FullTextFindingCode.PICO_EXCERPT_NOT_EXACT, f"PICO {name} excerpt is not an exact substring of the frozen full text.", field_path=f"pico.{name}.source_excerpt"))

    endpoints_verified = 0
    for idx, endpoint in enumerate(candidate.endpoints):
        if not endpoint.name.strip():
            findings.append(_finding(FullTextFindingCode.ENDPOINT_MISSING, "Endpoint name is missing.", field_path=f"endpoints.{idx}.name"))
            continue
        if not _exact(text, endpoint.source_excerpt):
            findings.append(_finding(FullTextFindingCode.ENDPOINT_EXCERPT_NOT_EXACT, f"Endpoint excerpt for {endpoint.name} is not exact.", field_path=f"endpoints.{idx}.source_excerpt"))
            continue
        endpoints_verified += 1

    effects_verified = 0
    for idx, effect in enumerate(candidate.effect_estimates):
        missing = not effect.endpoint_name.strip() or not effect.effect_measure.strip() or not effect.effect_value.strip()
        if missing:
            findings.append(_finding(FullTextFindingCode.EFFECT_ESTIMATE_MISSING, "Effect estimate lacks endpoint, measure, or value.", field_path=f"effect_estimates.{idx}"))
            continue
        if not _exact(text, effect.source_excerpt):
            findings.append(_finding(FullTextFindingCode.EFFECT_EXCERPT_NOT_EXACT, f"Effect estimate excerpt for {effect.endpoint_name} is not exact.", field_path=f"effect_estimates.{idx}.source_excerpt"))
            continue
        effects_verified += 1

    rob = candidate.risk_of_bias
    rob_verified = bool(rob.human_verified and rob.overall != RiskOfBiasJudgement.UNCLEAR)
    if not rob_verified:
        findings.append(_finding(FullTextFindingCode.RISK_OF_BIAS_INCOMPLETE, "Risk-of-bias assessment requires human verification and a non-unclear overall judgement.", field_path="risk_of_bias", severity="warning"))

    app = candidate.applicability
    applicability_verified = bool(app.human_verified and app.judgement.value != "unclear")
    if not applicability_verified:
        findings.append(_finding(FullTextFindingCode.APPLICABILITY_INCOMPLETE, "Applicability assessment requires human verification and a non-unclear judgement.", field_path="applicability", severity="warning"))

    hard_errors = [f for f in findings if f.severity == "error"]
    core_verified = not hard_errors and pico_verified and endpoints_verified == len(candidate.endpoints)

    linked_claims: list[str] = []
    if core_verified and rob_verified and applicability_verified:
        linked_claims = list(candidate.linked_claim_ids)
    elif candidate.linked_claim_ids:
        findings.append(_finding(FullTextFindingCode.CLAIM_NOT_FULL_TEXT_VERIFIED, "Linked claims remain ineligible for full-text promotion because appraisal gates are incomplete.", field_path="linked_claim_ids", severity="warning"))

    if hard_errors:
        status = AppraisalStatus.REJECTED
        can_influence = False
    elif core_verified and rob_verified and applicability_verified:
        status = AppraisalStatus.VERIFIED
        can_influence = True
    elif core_verified:
        status = AppraisalStatus.PARTIALLY_VERIFIED
        can_influence = False
    else:
        status = AppraisalStatus.UNVERIFIED
        can_influence = False

    limitations = [
        "This layer verifies a human-authored appraisal against a frozen full-text snapshot; it does not autonomously infer study validity.",
        "Risk-of-bias and applicability judgements remain reviewer-dependent and require later inter-reviewer validation for formal qualification.",
        "A verified appraisal does not by itself establish a patient-specific treatment recommendation.",
    ]

    return FullTextAppraisalReport(
        appraisal_id=candidate.appraisal_id,
        pmid=candidate.pmid,
        status=status,
        findings=findings,
        pico_verified=pico_verified and not any(f.code == FullTextFindingCode.PICO_EXCERPT_NOT_EXACT for f in findings),
        endpoints_verified=endpoints_verified,
        effect_estimates_verified=effects_verified,
        risk_of_bias_verified=rob_verified,
        applicability_verified=applicability_verified,
        linked_claims_verified_for_full_text=linked_claims,
        can_influence_synthesis=can_influence,
        limitations=limitations,
        summary=(
            f"Full-text appraisal {status.value}: PICO verified={pico_verified}; "
            f"endpoints={endpoints_verified}/{len(candidate.endpoints)}; "
            f"effects={effects_verified}/{len(candidate.effect_estimates)}; "
            f"risk-of-bias verified={rob_verified}; applicability verified={applicability_verified}."
        ),
    )
