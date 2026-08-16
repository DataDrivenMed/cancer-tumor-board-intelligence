from __future__ import annotations

from datetime import date

from agents.guideline import GuidelineEvidenceStore
from schemas.guideline import (
    GuidanceRecommendation,
    GuidanceSource,
    GuidanceSourceType,
    GuidanceStrength,
)


ELN_2022_URL = (
    "https://ashpublications.org/blood/article/140/12/1345/485817/"
    "Diagnosis-and-management-of-AML-in-adults-2022"
)


def public_eln_aml_store() -> GuidelineEvidenceStore:
    """Bounded machine-processable AML guidance derived from the open-access ELN 2022 report.

    This is intentionally not a scraped copy of the article. It contains a narrowly
    scoped, source-located consensus statement needed for the first AML product
    pathway. The recommendation text is a local paraphrase; the source excerpt is a
    short exact anchor used for verification and attribution.
    """

    source = GuidanceSource(
        source_id="ELN-AML-2022",
        title="Diagnosis and management of AML in adults: 2022 recommendations from an international expert panel on behalf of the ELN",
        organization="European LeukemiaNet",
        source_type=GuidanceSourceType.CONSENSUS_GUIDELINE,
        jurisdiction="international",
        url=ELN_2022_URL,
        version="2022",
        publication_date=date(2022, 9, 22),
        accessed_date=date(2026, 8, 16),
        license_status="public",
        verified=True,
        content_hash=None,
    )

    flt3_relapse = GuidanceRecommendation(
        recommendation_id="ELN2022-RR-FLT3-GILTERITINIB",
        source_id=source.source_id,
        disease_terms=["acute myeloid leukemia", "aml"],
        disease_states=["relapsed", "refractory", "relapsed refractory"],
        question_domains=["treatment_management", "molecular_management"],
        required_molecular_terms=["FLT3"],
        recommendation_text=(
            "For relapsed or refractory AML with a verified FLT3 mutation, discuss gilteritinib as a consensus-supported salvage option, "
            "with treatment selection remaining conditional on prior therapy, current disease biology, transplant strategy, patient fitness, safety review, and clinician adjudication."
        ),
        source_excerpt="Gilteritinib (AML with FLT3 mutation)",
        source_locator="Relapsed and refractory disease; Table 10, common salvage regimens",
        strength=GuidanceStrength.NOT_STATED,
        evidence_level="ELN 2022 international expert-panel recommendation",
        conditions=[
            "FLT3 mutation must be represented with verified case provenance.",
            "Repeat molecular evaluation at relapse should be considered because actionable clones can evolve.",
            "Treatment choice must account for prior FLT3-inhibitor exposure, patient fitness, transplant candidacy, and current safety constraints.",
        ],
        exclusions=[
            "Do not infer suitability when FLT3 status is absent, unverified, or discordant.",
            "This consensus statement does not establish patient-specific treatment eligibility or dosing."
        ],
        source_verified=True,
    )

    return GuidelineEvidenceStore(
        sources=(source,),
        recommendations=(flt3_relapse,),
    )
