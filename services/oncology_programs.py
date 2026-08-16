from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OncologyProgram:
    program_id: str
    board_type: str
    display_name: str
    diagnosis_terms: tuple[str, ...]


# Pan-oncology disease-family registry. The registry groups individual diagnoses into
# operational tumor-board programs while preserving the diagnosis itself in the case.
# It is intentionally broader than any one evidence package. A registered program is
# architecturally supported; disease-specific recommendation evidence must still be
# present, verified, current, and admitted before a recommendation can be supported.
PROGRAMS: tuple[OncologyProgram, ...] = (
    OncologyProgram(
        "hematologic_malignancy", "hematologic_malignancy_board", "Hematologic malignancies",
        (
            "acute myeloid leukemia", "aml", "acute lymphoblastic leukemia", "all",
            "chronic myeloid leukemia", "cml", "chronic lymphocytic leukemia", "cll",
            "myelodysplastic", "myeloproliferative", "multiple myeloma", "plasma cell",
            "hodgkin lymphoma", "non-hodgkin lymphoma", "lymphoma", "leukemia",
            "hairy cell leukemia", "langerhans cell histiocytosis",
        ),
    ),
    OncologyProgram(
        "breast_oncology", "breast_tumor_board", "Breast oncology",
        ("breast cancer", "breast carcinoma", "ductal carcinoma", "lobular carcinoma", "dcis"),
    ),
    OncologyProgram(
        "thoracic_oncology", "thoracic_tumor_board", "Thoracic oncology",
        (
            "lung cancer", "non-small cell lung", "nsclc", "small cell lung", "sclc",
            "mesothelioma", "thymoma", "thymic carcinoma", "tracheobronchial",
        ),
    ),
    OncologyProgram(
        "gastrointestinal_oncology", "gastrointestinal_tumor_board", "Gastrointestinal oncology",
        (
            "colorectal", "colon cancer", "rectal cancer", "anal cancer", "esophageal",
            "gastric cancer", "stomach cancer", "pancreatic cancer", "pancreatic adenocarcinoma",
            "cholangiocarcinoma", "bile duct", "gallbladder", "hepatocellular", "liver cancer",
            "small intestine", "appendix cancer", "gastrointestinal stromal", "gist",
            "gastrointestinal neuroendocrine", "pancreatic neuroendocrine",
        ),
    ),
    OncologyProgram(
        "genitourinary_oncology", "genitourinary_tumor_board", "Genitourinary oncology",
        (
            "prostate cancer", "renal cell", "kidney cancer", "bladder cancer", "urothelial",
            "testicular cancer", "germ cell tumor", "penile cancer", "urethral cancer",
            "renal pelvis", "ureter cancer",
        ),
    ),
    OncologyProgram(
        "gynecologic_oncology", "gynecologic_tumor_board", "Gynecologic oncology",
        (
            "ovarian cancer", "fallopian tube", "primary peritoneal", "endometrial",
            "uterine cancer", "uterine sarcoma", "cervical cancer", "vaginal cancer",
            "vulvar cancer", "gestational trophoblastic",
        ),
    ),
    OncologyProgram(
        "head_neck_oncology", "head_neck_tumor_board", "Head and neck oncology",
        (
            "head and neck", "oral cavity", "oropharyngeal", "nasopharyngeal", "hypopharyngeal",
            "laryngeal", "salivary gland", "nasal cavity", "paranasal sinus", "esthesioneuroblastoma",
            "squamous neck cancer",
        ),
    ),
    OncologyProgram(
        "neuro_oncology", "neuro_oncology_tumor_board", "Neuro-oncology",
        (
            "glioblastoma", "glioma", "astrocytoma", "oligodendroglioma", "ependymoma",
            "medulloblastoma", "brain tumor", "brain cancer", "central nervous system tumor",
            "cns tumor", "primary cns lymphoma", "meningioma",
        ),
    ),
    OncologyProgram(
        "cutaneous_oncology", "cutaneous_tumor_board", "Melanoma and cutaneous oncology",
        (
            "melanoma", "merkel cell carcinoma", "cutaneous squamous", "skin cancer",
            "basal cell carcinoma", "cutaneous t-cell lymphoma", "mycosis fungoides", "sezary",
        ),
    ),
    OncologyProgram(
        "sarcoma_oncology", "sarcoma_tumor_board", "Sarcoma and bone oncology",
        (
            "soft tissue sarcoma", "sarcoma", "osteosarcoma", "ewing sarcoma", "chondrosarcoma",
            "gastrointestinal stromal tumor", "gist", "rhabdomyosarcoma", "kaposi sarcoma",
            "bone cancer", "chordoma",
        ),
    ),
    OncologyProgram(
        "endocrine_neuroendocrine_oncology", "endocrine_neuroendocrine_tumor_board", "Endocrine and neuroendocrine oncology",
        (
            "thyroid cancer", "parathyroid cancer", "adrenocortical", "pheochromocytoma",
            "paraganglioma", "pituitary tumor", "neuroendocrine tumor", "neuroendocrine carcinoma",
        ),
    ),
    OncologyProgram(
        "ophthalmic_oncology", "ophthalmic_tumor_board", "Ophthalmic oncology",
        ("intraocular melanoma", "uveal melanoma", "retinoblastoma", "eye cancer"),
    ),
    OncologyProgram(
        "pediatric_oncology", "pediatric_oncology_tumor_board", "Pediatric oncology",
        (
            "neuroblastoma", "wilms tumor", "pleuropulmonary blastoma", "retinoblastoma",
            "pediatric cancer", "childhood cancer", "childhood leukemia", "childhood lymphoma",
            "rhabdomyosarcoma", "medulloblastoma", "atypical teratoid", "dipg",
        ),
    ),
    OncologyProgram(
        "rare_unknown_primary_oncology", "rare_unknown_primary_tumor_board", "Rare cancers and unknown primary",
        (
            "carcinoma of unknown primary", "unknown primary", "cup", "nut carcinoma",
            "adrenocortical carcinoma", "extragonadal germ cell", "rare cancer",
        ),
    ),
)

PROGRAM_BY_ID = {program.program_id: program for program in PROGRAMS}


def _norm(value: object | None) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def registered_program_ids() -> tuple[str, ...]:
    return tuple(program.program_id for program in PROGRAMS)


def is_registered_oncology_program(program_id: str | None) -> bool:
    return str(program_id or "") in PROGRAM_BY_ID


def classify_diagnosis(diagnosis: object | None) -> OncologyProgram:
    text = _norm(diagnosis)
    if not text:
        return PROGRAM_BY_ID["rare_unknown_primary_oncology"]

    # Prefer the longest matching disease phrase so specific diagnoses win over broad
    # substrings such as "sarcoma" or "lymphoma".
    matches: list[tuple[int, OncologyProgram]] = []
    for program in PROGRAMS:
        for term in program.diagnosis_terms:
            normalized_term = _norm(term)
            if normalized_term and normalized_term in text:
                matches.append((len(normalized_term), program))
    if matches:
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]
    return PROGRAM_BY_ID["rare_unknown_primary_oncology"]


def assign_case_program(case):
    """Return a copy of a canonical case with deterministic pan-oncology metadata."""
    classified = classify_diagnosis(getattr(getattr(case, "diagnosis", None), "value", None))
    updated = case.model_copy(deep=True)
    updated.disease_program = classified.program_id
    updated.tumor_board_type = classified.board_type
    return updated
