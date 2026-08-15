from hashlib import sha256

from schemas.evidence_verifier import (
    EvidenceClaimCandidate,
    EvidenceClaimStatus,
    EvidenceClaimType,
    EvidenceDirection,
    EvidenceSourceSnapshot,
    VerificationFindingCode,
)
from services.evidence_verifier import verify_evidence_claims


ABSTRACT = (
    "In this synthetic randomized trial, 120 adults with relapsed AML were assigned to Treatment A or Treatment B. "
    "The primary endpoint was complete remission. Complete remission occurred in 48% with Treatment A and 31% with Treatment B."
)
HASH = sha256(ABSTRACT.encode("utf-8")).hexdigest()


def source(**kwargs):
    values = dict(
        pmid="99900001",
        title="Synthetic trial",
        abstract_text=ABSTRACT,
        abstract_sha256=HASH,
        source_verified=True,
        publication_types=["Randomized Controlled Trial"],
    )
    values.update(kwargs)
    return EvidenceSourceSnapshot(**values)


def candidate(**kwargs):
    values = dict(
        claim_id="CLAIM-001",
        claim_text="Treatment A was associated with a higher complete-remission proportion than Treatment B in the reported study population.",
        claim_type=EvidenceClaimType.EFFICACY,
        pmid="99900001",
        abstract_sha256=HASH,
        source_excerpt="Complete remission occurred in 48% with Treatment A and 31% with Treatment B.",
        study_design="randomized trial",
        population="120 adults with relapsed AML",
        intervention="Treatment A",
        comparator="Treatment B",
        endpoints=["complete remission"],
        numeric_results=["48% vs 31%"],
        applicability="Directly relevant to a relapsed AML treatment question, but synthetic fixture only.",
        direction=EvidenceDirection.SUPPORTS,
        human_verified=True,
    )
    values.update(kwargs)
    return EvidenceClaimCandidate(**values)


def codes(report):
    return {finding.code for finding in report.claims[0].findings}


def test_fully_attested_exact_claim_verifies():
    report = verify_evidence_claims([candidate()], [source()])
    assert report.status == "completed"
    assert report.verified_count == 1
    assert report.claims[0].status == EvidenceClaimStatus.VERIFIED
    assert report.claims[0].can_influence_synthesis is True
    assert report.can_support_clinical_synthesis is True


def test_wrong_hash_rejects_claim():
    wrong = "0" * 64
    report = verify_evidence_claims([candidate(abstract_sha256=wrong)], [source()])
    assert report.claims[0].status == EvidenceClaimStatus.REJECTED
    assert VerificationFindingCode.ABSTRACT_HASH_MISMATCH in codes(report)
    assert report.can_support_clinical_synthesis is False


def test_non_exact_excerpt_rejects_claim():
    report = verify_evidence_claims([candidate(source_excerpt="48 percent versus 31 percent")], [source()])
    assert report.claims[0].status == EvidenceClaimStatus.REJECTED
    assert VerificationFindingCode.SOURCE_EXCERPT_NOT_EXACT in codes(report)


def test_human_review_required():
    report = verify_evidence_claims([candidate(human_verified=False)], [source()])
    assert report.claims[0].status == EvidenceClaimStatus.UNVERIFIED
    assert VerificationFindingCode.HUMAN_REVIEW_REQUIRED in codes(report)


def test_missing_design_blocks_verification():
    report = verify_evidence_claims([candidate(study_design=None)], [source()])
    assert report.claims[0].status == EvidenceClaimStatus.UNVERIFIED
    assert VerificationFindingCode.STUDY_DESIGN_MISSING in codes(report)


def test_missing_numeric_result_is_partial_not_silent_full_verification():
    report = verify_evidence_claims([candidate(numeric_results=[])], [source()])
    assert report.claims[0].status == EvidenceClaimStatus.PARTIALLY_VERIFIED
    assert VerificationFindingCode.NUMERIC_RESULTS_MISSING in codes(report)


def test_contradictory_direction_is_preserved():
    report = verify_evidence_claims([candidate(direction=EvidenceDirection.CONTRADICTS)], [source()])
    assert report.claims[0].status == EvidenceClaimStatus.CONFLICTING
    assert VerificationFindingCode.CONTRADICTION_PRESENT in codes(report)


def test_unretrieved_pmid_rejects():
    report = verify_evidence_claims([candidate(pmid="99900002")], [source()])
    assert report.claims[0].status == EvidenceClaimStatus.REJECTED
    assert VerificationFindingCode.PMID_NOT_RETRIEVED in codes(report)


def test_same_input_is_deterministic():
    first = verify_evidence_claims([candidate()], [source()]).model_dump(mode="json")
    second = verify_evidence_claims([candidate()], [source()]).model_dump(mode="json")
    assert first == second
