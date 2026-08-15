from __future__ import annotations

from qualification.cases import GoldCase


REMEDIATION_CASES_V23: tuple[GoldCase, ...] = (
    GoldCase(
        case_id="W01",
        title="Suspected metastatic carcinoma with pending liver biopsy",
        target_failure_mode="Uncertain diagnosis exact provenance plus pathology missingness",
        narrative=(
            "CT shows multiple liver lesions and metastatic carcinoma is suspected. A liver biopsy is pending and the primary site is unknown. "
            "Molecular testing has not been performed and ECOG is not documented. No anticancer therapy has started."
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
        case_id="W02",
        title="Suspected lymphoma awaiting excisional biopsy",
        target_failure_mode="Cross-field pathology gap reconciliation",
        narrative=(
            "A 58-year-old man has bulky cervical and mediastinal adenopathy concerning for lymphoma. Lymphoma is suspected, but excisional biopsy is pending. "
            "ECOG is not documented and no systemic therapy has started."
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
        case_id="W03",
        title="New AML with pending cytogenetics",
        target_failure_mode="Confirmed diagnosis with molecular missingness",
        narrative=(
            "A 64-year-old woman has bone-marrow-confirmed acute myeloid leukemia. ECOG is 1. FLT3, NPM1 and cytogenetic testing are pending. "
            "Induction therapy has not yet started."
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
        case_id="W04",
        title="Relapsed DLBCL with multi-line treatment chronology",
        target_failure_mode="Longitudinal treatment completeness",
        narrative=(
            "A 61-year-old woman with diffuse large B-cell lymphoma received R-CHOP, then at first relapse received R-ICE followed by autologous stem cell transplant. "
            "At a later relapse she received CAR-T therapy. Disease is relapsed and ECOG is 1."
        ),
        expected_diagnosis="diffuse large b-cell lymphoma",
        expected_disease_state="relapsed",
        expected_ecog="1",
        expected_treatments=("R-CHOP", "R-ICE", "CAR-T"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="W05",
        title="Myeloma with induction transplant maintenance and salvage",
        target_failure_mode="Intermediate treatment episode completeness",
        narrative=(
            "A 59-year-old man with multiple myeloma received daratumumab-RVd induction, underwent autologous stem cell transplant, and then received lenalidomide maintenance. "
            "At progression he started carfilzomib plus pomalidomide plus dexamethasone. Disease is progressive and ECOG is 1."
        ),
        expected_diagnosis="multiple myeloma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("daratumumab", "RVd", "lenalidomide", "carfilzomib", "pomalidomide", "dexamethasone"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="W06",
        title="MDS with planned azacitidine not yet started",
        target_failure_mode="Planned therapy must not enter administered history",
        narrative=(
            "A 72-year-old woman has biopsy-confirmed myelodysplastic syndrome. Azacitidine is planned for next week but has not started. "
            "There is no prior disease-directed therapy and ECOG is 2."
        ),
        expected_diagnosis="myelodysplastic syndrome",
        expected_disease_state="newly diagnosed",
        expected_ecog="2",
        require_no_treatments=True,
        prohibited_confirmed_values=("azacitidine started", "azacitidine administered"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="W07",
        title="Follicular lymphoma with radiographic progression",
        target_failure_mode="Progression canonicalization with exact provenance",
        narrative=(
            "A 67-year-old woman has follicular lymphoma previously treated with bendamustine plus rituximab. Current PET/CT demonstrates radiographic progression. "
            "ECOG is 1."
        ),
        expected_diagnosis="follicular lymphoma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("bendamustine", "rituximab"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="W08",
        title="Remote metastatic breast cancer with new AML",
        target_failure_mode="Historical malignancy contamination guard",
        narrative=(
            "A 70-year-old woman had metastatic breast cancer treated in 2011 and has had no active breast cancer for many years. She now has bone-marrow-confirmed acute myeloid leukemia. "
            "ECOG is 1 and the AML is newly diagnosed."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="newly diagnosed",
        expected_ecog="1",
        prohibited_confirmed_values=("current metastatic breast cancer", "recurrent breast cancer"),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="W09",
        title="Lung cancer with unresolved stage III versus IV discrepancy",
        target_failure_mode="Stage conflict separation",
        narrative=(
            "A 63-year-old man has biopsy-confirmed lung adenocarcinoma. The oncology note records stage IIIB, while PET/CT describes a distant adrenal lesion and labels stage IV. "
            "The discrepancy has not been resolved. ECOG is 1."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state=None,
        expected_ecog="1",
        expected_conflict_fields=("stage",),
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="W10",
        title="Suspected metastatic carcinoma with pending bone biopsy",
        target_failure_mode="Repeated uncertain-diagnosis provenance stress test",
        narrative=(
            "PET/CT demonstrates multifocal osseous lesions and metastatic carcinoma is suspected. Bone biopsy is pending, the primary site remains unknown, and molecular profiling is unavailable. "
            "ECOG is not documented. No systemic treatment has started."
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
        case_id="W11",
        title="Metastatic colorectal cancer with liver metastases",
        target_failure_mode="Metastatic-state canonicalization",
        narrative=(
            "A 55-year-old man has biopsy-confirmed colorectal adenocarcinoma with multiple liver metastases. ECOG is 0. No systemic therapy has started."
        ),
        expected_diagnosis="colorectal adenocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog="0",
        require_no_treatments=True,
        strict_core_gate=True,
    ),
    GoldCase(
        case_id="W12",
        title="Resected melanoma with adjuvant therapy planned",
        target_failure_mode="Resected state and planned therapy separation",
        narrative=(
            "A 49-year-old woman has resected stage III melanoma. Adjuvant pembrolizumab is recommended but has not started. There is no prior systemic therapy. ECOG is 0."
        ),
        expected_diagnosis="melanoma",
        expected_disease_state="resected",
        expected_ecog="0",
        require_no_treatments=True,
        prohibited_confirmed_values=("pembrolizumab started", "pembrolizumab administered"),
        strict_core_gate=True,
    ),
)

# Frozen before first inference. W01/W10 directly stress the two v2.2 S03 failure modes;
# W04/W05 stress treatment completeness; W07 provenance/canonicalization; W09 conflict safety.
REMEDIATION_REPEAT_CASE_IDS_V23: tuple[str, ...] = ("W01", "W04", "W05", "W07", "W09", "W10")
REMEDIATION_REPEAT_COUNT_V23 = 3


def get_remediation_case_v23(case_id: str) -> GoldCase:
    for case in REMEDIATION_CASES_V23:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)
