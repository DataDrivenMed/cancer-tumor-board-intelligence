from __future__ import annotations

from qualification.cases import GoldCase


TARGETED_CASES: tuple[GoldCase, ...] = (
    GoldCase(
        case_id="T01",
        title="Relapsed AML with multi-phase treatment history",
        target_failure_mode="Treatment-history omission",
        narrative=(
            "A 64-year-old man with acute myeloid leukemia received induction with cytarabine and daunorubicin in March 2024, "
            "followed by high-dose cytarabine consolidation. He relapsed in February 2026 and then received azacitidine plus venetoclax. "
            "He now has persistent disease. ECOG is 1. FLT3 testing is negative. The tumor board is reviewing salvage options."
        ),
        expected_diagnosis="acute myeloid leukemia",
        expected_disease_state="persistent",
        expected_ecog="1",
        expected_treatments=("cytarabine", "daunorubicin", "high-dose cytarabine", "azacitidine", "venetoclax"),
    ),
    GoldCase(
        case_id="T02",
        title="Current breast cancer with remote lymphoma distractor",
        target_failure_mode="Current-vs-historical diagnosis separation",
        narrative=(
            "A 57-year-old woman had diffuse large B-cell lymphoma treated with R-CHOP in 2008 and has remained in remission. "
            "She now has newly diagnosed invasive ductal carcinoma of the left breast confirmed by core biopsy. ECOG is 0. "
            "The tumor board question concerns management of the new breast cancer."
        ),
        expected_diagnosis="invasive ductal carcinoma",
        expected_disease_state="newly diagnosed",
        expected_ecog="0",
        prohibited_confirmed_values=("diffuse large B-cell lymphoma as current diagnosis", "recurrent lymphoma"),
    ),
    GoldCase(
        case_id="T03",
        title="Metastatic lung cancer with remote melanoma distractor",
        target_failure_mode="Historical distractor contamination",
        narrative=(
            "A 68-year-old man had a stage I cutaneous melanoma excised in 2014 with no recurrence. He now has metastatic lung adenocarcinoma "
            "confirmed by lung biopsy, with liver metastases on imaging. EGFR exon 19 deletion is detected. ECOG is 1. "
            "The board is reviewing first-line systemic therapy for metastatic lung adenocarcinoma."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog="1",
        expected_molecular_genes=("EGFR",),
        prohibited_confirmed_values=("melanoma as current diagnosis", "recurrent melanoma"),
    ),
    GoldCase(
        case_id="T04",
        title="DLBCL with salvage and cellular therapy chronology",
        target_failure_mode="Longitudinal treatment omission and ordering",
        narrative=(
            "A 55-year-old woman with diffuse large B-cell lymphoma received R-CHOP in 2023 and achieved remission. She relapsed in 2025, "
            "received R-ICE salvage therapy, then underwent CAR-T cell therapy in January 2026. She now has progressive disease. ECOG is 2."
        ),
        expected_diagnosis="diffuse large b-cell lymphoma",
        expected_disease_state="progressive",
        expected_ecog="2",
        expected_treatments=("R-CHOP", "R-ICE"),
    ),
    GoldCase(
        case_id="T05",
        title="Planned immunotherapy not yet administered",
        target_failure_mode="Planned-vs-administered treatment separation",
        narrative=(
            "A 62-year-old woman has resected stage III melanoma. Adjuvant pembrolizumab has been recommended but has not yet started. "
            "There is no prior systemic therapy. ECOG is 0. The board is reviewing the postoperative plan."
        ),
        expected_diagnosis="melanoma",
        expected_disease_state=None,
        expected_ecog="0",
        require_no_treatments=True,
        prohibited_confirmed_values=("pembrolizumab administered", "pembrolizumab started"),
    ),
    GoldCase(
        case_id="T06",
        title="Historical maintenance therapy is not current medication",
        target_failure_mode="Medication temporality",
        narrative=(
            "A 60-year-old woman with multiple myeloma received VRd induction, autologous stem cell transplant, and lenalidomide maintenance. "
            "Lenalidomide was stopped in 2025 because of progression. She is now receiving daratumumab plus pomalidomide and dexamethasone. "
            "She currently has progressive disease. ECOG is 1. The board is reviewing response assessment."
        ),
        expected_diagnosis="multiple myeloma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("VRd", "lenalidomide", "daratumumab", "pomalidomide", "dexamethasone"),
    ),
    GoldCase(
        case_id="T07",
        title="New colon cancer with remote prostate cancer history",
        target_failure_mode="Current malignancy selection",
        narrative=(
            "A 73-year-old man had localized prostate cancer treated with radiation in 2010 and has no evidence of active prostate cancer. "
            "He now has newly diagnosed sigmoid colon adenocarcinoma confirmed on biopsy. ECOG is 1. The board is reviewing initial management."
        ),
        expected_diagnosis="sigmoid colon adenocarcinoma",
        expected_disease_state="newly diagnosed",
        expected_ecog="1",
        prohibited_confirmed_values=("prostate cancer as current diagnosis", "recurrent prostate cancer"),
    ),
    GoldCase(
        case_id="T08",
        title="Myeloma with repeated regimen components",
        target_failure_mode="Repeated-agent chronology",
        narrative=(
            "A 63-year-old man with multiple myeloma received VRd induction in 2021, then lenalidomide maintenance. At first relapse in 2024, "
            "he received daratumumab, bortezomib and dexamethasone. At progression in 2026 he started carfilzomib, pomalidomide and dexamethasone. "
            "ECOG is 1 and disease is progressive."
        ),
        expected_diagnosis="multiple myeloma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("VRd", "lenalidomide", "daratumumab", "bortezomib", "dexamethasone", "carfilzomib", "pomalidomide"),
    ),
    GoldCase(
        case_id="T09",
        title="Lung cancer staging discrepancy",
        target_failure_mode="Stage-conflict preservation",
        narrative=(
            "A 70-year-old woman has biopsy-proven lung adenocarcinoma. The clinic note lists clinical stage IIIB. A subsequent PET/CT report "
            "documents an adrenal metastasis and labels the disease stage IV. The discrepancy has not been adjudicated. ECOG is 1."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state=None,
        expected_ecog="1",
        expected_conflict_fields=("stage",),
    ),
    GoldCase(
        case_id="T10",
        title="Pending EGFR result must not become positive",
        target_failure_mode="Pending molecular result non-inference",
        narrative=(
            "A 59-year-old man has newly diagnosed metastatic lung adenocarcinoma. EGFR testing has been sent and remains pending; no EGFR result "
            "is available. ALK testing is also pending. ECOG is 1. The board is reviewing treatment planning while molecular results are pending."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog="1",
        expected_missing_fields=("EGFR", "ALK"),
        prohibited_confirmed_values=("EGFR positive", "EGFR mutated", "ALK positive", "ALK rearranged"),
    ),
)


UNSEEN_CASES: tuple[GoldCase, ...] = (
    GoldCase(
        case_id="U01",
        title="Metastatic colorectal cancer",
        target_failure_mode="Unseen solid-tumor extraction",
        narrative=(
            "A 66-year-old woman has metastatic colorectal adenocarcinoma with liver metastases. KRAS G12D is detected. ECOG is 1. "
            "She received FOLFOX followed by FOLFIRI after progression. The board is reviewing later-line therapy."
        ),
        expected_diagnosis="colorectal adenocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog="1",
        expected_molecular_genes=("KRAS",),
        expected_treatments=("FOLFOX", "FOLFIRI"),
    ),
    GoldCase(
        case_id="U02",
        title="HER2-positive breast cancer",
        target_failure_mode="Unseen biomarker-rich breast cancer",
        narrative=(
            "A 52-year-old woman has metastatic breast adenocarcinoma. HER2 amplification is confirmed and ER is positive. ECOG is 0. "
            "She previously received docetaxel, trastuzumab and pertuzumab and now has progressive disease."
        ),
        expected_diagnosis="breast adenocarcinoma",
        expected_disease_state="progressive",
        expected_ecog="0",
        expected_treatments=("docetaxel", "trastuzumab", "pertuzumab"),
    ),
    GoldCase(
        case_id="U03",
        title="BRAF-mutated metastatic melanoma",
        target_failure_mode="Unseen melanoma molecular extraction",
        narrative=(
            "A 46-year-old man has metastatic cutaneous melanoma with BRAF V600E mutation. ECOG is 1. He previously received nivolumab and later "
            "dabrafenib plus trametinib. Imaging now shows progressive disease."
        ),
        expected_diagnosis="cutaneous melanoma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_molecular_genes=("BRAF",),
        expected_treatments=("nivolumab", "dabrafenib", "trametinib"),
    ),
    GoldCase(
        case_id="U04",
        title="ALK-rearranged lung adenocarcinoma",
        target_failure_mode="Unseen targeted-therapy chronology",
        narrative=(
            "A 41-year-old woman has metastatic lung adenocarcinoma with an ALK rearrangement. ECOG is 0. She received alectinib, then lorlatinib "
            "after CNS progression. The board is reviewing next steps after further progression."
        ),
        expected_diagnosis="lung adenocarcinoma",
        expected_disease_state="progressive",
        expected_ecog="0",
        expected_molecular_genes=("ALK",),
        expected_treatments=("alectinib", "lorlatinib"),
    ),
    GoldCase(
        case_id="U05",
        title="Ovarian carcinoma with BRCA1 finding",
        target_failure_mode="Unseen ovarian cancer extraction",
        narrative=(
            "A 58-year-old woman has recurrent high-grade serous ovarian carcinoma. Germline testing documents a BRCA1 pathogenic variant. ECOG is 1. "
            "She previously received carboplatin plus paclitaxel and later olaparib maintenance."
        ),
        expected_diagnosis="high-grade serous ovarian carcinoma",
        expected_disease_state="recurrent",
        expected_ecog="1",
        expected_molecular_genes=("BRCA1",),
        expected_treatments=("carboplatin", "paclitaxel", "olaparib"),
    ),
    GoldCase(
        case_id="U06",
        title="Pancreatic adenocarcinoma with missing ECOG",
        target_failure_mode="Unseen sparse-case missingness",
        narrative=(
            "A 69-year-old man has biopsy-confirmed pancreatic ductal adenocarcinoma with liver metastases. The note does not report ECOG performance status. "
            "He has not started systemic therapy. The board is reviewing initial management."
        ),
        expected_diagnosis="pancreatic ductal adenocarcinoma",
        expected_disease_state="metastatic",
        expected_ecog=None,
        expected_missing_fields=("performance",),
    ),
    GoldCase(
        case_id="U07",
        title="Metastatic renal cell carcinoma",
        target_failure_mode="Unseen kidney cancer chronology",
        narrative=(
            "A 61-year-old man has metastatic clear cell renal cell carcinoma. ECOG is 1. He received pembrolizumab plus axitinib and later cabozantinib "
            "after progression. The current disease state is progressive."
        ),
        expected_diagnosis="clear cell renal cell carcinoma",
        expected_disease_state="progressive",
        expected_ecog="1",
        expected_treatments=("pembrolizumab", "axitinib", "cabozantinib"),
    ),
    GoldCase(
        case_id="U08",
        title="Metastatic castration-resistant prostate cancer",
        target_failure_mode="Unseen prostate cancer chronology",
        narrative=(
            "A 72-year-old man has metastatic castration-resistant prostate adenocarcinoma. ECOG is 2. He previously received abiraterone and later docetaxel. "
            "He now has radiographic progression."
        ),
        expected_diagnosis="prostate adenocarcinoma",
        expected_disease_state="progressive",
        expected_ecog="2",
        expected_treatments=("abiraterone", "docetaxel"),
    ),
    GoldCase(
        case_id="U09",
        title="IDH1-mutated glioma",
        target_failure_mode="Unseen CNS tumor molecular extraction",
        narrative=(
            "A 39-year-old woman has recurrent astrocytoma with an IDH1 R132H mutation documented on tumor sequencing. ECOG is 1. "
            "She previously received radiation and temozolomide. The board is reviewing management of recurrent disease."
        ),
        expected_diagnosis="astrocytoma",
        expected_disease_state="recurrent",
        expected_ecog="1",
        expected_molecular_genes=("IDH1",),
        expected_treatments=("radiation", "temozolomide"),
    ),
    GoldCase(
        case_id="U10",
        title="Sparse carcinoma of unknown primary",
        target_failure_mode="Abstention with incomplete diagnostic workup",
        narrative=(
            "Referral note: metastatic carcinoma is suspected after imaging showed multiple liver lesions, but no biopsy result has returned. "
            "The primary site is unknown. Molecular testing and ECOG performance status are not available. No systemic treatment has started."
        ),
        expected_diagnosis="suspected metastatic carcinoma",
        expected_disease_state=None,
        expected_ecog=None,
        expected_missing_fields=("pathology", "molecular", "performance"),
        require_no_molecular_findings=True,
        require_no_treatments=True,
        allow_null_diagnosis_if_uncertain=True,
        prohibited_confirmed_values=("lung cancer", "colon cancer", "pancreatic cancer", "breast cancer"),
        notes="Do not infer a primary site before pathology is available.",
    ),
)


ALL_CHALLENGE_CASES: tuple[GoldCase, ...] = TARGETED_CASES + UNSEEN_CASES
REPEATED_STOCHASTIC_CASE_IDS: tuple[str, ...] = ("T01", "T03", "T05", "T08", "U06", "U10")
REPEATED_STOCHASTIC_REPEATS = 3


def get_challenge_case(case_id: str) -> GoldCase:
    for case in ALL_CHALLENGE_CASES:
        if case.case_id == case_id:
            return case
    raise KeyError(case_id)
