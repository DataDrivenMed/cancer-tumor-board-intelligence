from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import re
from typing import Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from schemas.safety import SafetyEvidenceRecord, SafetyEvidenceStore, SafetyEvidenceType, SafetySeverity


OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
ADAPTER_VERSION = "1.1.0"


class FDALabelClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class FDALabelSectionCandidate:
    therapy: str
    spl_set_id: str | None
    spl_id: str | None
    application_number: str | None
    effective_time: str | None
    section: str
    text: str
    source_url: str
    accessed_date: date
    synthetic: bool = False


@dataclass(frozen=True)
class SafetyRecordAttestation:
    candidate_index: int
    evidence_id: str
    evidence_type: SafetyEvidenceType
    severity: SafetySeverity
    safety_issue: str
    exact_excerpt: str
    therapy_terms: tuple[str, ...]
    disease_terms: tuple[str, ...] = ()
    trigger_terms: tuple[str, ...] = ()
    required_parameters: tuple[str, ...] = ()
    contraindication: bool = False


def _http_get(url: str, timeout: float) -> bytes:
    req = Request(url, headers={"User-Agent": "CancerTumorBoardIntelligence/1.0 FDA label adapter"})
    try:
        with urlopen(req, timeout=timeout) as response:  # nosec B310 - generated from fixed HTTPS FDA origin
            final = response.geturl()
            if not final.startswith("https://api.fda.gov/"):
                raise FDALabelClientError("openFDA request redirected outside api.fda.gov")
            return response.read()
    except HTTPError as exc:
        if exc.code == 404:
            return b'{"results": []}'
        raise


def _clean(value: object | None) -> str:
    return " ".join(str(value or "").split()).strip()


def _first(value: object | None) -> str | None:
    if isinstance(value, list):
        for item in value:
            text = _clean(item)
            if text:
                return text
        return None
    text = _clean(value)
    return text or None


def _quote_search(value: str) -> str:
    # openFDA search strings use Lucene syntax. Keep only conservative drug-name characters.
    safe = re.sub(r"[^A-Za-z0-9 .+_-]", " ", value)
    safe = " ".join(safe.split())
    if not safe:
        raise ValueError("therapy name is empty after normalization")
    return safe.replace('"', "")


_SECTION_FIELDS = (
    "boxed_warning",
    "contraindications",
    "warnings",
    "warnings_and_cautions",
    "drug_interactions",
    "adverse_reactions",
    "dosage_and_administration",
    "use_in_specific_populations",
)


class FDALabelClient:
    """Retrieve bounded Structured Product Labeling sections from openFDA.

    Retrieval produces source candidates only. It does not infer patient-specific
    safety findings and does not auto-admit records into the Safety Agent store.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        transport: Callable[[str, float], bytes] | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.transport = transport or _http_get
        self.timeout = timeout

    def fetch_sections(
        self,
        *,
        therapy: str,
        limit: int = 5,
        accessed_date: date | None = None,
    ) -> list[FDALabelSectionCandidate]:
        therapy = _quote_search(therapy)
        limit = max(1, min(20, int(limit)))
        search = (
            f'openfda.generic_name:"{therapy}" OR '
            f'openfda.brand_name:"{therapy}" OR '
            f'openfda.substance_name:"{therapy}"'
        )

        public_params: dict[str, str | int] = {"search": search, "limit": limit}
        source_url = f"{OPENFDA_LABEL_URL}?{urlencode(public_params)}"

        request_params = dict(public_params)
        if self.api_key:
            request_params["api_key"] = self.api_key
        request_url = f"{OPENFDA_LABEL_URL}?{urlencode(request_params)}"

        try:
            payload = json.loads(self.transport(request_url, self.timeout).decode("utf-8"))
        except Exception as exc:
            raise FDALabelClientError(f"openFDA label request failed: {exc}") from exc

        results = payload.get("results") or [] if isinstance(payload, dict) else []
        accessed = accessed_date or date.today()
        candidates: list[FDALabelSectionCandidate] = []
        seen: set[tuple[str | None, str, str]] = set()

        # Prefer the most recent represented effective time, while retaining bounded
        # multiple labels because generic/brand searches can match more than one SPL.
        results = sorted(
            [r for r in results if isinstance(r, dict)],
            key=lambda r: _clean(r.get("effective_time")),
            reverse=True,
        )

        for record in results:
            openfda = record.get("openfda") or {}
            spl_set_id = _first(record.get("set_id")) or _first(openfda.get("spl_set_id"))
            spl_id = _first(record.get("id")) or _first(openfda.get("spl_id"))
            application = _first(openfda.get("application_number"))
            effective_time = _first(record.get("effective_time"))

            for section in _SECTION_FIELDS:
                raw = record.get(section)
                values = raw if isinstance(raw, list) else [raw] if raw else []
                for item in values:
                    text = _clean(item)
                    if not text:
                        continue
                    key = (spl_set_id, section, text)
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append(
                        FDALabelSectionCandidate(
                            therapy=therapy,
                            spl_set_id=spl_set_id,
                            spl_id=spl_id,
                            application_number=application,
                            effective_time=effective_time,
                            section=section,
                            text=text,
                            source_url=source_url,
                            accessed_date=accessed,
                        )
                    )
        return candidates


def build_attested_safety_store(
    candidates: list[FDALabelSectionCandidate],
    attestations: list[SafetyRecordAttestation],
) -> SafetyEvidenceStore:
    """Convert reviewed FDA label passages into locally attested safety records.

    Exact excerpt membership is enforced. This prevents a reviewer or downstream
    model from attributing text to an FDA label section when the source span is not
    literally present in the retrieved candidate.
    """
    records: list[SafetyEvidenceRecord] = []
    used_ids: set[str] = set()

    for attestation in attestations:
        if attestation.evidence_id in used_ids:
            raise ValueError(f"Duplicate safety evidence_id: {attestation.evidence_id}")
        if attestation.candidate_index < 0 or attestation.candidate_index >= len(candidates):
            raise ValueError(f"Invalid FDA candidate index: {attestation.candidate_index}")

        candidate = candidates[attestation.candidate_index]
        excerpt = _clean(attestation.exact_excerpt)
        if not excerpt or excerpt not in candidate.text:
            raise ValueError(
                f"Attested excerpt for {attestation.evidence_id} is not an exact span of the selected FDA label section"
            )

        source_id = candidate.spl_set_id or candidate.spl_id or f"openfda:{candidate.therapy}"
        records.append(
            SafetyEvidenceRecord(
                evidence_id=attestation.evidence_id,
                source_id=source_id,
                source_title=f"FDA Structured Product Labeling: {candidate.therapy}",
                source_locator=(
                    f"{candidate.section}; SPL set {candidate.spl_set_id or 'not represented'}; "
                    f"effective_time {candidate.effective_time or 'not represented'}"
                ),
                source_excerpt=excerpt,
                source_verified=True,
                human_verified=True,
                synthetic=candidate.synthetic,
                therapy_terms=list(attestation.therapy_terms),
                disease_terms=list(attestation.disease_terms),
                trigger_terms=list(attestation.trigger_terms),
                evidence_type=attestation.evidence_type,
                severity=attestation.severity,
                safety_issue=attestation.safety_issue.strip(),
                required_parameters=list(attestation.required_parameters),
                contraindication=attestation.contraindication,
            )
        )
        used_ids.add(attestation.evidence_id)

    return SafetyEvidenceStore(records=records)
