from __future__ import annotations

from schemas.case import CancerTumorBoardCase, MolecularFinding
from schemas.translational import (
    TranslationalEvidenceRecord,
    TranslationalEvidenceStore,
    TranslationalEvidenceTier,
    TranslationalFinding,
    TranslationalReport,
)


AGENT_ID = "translational"
AGENT_VERSION = "1.0.0"


def _norm(text: str | None) -> str:
    return " ".join((text or "").lower().replace("_", " ").split())


def _finding_terms(finding: MolecularFinding) -> set[str]:
    terms = {
        _norm(finding.gene),
        _norm(finding.alteration_type),
        _norm(finding.hgvs_c),
        _norm(finding.hgvs_p),
    }
    return {term for term in terms if term}


def _record_matches(case: CancerTumorBoardCase, finding: MolecularFinding, record: TranslationalEvidenceRecord) -> bool:
    if not record.source_verified or not record.human_verified:
        return False

    if record.gene and _norm(record.gene) != _norm(finding.gene):
        return False

    diagnosis = _norm(str(case.diagnosis.value or ""))
    if record.disease_terms:
        matched_disease = any(
            _norm(term) and (_norm(term) in diagnosis or diagnosis in _norm(term))
            for term in record.disease_terms
        )
        if not matched_disease:
            return False

    if record.alteration_terms:
        represented_terms = _finding_terms(finding)
        if not any(
            any(_norm(term) in represented or represented in _norm(term) for represented in represented_terms)
            for term in record.alteration_terms
            if _norm(term)
        ):
            return False

    return True


def _strongest_tier(records: list[TranslationalEvidenceRecord]) -> TranslationalEvidenceTier | None:
    rank = {
        TranslationalEvidenceTier.HYPOTHESIS_ONLY: 0,
        TranslationalEvidenceTier.T3_IN_VITRO_PRECLINICAL: 1,
        TranslationalEvidenceTier.T2_IN_VIVO_PRECLINICAL: 2,
        TranslationalEvidenceTier.T1_HUMAN_TRANSLATIONAL: 3,
    }
    if not records:
        return None
    return max((record.evidence_tier for record in records), key=lambda tier: rank[tier])


class TranslationalBiologyAgent:
    """Evidence-bounded translational specialist.

    This agent summarizes verified mechanistic and preclinical/human-translational
    evidence for represented molecular findings. It never upgrades mechanistic,
    preclinical, or translational evidence into clinical actionability.
    """

    agent_id = AGENT_ID
    agent_version = AGENT_VERSION

    def __init__(self, store: TranslationalEvidenceStore | None = None, *, production_mode: bool = True) -> None:
        self.store = store or TranslationalEvidenceStore()
        self.production_mode = production_mode

    def run(self, case: CancerTumorBoardCase) -> TranslationalReport:
        if case.disease_program != "hematologic_malignancy":
            return TranslationalReport(
                case_id=case.case_id,
                status="abstain_domain",
                summary="Translational Biology Agent v1 is restricted to hematologic malignancy cases.",
                limitations=["Case is outside the v1 hematologic-malignancy domain."],
            )

        if not case.molecular_findings:
            return TranslationalReport(
                case_id=case.case_id,
                status="no_evidence_found",
                summary="No represented molecular finding is available for translational matching.",
                limitations=["Absence of represented findings does not establish a negative molecular evaluation."],
            )

        usable_records = [
            record
            for record in self.store.records
            if record.source_verified
            and record.human_verified
            and not (self.production_mode and record.synthetic)
        ]
        if not usable_records:
            return TranslationalReport(
                case_id=case.case_id,
                status="source_unavailable",
                summary="No verified production translational evidence records are available.",
                limitations=[
                    "The agent will not generate mechanistic hypotheses from model memory.",
                    "Mechanistic or preclinical evidence cannot establish clinical actionability.",
                ],
            )

        findings: list[TranslationalFinding] = []
        any_match = False
        any_human_translational = False

        for molecular_finding in case.molecular_findings:
            matched = [
                record
                for record in usable_records
                if _record_matches(case, molecular_finding, record)
            ]
            any_match = any_match or bool(matched)
            strongest = _strongest_tier(matched)
            human_support = strongest == TranslationalEvidenceTier.T1_HUMAN_TRANSLATIONAL
            any_human_translational = any_human_translational or human_support

            findings.append(
                TranslationalFinding(
                    subject=molecular_finding.hgvs_p or molecular_finding.hgvs_c or molecular_finding.alteration_type or molecular_finding.gene,
                    matched_evidence_ids=[record.evidence_id for record in matched],
                    evidence_tiers=[record.evidence_tier for record in matched],
                    directions=[record.direction for record in matched],
                    mechanisms=sorted({record.mechanism for record in matched}),
                    interventions=sorted({record.intervention for record in matched if record.intervention}),
                    strongest_tier=strongest,
                    human_translational_support=human_support,
                    clinical_actionability_claim=False,
                    limitations=[] if matched else [
                        "No verified disease- and alteration-matched translational record was found; no mechanism was inferred."
                    ],
                )
            )

        if not any_match:
            status = "no_evidence_found"
            summary = "Represented molecular findings were evaluated, but no verified disease- and alteration-matched translational records were found."
        else:
            status = "completed" if all(finding.matched_evidence_ids for finding in findings) else "completed_with_limitations"
            summary = f"Matched translational evidence for {sum(bool(f.matched_evidence_ids) for f in findings)} of {len(findings)} represented molecular finding(s)."

        return TranslationalReport(
            case_id=case.case_id,
            status=status,
            findings=findings,
            limitations=[
                "Translational evidence describes mechanism or experimental association and does not establish treatment efficacy, regulatory indication, or patient-level eligibility.",
                "Clinical actionability remains the responsibility of separately verified clinical evidence and the Molecular Interpretation Agent.",
            ],
            summary=summary,
            can_support_mechanistic_claim=any_match,
            can_support_clinical_actionability_claim=False,
        )
