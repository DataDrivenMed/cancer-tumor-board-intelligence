from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
import re
from urllib.request import Request, urlopen

from pydantic import HttpUrl

from schemas.evidence_gateway import (
    EvidenceIngestionPackage,
    EvidenceRecommendationRecord,
    EvidenceSourceManifest,
)
from schemas.guideline import GuidanceSourceType, GuidanceStrength
from services.evidence_gateway import normalized_sha256


ADAPTER_VERSION = "1.0.0"
NCI_AML_PDQ_URL = "https://www.cancer.gov/types/leukemia/hp/adult-aml-treatment-pdq"
NCI_AML_SOURCE_ID = "NCI-PDQ-AML-HP"


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self.parts.append(data)


def html_to_visible_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    return " ".join(" ".join(parser.parts).split())


def _parse_updated_date(text: str) -> date | None:
    matches = list(re.finditer(
        r"Updated:\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})",
        text,
        flags=re.IGNORECASE,
    ))
    if not matches:
        return None
    month_names = {
        name.lower(): idx
        for idx, name in enumerate(
            ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
            start=1,
        )
    }
    match = matches[-1]
    return date(int(match.group(3)), month_names[match.group(1).lower()], int(match.group(2)))


@dataclass(frozen=True)
class NCIPDQSnapshot:
    url: str
    fetched_utc: datetime
    source_text: str
    content_sha256: str
    updated_date: date | None


@dataclass(frozen=True)
class NCIPDQCandidateBuild:
    package: EvidenceIngestionPackage
    warnings: tuple[str, ...]
    expected_candidate_count: int


def fetch_nci_aml_pdq(*, timeout_seconds: int = 20) -> NCIPDQSnapshot:
    request = Request(
        NCI_AML_PDQ_URL,
        headers={
            "User-Agent": "CancerTumorBoardIntelligence/1.0 (+research-prototype; evidence-verification)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - URL is a fixed HTTPS NCI endpoint
        final_url = response.geturl()
        if not final_url.startswith("https://www.cancer.gov/"):
            raise RuntimeError("NCI PDQ fetch redirected outside the allowed cancer.gov origin.")
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="replace")

    text = html_to_visible_text(html)
    if "Acute Myeloid Leukemia Treatment" not in text or "PDQ" not in text:
        raise RuntimeError("Fetched page did not contain the expected NCI AML PDQ identity markers.")

    return NCIPDQSnapshot(
        url=final_url,
        fetched_utc=datetime.utcnow(),
        source_text=text,
        content_sha256=normalized_sha256(text),
        updated_date=_parse_updated_date(text),
    )


# Candidate statements are deliberately bounded, exact-source statements. They are
# not converted into formal guideline recommendations. If NCI edits the source text,
# the changed statement fails closed and requires manual review before re-admission.
_CANDIDATES = (
    {
        "recommendation_id": "NCI-PDQ-AML-DX-001",
        "disease_terms": ["acute myeloid leukemia", "aml"],
        "disease_states": [],
        "question_domains": ["diagnosis_workup"],
        "excerpt": "A peripheral blood or bone marrow blast count of 20% or greater is required to make the diagnosis, except for cases with certain chromosomal abnormalities (i.e., t(15;17), t(8;21), inv(16), or t(16;16)).",
        "locator": "Diagnostic Evaluation",
        "evidence_level": None,
    },
    {
        "recommendation_id": "NCI-PDQ-AML-PROG-001",
        "disease_terms": ["acute myeloid leukemia", "aml"],
        "disease_states": [],
        "question_domains": ["diagnosis_workup", "molecular_management"],
        "excerpt": "Cytogenetic and molecular analyses provide the strongest prognostic information available, predicting outcome of both remission induction and consolidation therapy.",
        "locator": "Prognosis and Prognostic Factors",
        "evidence_level": None,
    },
    {
        "recommendation_id": "NCI-PDQ-AML-NEW-001",
        "disease_terms": ["acute myeloid leukemia", "aml"],
        "disease_states": ["newly diagnosed", "untreated"],
        "question_domains": ["treatment_management"],
        "excerpt": "Untreated AML is defined as newly diagnosed leukemia that has not been previously treated.",
        "locator": "Treatment Option Overview for Acute Myeloid Leukemia (AML)",
        "evidence_level": None,
    },
    {
        "recommendation_id": "NCI-PDQ-AML-RR-001",
        "disease_terms": ["acute myeloid leukemia", "aml"],
        "disease_states": ["refractory", "recurrent", "relapsed"],
        "question_domains": ["treatment_management"],
        "excerpt": "No standard treatment regimen exists for patients with refractory or recurrent acute myeloid leukemia (AML).",
        "locator": "Treatment of Refractory or Recurrent AML",
        "evidence_level": None,
    },
)


def build_nci_aml_pdq_candidate(snapshot: NCIPDQSnapshot, *, accessed_date: date | None = None) -> NCIPDQCandidateBuild:
    accessed = accessed_date or snapshot.fetched_utc.date()
    warnings: list[str] = []
    recommendations: list[EvidenceRecommendationRecord] = []

    for candidate in _CANDIDATES:
        excerpt = candidate["excerpt"]
        if excerpt not in snapshot.source_text:
            warnings.append(
                f"Expected source statement {candidate['recommendation_id']} was not found exactly and was omitted. Manual source review is required."
            )
            continue
        recommendations.append(EvidenceRecommendationRecord(
            recommendation_id=candidate["recommendation_id"],
            source_id=NCI_AML_SOURCE_ID,
            disease_terms=list(candidate["disease_terms"]),
            disease_states=list(candidate["disease_states"]),
            question_domains=list(candidate["question_domains"]),
            recommendation_text=excerpt,
            source_excerpt=excerpt,
            source_locator=candidate["locator"],
            strength=GuidanceStrength.NOT_STATED,
            evidence_level=candidate["evidence_level"],
            human_verified=False,
        ))

    if snapshot.updated_date is None:
        warnings.append("The NCI page update date could not be parsed; manual metadata verification is required.")

    manifest = EvidenceSourceManifest(
        source_id=NCI_AML_SOURCE_ID,
        title="Acute Myeloid Leukemia Treatment (PDQ®)–Health Professional Version",
        organization="National Cancer Institute, PDQ Adult Treatment Editorial Board",
        source_type=GuidanceSourceType.AUTHORITATIVE_EVIDENCE_SUMMARY,
        jurisdiction="US",
        url=HttpUrl(snapshot.url),
        version=snapshot.updated_date.isoformat() if snapshot.updated_date else None,
        updated_date=snapshot.updated_date,
        accessed_date=accessed,
        license_status="public",
        expected_content_sha256=snapshot.content_sha256,
        human_verified=False,
        verification_note=(
            "NCI PDQ is ingested as an authoritative evidence summary, not a formal guideline. "
            "Human review is required before the Evidence Gateway can admit this snapshot."
        ),
    )

    return NCIPDQCandidateBuild(
        package=EvidenceIngestionPackage(
            manifest=manifest,
            source_text=snapshot.source_text,
            recommendations=recommendations,
            package_created_utc=snapshot.fetched_utc,
            package_note=(
                "Candidate package generated from the live NCI AML PDQ page. No source or statement is human-verified by the adapter."
            ),
        ),
        warnings=tuple(warnings),
        expected_candidate_count=len(_CANDIDATES),
    )


def attest_nci_aml_pdq_candidate(
    build: NCIPDQCandidateBuild,
    *,
    source_human_verified: bool,
    verified_recommendation_ids: set[str],
    verification_note: str | None = None,
) -> EvidenceIngestionPackage:
    """Apply explicit reviewer attestations without changing source text or claims."""
    package = build.package.model_copy(deep=True)
    package.manifest.human_verified = source_human_verified
    if verification_note:
        package.manifest.verification_note = verification_note
    for record in package.recommendations:
        record.human_verified = record.recommendation_id in verified_recommendation_ids
    return package
