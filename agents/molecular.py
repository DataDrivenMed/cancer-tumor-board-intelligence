from __future__ import annotations

from schemas.case import CancerTumorBoardCase, MolecularFinding
from schemas.molecular import (
    ClinicalActionability,
    MolecularEvidenceDirection,
    MolecularEvidenceRecord,
    MolecularEvidenceStore,
    MolecularFindingInterpretation,
    MolecularReport,
)
from services.oncology_programs import is_registered_oncology_program


AGENT_ID = "molecular"
AGENT_VERSION = "1.1.0"


def _norm(text: str | None) -> str:
    return " ".join((text or "").lower().replace("_", " ").split())


def _finding_terms(finding: MolecularFinding) -> set[str]:
    terms = {_norm(finding.gene), _norm(finding.alteration_type), _norm(finding.hgvs_c), _norm(finding.hgvs_p)}
    return {t for t in terms if t}


def _record_matches(case: CancerTumorBoardCase, finding: MolecularFinding, record: MolecularEvidenceRecord) -> bool:
    if not record.source_verified or not record.human_verified:
        return False
    if _norm(record.gene) != _norm(finding.gene):
        return False

    diagnosis = _norm(str(case.diagnosis.value or ""))
    if record.disease_terms and not any(_norm(term) in diagnosis or diagnosis in _norm(term) for term in record.disease_terms if _norm(term)):
        return False

    if record.alteration_terms:
        finding_terms = _finding_terms(finding)
        if not any(
            any(_norm(term) in fterm or fterm in _norm(term) for fterm in finding_terms)
            for term in record.alteration_terms
            if _norm(term)
        ):
            return False
    return True


def _max_actionability(records: list[MolecularEvidenceRecord]) -> ClinicalActionability:
    rank = {
        ClinicalActionability.UNKNOWN: 0,
        ClinicalActionability.NOT_ESTABLISHED: 1,
        ClinicalActionability.INVESTIGATIONAL: 2,
        ClinicalActionability.EMERGING: 3,
        ClinicalActionability.ESTABLISHED: 4,
    }
    return max((r.actionability for r in records), key=lambda x: rank[x], default=ClinicalActionability.UNKNOWN)


class MolecularInterpretationAgent:
    """Evidence-bounded pan-oncology molecular specialist."""

    agent_id = AGENT_ID
    agent_version = AGENT_VERSION

    def __init__(self, store: MolecularEvidenceStore | None = None, *, production_mode: bool = True) -> None:
        self.store = store or MolecularEvidenceStore()
        self.production_mode = production_mode

    def run(self, case: CancerTumorBoardCase) -> MolecularReport:
        if not is_registered_oncology_program(case.disease_program):
            return MolecularReport(
                case_id=case.case_id,
                status="abstain_domain",
                summary="Molecular Interpretation Agent received a case outside the registered oncology programs.",
                limitations=["The disease program must be classified into the governed pan-oncology registry before analysis."],
            )

        if not case.molecular_findings:
            return MolecularReport(
                case_id=case.case_id,
                status="no_evidence_found",
                summary="No molecular findings are represented in the canonical case.",
                limitations=["Absence of represented findings does not establish a negative molecular evaluation."],
            )

        usable_records = [
            r for r in self.store.records
            if r.source_verified and r.human_verified and not (self.production_mode and r.synthetic)
        ]
        if not usable_records:
            return MolecularReport(
                case_id=case.case_id,
                status="source_unavailable",
                summary="No verified production molecular evidence records are available.",
                limitations=[
                    "The agent will not infer molecular actionability from model knowledge or gene identity alone.",
                    "Mechanistic plausibility is not equivalent to clinical actionability.",
                ],
            )

        interpretations: list[MolecularFindingInterpretation] = []
        any_match = False
        any_actionable = False

        for finding in case.molecular_findings:
            matched = [r for r in usable_records if _record_matches(case, finding, r)]
            any_match = any_match or bool(matched)
            actionability = _max_actionability(matched)
            directions = [r.direction for r in matched]
            therapies = sorted({r.therapy for r in matched if r.therapy})

            established_or_emerging = actionability in {
                ClinicalActionability.ESTABLISHED,
                ClinicalActionability.EMERGING,
            }
            any_actionable = any_actionable or established_or_emerging

            interpretations.append(
                MolecularFindingInterpretation(
                    gene=finding.gene,
                    alteration=finding.hgvs_p or finding.hgvs_c or finding.alteration_type,
                    matched_evidence_ids=[r.evidence_id for r in matched],
                    evidence_directions=directions,
                    therapies=therapies,
                    biologic_relevance="supported" if matched else "uncertain",
                    clinical_actionability=actionability,
                    resistance_signal=MolecularEvidenceDirection.SUPPORTS_RESISTANCE in directions,
                    diagnostic_signal=MolecularEvidenceDirection.DIAGNOSTIC in directions,
                    prognostic_signal=MolecularEvidenceDirection.PROGNOSTIC in directions,
                    limitations=[] if matched else [
                        "No verified disease- and alteration-matched evidence record was found; no actionability inference was made."
                    ],
                    can_support_clinical_actionability_claim=established_or_emerging,
                )
            )

        if not any_match:
            status = "no_evidence_found"
            summary = "Molecular findings were recognized, but no verified disease- and alteration-matched evidence records were found."
        else:
            status = "completed" if all(i.matched_evidence_ids for i in interpretations) else "completed_with_limitations"
            summary = f"Interpreted {len(interpretations)} represented molecular finding(s) against the verified molecular evidence store."

        return MolecularReport(
            case_id=case.case_id,
            status=status,
            interpretations=interpretations,
            limitations=[
                "The agent does not infer germline status, pathogenicity, clonality, treatment eligibility, or regulatory indication beyond verified evidence records.",
                "Clinical actionability is disease-context specific and is kept separate from biological plausibility.",
            ],
            summary=summary,
            can_support_clinical_actionability_claim=any_actionable,
        )
