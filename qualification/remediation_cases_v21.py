from __future__ import annotations

from qualification.cases import GoldCase


REMEDIATION_CASES: tuple[GoldCase, ...] = (
    GoldCase(
        case_id="R01",
        title="Metastatic lung adenocarcinoma with bone disease",
        target_failure_mode="Canonical metastatic-state promotion",
        narrative=(
            "A 58-year-old woman has lung adenocarcinoma with biopsy-confirmed histology and multiple bone metastases on PET/CT. "
            "ECOG is 1. EGFR L858R is detected. She has not started systemic therapy. The board is reviewing first-line management."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog="1",
        expected_molecular_genes=("EGFR",),
        require_no_treatments=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="R02",
        title="Pancreatic adenocarcinoma with hepatic metastases",
        target_failure_mode="Metastatic state derived from explicit metastases wording",
        narrative=(
            "A 71-year-old man has biopsy-confirmed pancreatic ductal adenocarcinoma with hepatic metastases. "
            "ECOG performance status is not documented. No systemic therapy has started. The board is reviewing initial management."
        ),
        expected_diagnosis="pancreatic ductal adenocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog=None,
        expected_missing_fields=("performance",),
        require_no_treatments=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="R03",
        title="Renal cell carcinoma with pulmonary metastases",
        target_failure_mode="Cross-disease metastatic-state consistency",
        narrative=(
            "A 64-year-old man has clear cell renal cell carcinoma with pulmonary metastases documented on CT. "
            "ECOG is 1. He has not yet started systemic therapy."
        ),
        expected_diagnosis="clear cell renal cell carcinoma",
        expected_disease_state="metastatic",
        expected_ecog="1",
        require_no_treatments=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="R04",
        title="Suspected metastatic carcinoma before biopsy",
        target_failure_mode="Uncertainty preservation without disease-state overpromotion",
        narrative=(
            "Imaging shows multiple liver lesions and metastatic carcinoma is suspected, but the biopsy result has not returned. "
            "The primary site is unknown. Molecular testing and ECOG performance status are unavailable. No systemic treatment has started."
        ),
        expected_diagnosis="suspected metastatic carcinoma",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "molecular", "performance"),
        require_no_molecular_findings=True,
        require_no_treatments=True,
        allow_null_diagnosis_if_uncertain=True,
        strict_core_gate=True,
        prohibited_confirmed_values=("lung cancer", "colon cancer", "pancreatic cancer", "breast cancer"),
    ),
    GoldCase(
        case_id="R05",
        title="Remote metastatic breast cancer with new endometrial cancer",
        target_failure_mode="Historical metastatic-state contamination",
        narrative=(
            "A 67-year-old woman had metastatic breast cancer treated in 2011 and has had no evidence of active breast cancer for years. "
            "She now has newly diagnosed endometrioid endometrial carcinoma confirmed by biopsy. ECOG is 0. "
            "The board question concerns the new endometrial cancer."
        ),
        expected_diagnosis="endometrioid endometrial carcinoma",
        expected_disease_state="newly diagnosed",
        expected_ecog="0",
        strict_core_gate=True,
        prohibited_confirmed_values=("breast cancer as current diagnosis", "current metastatic breast cancer"),
    ),
    GoldCase(
        case_id="R06",
        title="AML with induction consolidation maintenance and salvage",
        target_failure_mode="Longitudinal treatment episode completeness",
        narrative=(
            "A 62-year-old man with acute myeloid leukemia received cytarabine and daunorubicin induction in 2023, followed by high-dose cytarabine consolidation. "
            "He then received oral azacitidine maintenance. After relapse in 2026, he started gilteritinib. "
            "He now has persistent disease and ECOG is 1. FLT3-ITD is detected."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="persistent",
        expected_ecog="1",
        expected_molecular_genes=("FLT3",),
        expected_treatments=("cytarabine", "daunorubicin", "high-dose cytarabine", "oral azacitidine", "gilteritinib"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="R07",
        title="Myeloma with intermediate maintenance and repeated dexamethasone",
        target_failure_mode="Intermediate treatment omission and repeated-agent chronology",
        narrative=(
            "A 59-year-old woman with multiple myeloma received Dara-VRd induction in 2022, underwent autologous stem cell transplant, then received lenalidomide maintenance. "
            "At relapse she received carfilzomib plus dexamethasone. After later progression she started pomalidomide, cyclophosphamide and dexamethasone. "
            "Disease is progressive and ECOG is 1."
        ),
        expected_diagnosis="multiple myeloma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("Dara-VRd", "lenalidomide", "carfilzomib", "dexamethasone", "pomalidomide", "cyclophosphamide", "dexamethasone"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="R08",
        title="Follicular lymphoma with maintenance between systemic regimens",
        target_failure_mode="Maintenance episode preservation",
        narrative=(
            "A 65-year-old man with follicular lymphoma received bendamustine plus rituximab and then rituximab maintenance. "
            "After histologic transformation to diffuse large B-cell lymphoma, he received R-CHOP. He now has progressive disease. ECOG is 2."
        ),
        expected_diagnosis="diffuse large b-cell lymphoma",
        expected_disease_state="progressive",
        expected_ecog="2",
        expected_treatments=("bendamustine", "rituximab", "rituximab maintenance", "R-CHOP"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="R09",
        title="Resected melanoma with planned adjuvant therapy",
        target_failure_mode="Resected-state representation and planned-vs-administered therapy",
        narrative=(
            "A 54-year-old woman has resected stage III cutaneous melanoma. Adjuvant nivolumab is recommended but has not yet started. "
            "There is no prior systemic therapy. ECOG is 0."
        ),
        expected_diagnosis="cutaneous melanoma",
        expected_disease_state="resected",
        expected_ecog="0",
        require_no_treatments=True,
        strict_core_gate=True,
        prohibited_confirmed_values=("nivolumab administered", "nivolumab started"),
    ),
    GoldCase(
        case_id="R10",
        title="Carcinoma of unknown primary with diagnostic uncertainty",
        target_failure_mode="Status-aware diagnosis equivalence",
        narrative=(
            "Metastatic carcinoma is suspected after imaging demonstrated liver and bone lesions, but tissue diagnosis is still pending and the primary site is unknown. "
            "Molecular testing is unavailable. ECOG performance status is not documented. No treatment has started."
        ),
        expected_diagnosis="suspected metastatic carcinoma",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "molecular", "performance"),
        require_no_molecular_findings=True,
        require_no_treatments=True,
        allow_null_diagnosis_if_uncertain=True,
        strict_core_gate=True,
        prohibited_confirmed_values=("lung cancer", "colon cancer", "pancreatic cancer", "breast cancer"),
    ),
    GoldCase(
        case_id="R11",
        title="Prostate cancer with radiographic progression",
        target_failure_mode="Disease-state semantic equivalence",
        narrative=(
            "A 75-year-old man has metastatic castration-resistant prostate adenocarcinoma. ECOG is 1. "
            "He previously received abiraterone followed by docetaxel. Current imaging demonstrates radiographic progression."
        ),
        expected_diagnosis="prostate adenocarcinoma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("abiraterone", "docetaxel"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="R12",
        title="Lung cancer with unresolved stage conflict",
        target_failure_mode="Conflict-preserving resolver abstention",
        narrative=(
            "A 69-year-old woman has biopsy-confirmed lung adenocarcinoma. The oncology note lists stage IIIB, while a subsequent PET/CT report identifies a distant adrenal metastasis and labels the disease stage IV. "
            "The discrepancy remains unresolved. ECOG is 1."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state=None,
        expected_ecog="1",
        expected_conflict_fields=("stage",),
        strict_core_gate=True,
    ),
)


REMEDIATION_REPEAT_CASE_IDS: tuple[str, ...] = ("R01", "R02", "R06", "R07", "R10", "R12")
REMEDIATION_REPEAT_COUNT = 3


def get_remediation_case(case_id: str) -> GoldCase:
    for case in REMEDIATION_CASES:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)
