from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GoldCase:
    case_id: str
    title: str
    target_failure_mode: str
    narrative: str
    expected_diagnosis: str
    expected_disease_state: str | None
    expected_ecog: str | None
    expected_molecular_genes: tuple[str, ...] = ()
    expected_treatments: tuple[str, ...] = ()
    expected_missing_fields: tuple[str, ...] = ()
    expected_conflict_fields: tuple[str, ...] = ()
    prohibited_confirmed_values: tuple[str, ...] = ()
    notes: str = ""


CASES: tuple[GoldCase, ...] = (
    GoldCase(
        case_id="Q01",
        title="Baseline relapsed AML",
        target_failure_mode="Straightforward extraction",
        narrative=(
            "A 61-year-old man with acute myeloid leukemia is presented for tumor board review. "
            "He achieved complete remission after induction with cytarabine and daunorubicin, followed by consolidation. "
            "He now has relapsed AML. ECOG performance status is 1. "
            "Bone marrow biopsy shows recurrent AML with 48% blasts. Molecular testing detects FLT3-ITD with VAF 31%. "
            "The clinical question is management of relapsed FLT3-mutated AML."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="relapsed",
        expected_ecog="1",
        expected_molecular_genes=("FLT3",),
        expected_treatments=("cytarabine", "daunorubicin"),
    ),
    GoldCase(
        case_id="Q02",
        title="AML with critical missing data",
        target_failure_mode="Missing-information detection",
        narrative=(
            "A 74-year-old woman has newly diagnosed acute myeloid leukemia with 36% marrow blasts. "
            "NPM1 mutation is detected. The note does not report ECOG performance status or creatinine/renal function. "
            "No treatment has started. The board is asked to discuss initial management."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="newly diagnosed",
        expected_ecog=None,
        expected_molecular_genes=("NPM1",),
        expected_missing_fields=("performance", "ecog", "renal", "creatinine"),
        prohibited_confirmed_values=("ECOG 0", "ECOG 1", "normal renal function"),
    ),
    GoldCase(
        case_id="Q03",
        title="Conflicting AML pathology",
        target_failure_mode="Contradiction preservation",
        narrative=(
            "Outside marrow pathology dated June 2 was interpreted as myelodysplastic syndrome with excess blasts, 14% blasts. "
            "Repeat marrow at the referral center dated June 12 was interpreted as acute myeloid leukemia with 24% blasts. "
            "The discrepancy has not been resolved. ECOG is 2. The board question is how to proceed while pathology review is pending."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state=None,
        expected_ecog="2",
        expected_conflict_fields=("diagnosis", "pathology", "blasts"),
    ),
    GoldCase(
        case_id="Q04",
        title="FLT3 pending, not positive",
        target_failure_mode="Pending-result non-inference",
        narrative=(
            "A 58-year-old man has newly diagnosed acute myeloid leukemia. Cytogenetics are pending. "
            "FLT3 testing has been sent and remains pending; no FLT3 result is available. ECOG is 0. "
            "The clinical question is induction planning while molecular results are pending."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="newly diagnosed",
        expected_ecog="0",
        expected_missing_fields=("flt3", "cytogenetic"),
        prohibited_confirmed_values=("FLT3-ITD", "FLT3 positive", "FLT3 mutated"),
    ),
    GoldCase(
        case_id="Q05",
        title="Complex AML treatment chronology",
        target_failure_mode="Treatment chronology",
        narrative=(
            "A 66-year-old woman with AML received azacitidine plus venetoclax beginning January 2025 and achieved CR. "
            "Disease relapsed in October 2025. She then received FLAG-IDA in November 2025 but had refractory disease. "
            "In January 2026 she started gilteritinib after FLT3-ITD was detected. ECOG is 1. "
            "The board is asked to review options after progression on gilteritinib."
        ),
        expected_diagnosis="aml",
        expected_disease_state="progression",
        expected_ecog="1",
        expected_molecular_genes=("FLT3",),
        expected_treatments=("azacitidine", "venetoclax", "FLAG-IDA", "gilteritinib"),
    ),
    GoldCase(
        case_id="Q06",
        title="Variant without established actionability",
        target_failure_mode="Molecular over-interpretation guardrail",
        narrative=(
            "A 49-year-old woman has relapsed AML. Sequencing reports a DNMT3A R882H variant at VAF 18%. "
            "The molecular report does not state that this variant predicts sensitivity to any specific therapy. ECOG is 1. "
            "The clinical question is treatment selection for relapsed AML."
        ),
        expected_diagnosis="aml",
        expected_disease_state="relapsed",
        expected_ecog="1",
        expected_molecular_genes=("DNMT3A",),
        prohibited_confirmed_values=("actionable", "targeted therapy indicated", "predicts sensitivity"),
    ),
    GoldCase(
        case_id="Q07",
        title="Lymphoma staging conflict",
        target_failure_mode="Conflicting stage information",
        narrative=(
            "A 63-year-old man has diffuse large B-cell lymphoma. The oncology clinic note lists stage III disease. "
            "The PET/CT report describes extranodal liver involvement and labels the disease stage IV. "
            "The staging discrepancy is unresolved. ECOG is 1. R-CHOP has not yet started."
        ),
        expected_diagnosis="diffuse large b-cell lymphoma",
        expected_disease_state=None,
        expected_ecog="1",
        expected_conflict_fields=("stage",),
    ),
    GoldCase(
        case_id="Q08",
        title="Myeloma with transplant and multiple prior regimens",
        target_failure_mode="Longitudinal treatment and transplant extraction",
        narrative=(
            "A 59-year-old woman with multiple myeloma received VRd induction in 2022, then autologous stem cell transplant in February 2023, "
            "followed by lenalidomide maintenance. She relapsed in 2025 and received daratumumab, carfilzomib and dexamethasone. "
            "She now has progressive disease. ECOG is 1. The board is asked to review next-line therapy."
        ),
        expected_diagnosis="multiple myeloma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("VRd", "lenalidomide", "daratumumab", "carfilzomib", "dexamethasone"),
    ),
    GoldCase(
        case_id="Q09",
        title="Historical distractor contamination",
        target_failure_mode="Current-state vs historical-information separation",
        narrative=(
            "A 71-year-old man had prostate cancer treated with prostatectomy in 2012 and has no evidence of recurrence. "
            "He now has newly diagnosed mantle cell lymphoma confirmed by lymph-node biopsy. ECOG is 2. "
            "The tumor board question concerns initial management of mantle cell lymphoma."
        ),
        expected_diagnosis="mantle cell lymphoma",
        expected_disease_state="newly diagnosed",
        expected_ecog="2",
        prohibited_confirmed_values=("prostate cancer as current diagnosis", "recurrent prostate cancer"),
    ),
    GoldCase(
        case_id="Q10",
        title="Intentionally insufficient case",
        target_failure_mode="Abstention and non-inference",
        narrative=(
            "Referral note: patient with a suspected hematologic malignancy. Outside records have not arrived. "
            "No pathology report, molecular report, staging information, ECOG score, laboratory values, or treatment history is available. "
            "The referral asks for tumor board review once records are obtained."
        ),
        expected_diagnosis="suspected hematologic malignancy",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "molecular", "stage", "performance", "ecog", "laboratory", "treatment"),
        prohibited_confirmed_values=("AML", "lymphoma", "myeloma", "ECOG 0", "ECOG 1"),
        notes="Correct behavior is to preserve diagnostic uncertainty and report missing data rather than infer a disease subtype.",
    ),
)


def get_case(case_id: str) -> GoldCase:
    for case in CASES:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)
