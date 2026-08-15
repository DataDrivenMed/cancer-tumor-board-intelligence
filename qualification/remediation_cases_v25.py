from __future__ import annotations

from qualification.cases import GoldCase


REMEDIATION_CASES_V25: tuple[GoldCase, ...] = (
    GoldCase(
        case_id="Y01",
        title="Suspected metastatic carcinoma with unresolved tissue diagnosis",
        target_failure_mode="Uncertainty invariant plus diagnostic missingness ontology",
        narrative=(
            "CT demonstrates multiple hepatic lesions. Metastatic carcinoma is suspected, but core biopsy is pending and the primary site remains unknown. "
            "Comprehensive molecular profiling has not been performed. ECOG is not documented. No anticancer treatment has started."
        ),
        expected_diagnosis="metastatic carcinoma",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "molecular", "performance"),
        require_no_molecular_findings=True,
        require_no_treatments=True,
        allow_null_diagnosis_if_uncertain=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y02",
        title="New AML with multiple pending molecular tests",
        target_failure_mode="Molecular ontology classification",
        narrative=(
            "A 62-year-old woman has newly diagnosed acute myeloid leukemia confirmed on bone marrow examination. ECOG is 1. "
            "FLT3, NPM1, IDH1, IDH2, karyotype, and FISH results are pending. Induction treatment has not started."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="newly diagnosed",
        expected_ecog="1",
        expected_missing_fields=("molecular",),
        require_no_molecular_findings=True,
        require_no_treatments=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y03",
        title="New MDS with planned decitabine",
        target_failure_mode="Planned therapy excluded from administered history",
        narrative=(
            "A 74-year-old man has newly diagnosed, biopsy-confirmed myelodysplastic syndrome. ECOG is 2. Decitabine is recommended to begin next week but has not started. "
            "There is no prior disease-directed treatment."
        ),
        expected_diagnosis="myelodysplastic syndrome",
        expected_disease_state="newly diagnosed",
        expected_ecog="2",
        require_no_treatments=True,
        prohibited_confirmed_values=("decitabine started", "decitabine administered"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y04",
        title="Relapsed DLBCL with repeated treatment phases",
        target_failure_mode="Treatment chronology without semantic duplication",
        narrative=(
            "A 60-year-old woman with diffuse large B-cell lymphoma received R-CHOP. At relapse she received R-DHAP followed by autologous stem cell transplant. "
            "After a later relapse she received CAR-T therapy. Disease is relapsed and ECOG is 1."
        ),
        expected_diagnosis="diffuse large b-cell lymphoma",
        expected_disease_state="relapsed",
        expected_ecog="1",
        expected_treatments=("R-CHOP", "R-DHAP", "CAR-T"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y05",
        title="Myeloma induction transplant maintenance and salvage",
        target_failure_mode="Duplicate-prone treatment completeness repair",
        narrative=(
            "A 57-year-old man with multiple myeloma received daratumumab-RVd induction, underwent autologous stem cell transplant, and then received lenalidomide maintenance. "
            "At progression he started carfilzomib plus pomalidomide plus dexamethasone. Disease is progressive and ECOG is 1."
        ),
        expected_diagnosis="multiple myeloma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("daratumumab", "RVd", "lenalidomide", "carfilzomib", "pomalidomide", "dexamethasone"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y06",
        title="Suspected lymphoma awaiting node biopsy",
        target_failure_mode="Pathology and performance-status missingness ontology",
        narrative=(
            "A 55-year-old man has bulky retroperitoneal and mediastinal adenopathy concerning for lymphoma. Lymphoma is suspected and lymph-node biopsy is pending. "
            "ECOG has not been documented. No systemic therapy has started."
        ),
        expected_diagnosis="lymphoma",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "performance"),
        require_no_treatments=True,
        allow_null_diagnosis_if_uncertain=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y07",
        title="Follicular lymphoma with current progression",
        target_failure_mode="Progression provenance and chronology",
        narrative=(
            "A 66-year-old woman with follicular lymphoma previously received bendamustine plus rituximab followed by rituximab maintenance. "
            "Current PET/CT shows radiographic progression. ECOG is 1."
        ),
        expected_diagnosis="follicular lymphoma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("bendamustine", "rituximab"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y08",
        title="Remote metastatic breast cancer with new AML",
        target_failure_mode="Historical malignancy contamination",
        narrative=(
            "A 69-year-old woman had metastatic breast cancer treated in 2010 and has had no active breast cancer for more than a decade. "
            "She now has newly diagnosed acute myeloid leukemia confirmed by bone marrow biopsy. ECOG is 1."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="newly diagnosed",
        expected_ecog="1",
        prohibited_confirmed_values=("current metastatic breast cancer", "recurrent breast cancer"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y09",
        title="Lung adenocarcinoma with unresolved stage conflict",
        target_failure_mode="Stage conflict separation",
        narrative=(
            "A 65-year-old man has biopsy-confirmed lung adenocarcinoma. One oncology note assigns stage IIIB; PET/CT identifies a distant adrenal lesion and labels the disease stage IV. "
            "The discrepancy is unresolved. ECOG is 1."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state=None,
        expected_ecog="1",
        expected_conflict_fields=("stage",),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y10",
        title="Carcinoma of uncertain primary with pending bone biopsy",
        target_failure_mode="Diagnostic-clarification ontology plus uncertainty invariant",
        narrative=(
            "PET/CT shows multifocal osseous lesions. Metastatic carcinoma is suspected, but bone biopsy is pending and the primary site is unknown. "
            "Molecular sequencing is unavailable and ECOG is not documented. No treatment has started."
        ),
        expected_diagnosis="metastatic carcinoma",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "molecular", "performance"),
        require_no_molecular_findings=True,
        require_no_treatments=True,
        allow_null_diagnosis_if_uncertain=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y11",
        title="Metastatic colorectal cancer with hepatic disease",
        target_failure_mode="Metastatic-state canonicalization",
        narrative=(
            "A 56-year-old man has biopsy-confirmed colorectal adenocarcinoma with multiple hepatic metastases. ECOG is 0. No systemic treatment has started."
        ),
        expected_diagnosis="colorectal adenocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog="0",
        require_no_treatments=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="Y12",
        title="Resected melanoma with systemic treatment planned",
        target_failure_mode="Resected state and planned-treatment separation",
        narrative=(
            "A 51-year-old woman has resected stage III melanoma. Adjuvant nivolumab is recommended but has not begun. There is no previous systemic therapy. ECOG is 0."
        ),
        expected_diagnosis="melanoma",
        expected_disease_state="resected",
        expected_ecog="0",
        require_no_treatments=True,
        prohibited_confirmed_values=("nivolumab started", "nivolumab administered"),
        strict_core_gate=True,
    ),
)

# Frozen before first v2.5 inference. Includes uncertainty, treatment-completeness,
# progression, stage-conflict, and duplicate-prone multi-line treatment cases.
REMEDIATION_REPEAT_CASE_IDS_V25: tuple[str, ...] = ("Y01", "Y04", "Y05", "Y07", "Y09", "Y10")
REMEDIATION_REPEAT_COUNT_V25 = 3


def get_remediation_case_v25(case_id: str) -> GoldCase:
    for case in REMEDIATION_CASES_V25:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)
