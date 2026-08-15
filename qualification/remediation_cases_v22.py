from __future__ import annotations

from qualification.cases import GoldCase


REMEDIATION_CASES_V22: tuple[GoldCase, ...] = (
    GoldCase(
        case_id="S01",
        title="Metastatic cholangiocarcinoma with hepatic lesions",
        target_failure_mode="Canonical metastatic-state normalization",
        narrative=(
            "A 63-year-old woman has biopsy-confirmed intrahepatic cholangiocarcinoma with multiple hepatic metastases and peritoneal metastases. "
            "ECOG is 1. No systemic therapy has started."
        ),
        expected_diagnosis="intrahepatic cholangiocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog="1",
        require_no_treatments=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S02",
        title="Metastatic bladder carcinoma with pulmonary metastases",
        target_failure_mode="Metastatic-state canonicalization across organ sites",
        narrative=(
            "A 70-year-old man has urothelial carcinoma of the bladder with pulmonary metastases documented on CT. ECOG is 2. "
            "No systemic treatment has begun."
        ),
        expected_diagnosis="urothelial carcinoma",
        expected_disease_state="metastatic",
        expected_ecog="2",
        require_no_treatments=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S03",
        title="Suspected metastatic carcinoma awaiting tissue diagnosis",
        target_failure_mode="Diagnostic certainty separated from disease state",
        narrative=(
            "Imaging demonstrates liver and lung lesions and metastatic carcinoma is suspected. Tissue diagnosis is pending and the primary site remains unknown. "
            "Molecular testing is unavailable and ECOG is not documented. No therapy has started."
        ),
        expected_diagnosis="suspected metastatic carcinoma",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "molecular", "performance"),
        require_no_molecular_findings=True,
        require_no_treatments=True,
        allow_null_diagnosis_if_uncertain=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S04",
        title="Remote metastatic colon cancer with new lymphoma",
        target_failure_mode="Historical metastatic contamination guard",
        narrative=(
            "A 72-year-old woman had metastatic colon cancer treated in 2010 and has had no evidence of recurrence for more than a decade. "
            "She now has newly diagnosed diffuse large B-cell lymphoma confirmed by lymph-node biopsy. ECOG is 1."
        ),
        expected_diagnosis="diffuse large b-cell lymphoma",
        expected_disease_state="newly diagnosed",
        expected_ecog="1",
        strict_core_gate=True,
        prohibited_confirmed_values=("current metastatic colon cancer", "recurrent colon cancer"),
    ),
    GoldCase(
        case_id="S05",
        title="Ovarian cancer with radiographic progression",
        target_failure_mode="Exact-source progression provenance repair",
        narrative=(
            "A 66-year-old woman has high-grade serous ovarian carcinoma. ECOG is 1. She previously received carboplatin plus paclitaxel. "
            "Current CT demonstrates radiographic progression."
        ),
        expected_diagnosis="high-grade serous ovarian carcinoma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("carboplatin", "paclitaxel"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S06",
        title="AML multi-phase treatment chronology",
        target_failure_mode="Induction consolidation maintenance salvage completeness",
        narrative=(
            "A 60-year-old man with acute myeloid leukemia received daunorubicin plus cytarabine induction, followed by high-dose cytarabine consolidation, then oral azacitidine maintenance. "
            "After relapse he started venetoclax plus azacitidine. ECOG is 1 and disease is relapsed."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="relapsed",
        expected_ecog="1",
        expected_treatments=("daunorubicin", "cytarabine", "high-dose cytarabine", "oral azacitidine", "venetoclax", "azacitidine"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S07",
        title="Myeloma with transplant maintenance and later regimens",
        target_failure_mode="Intermediate maintenance episode completeness",
        narrative=(
            "A 57-year-old woman with multiple myeloma received VRd induction, underwent autologous stem cell transplant, and then received lenalidomide maintenance. "
            "At relapse she received daratumumab plus pomalidomide plus dexamethasone. After subsequent progression she started carfilzomib plus dexamethasone. "
            "Disease is progressive and ECOG is 1."
        ),
        expected_diagnosis="multiple myeloma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("VRd", "lenalidomide", "daratumumab", "pomalidomide", "dexamethasone", "carfilzomib", "dexamethasone"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S08",
        title="Resected renal pelvis carcinoma with planned therapy",
        target_failure_mode="Planned therapy not treated as administered",
        narrative=(
            "A 68-year-old man has resected high-grade urothelial carcinoma of the renal pelvis. Adjuvant nivolumab is recommended but has not started. "
            "There is no prior systemic therapy. ECOG is 0."
        ),
        expected_diagnosis="urothelial carcinoma",
        expected_disease_state="resected",
        expected_ecog="0",
        require_no_treatments=True,
        strict_core_gate=True,
        prohibited_confirmed_values=("nivolumab started", "nivolumab administered"),
    ),
    GoldCase(
        case_id="S09",
        title="CUP with tissue diagnosis pending",
        target_failure_mode="Missing pathology category and uncertainty",
        narrative=(
            "Metastatic carcinoma is suspected after PET/CT showed bone and liver lesions. The tissue diagnosis remains pending and the primary site is unknown. "
            "ECOG is not documented and molecular profiling is unavailable. No treatment has started."
        ),
        expected_diagnosis="suspected metastatic carcinoma",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "molecular", "performance"),
        require_no_molecular_findings=True,
        require_no_treatments=True,
        allow_null_diagnosis_if_uncertain=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S10",
        title="Lung adenocarcinoma with unresolved stage discrepancy",
        target_failure_mode="Stage conflict separated from disease state",
        narrative=(
            "A 65-year-old woman has biopsy-confirmed lung adenocarcinoma. The clinic note records stage IIIA, while the PET/CT report identifies a distant bone metastasis and labels stage IV. "
            "The staging discrepancy remains unresolved. ECOG is 1."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state=None,
        expected_ecog="1",
        expected_conflict_fields=("stage",),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S11",
        title="Metastatic prostate cancer with radiographic progression",
        target_failure_mode="Composite excerpt exact provenance repair",
        narrative=(
            "A 73-year-old man has metastatic castration-resistant prostate adenocarcinoma. ECOG is 1. He previously received enzalutamide followed by cabazitaxel. "
            "Current imaging demonstrates radiographic progression."
        ),
        expected_diagnosis="prostate adenocarcinoma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("enzalutamide", "cabazitaxel"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="S12",
        title="New gastric cancer after remote metastatic melanoma",
        target_failure_mode="Current diagnosis temporal separation",
        narrative=(
            "A 69-year-old man had metastatic melanoma treated in 2012 and has had no active melanoma for years. He now has newly diagnosed gastric adenocarcinoma confirmed by biopsy. "
            "ECOG is 0."
        ),
        expected_diagnosis="gastric adenocarcinoma",
        expected_disease_state="newly diagnosed",
        expected_ecog="0",
        strict_core_gate=True,
        prohibited_confirmed_values=("current metastatic melanoma", "recurrent melanoma"),
    ),
)

REMEDIATION_REPEAT_CASE_IDS_V22: tuple[str, ...] = ("S01", "S03", "S05", "S06", "S07", "S10")
REMEDIATION_REPEAT_COUNT_V22 = 3


def get_remediation_case_v22(case_id: str) -> GoldCase:
    for case in REMEDIATION_CASES_V22:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)
