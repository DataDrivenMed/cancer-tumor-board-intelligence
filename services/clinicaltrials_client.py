from __future__ import annotations

from datetime import date
import json
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from schemas.clinical_trials import TrialLocation, TrialRecord


API_BASE = "https://clinicaltrials.gov/api/v2"
CLIENT_VERSION = "1.0.0"


class ClinicalTrialsClientError(RuntimeError):
    pass


def _http_get(url: str, timeout: float = 20.0) -> bytes:
    req = Request(url, headers={"User-Agent": "CancerTumorBoardIntelligence/1.0 ClinicalTrials.gov client"})
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_study(study: dict) -> TrialRecord | None:
    protocol = study.get("protocolSection") or {}
    identification = protocol.get("identificationModule") or {}
    status = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    conditions = protocol.get("conditionsModule") or {}
    arms = protocol.get("armsInterventionsModule") or {}
    eligibility = protocol.get("eligibilityModule") or {}
    contacts = protocol.get("contactsLocationsModule") or {}

    nct_id = str(identification.get("nctId") or "").strip()
    title = str(identification.get("briefTitle") or identification.get("officialTitle") or "").strip()
    if not nct_id or not title:
        return None

    interventions = []
    for item in arms.get("interventions") or []:
        name = str(item.get("name") or "").strip()
        if name:
            interventions.append(name)

    locations = []
    for loc in contacts.get("locations") or []:
        locations.append(
            TrialLocation(
                facility=(loc.get("facility") or "").strip() or None,
                city=(loc.get("city") or "").strip() or None,
                state=(loc.get("state") or "").strip() or None,
                country=(loc.get("country") or "").strip() or None,
            )
        )

    last_update = status.get("studyFirstPostDateStruct") or {}
    if status.get("lastUpdatePostDateStruct"):
        last_update = status.get("lastUpdatePostDateStruct")

    return TrialRecord(
        nct_id=nct_id,
        title=title,
        overall_status=(status.get("overallStatus") or None),
        study_type=(design.get("studyType") or None),
        phases=list(design.get("phases") or []),
        conditions=[str(x) for x in (conditions.get("conditions") or []) if str(x).strip()],
        interventions=interventions,
        eligibility_criteria=(eligibility.get("eligibilityCriteria") or None),
        minimum_age=(eligibility.get("minimumAge") or None),
        maximum_age=(eligibility.get("maximumAge") or None),
        sex=(eligibility.get("sex") or None),
        locations=locations,
        last_update_post_date=_parse_iso_date(last_update.get("date")),
        source_url=f"https://clinicaltrials.gov/study/{nct_id}",
        source_verified=True,
    )


class ClinicalTrialsClient:
    """Small deterministic client for the official ClinicalTrials.gov API v2.

    The client performs retrieval only. It does not infer patient eligibility.
    """

    def __init__(self, *, transport: Callable[[str, float], bytes] | None = None, timeout: float = 20.0) -> None:
        self.transport = transport or _http_get
        self.timeout = timeout

    def _get_json(self, endpoint: str, params: dict[str, str | int] | None = None) -> dict:
        url = f"{API_BASE}/{endpoint}"
        if params:
            url += "?" + urlencode(params)
        try:
            payload = self.transport(url, self.timeout)
            value = json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise ClinicalTrialsClientError(f"ClinicalTrials.gov request failed: {exc}") from exc
        if not isinstance(value, dict):
            raise ClinicalTrialsClientError("ClinicalTrials.gov returned an unexpected response shape.")
        return value

    def version(self) -> str | None:
        data = self._get_json("version")
        return data.get("dataTimestamp")

    def search(self, *, condition: str, other_terms: list[str] | None = None, page_size: int = 10) -> tuple[str | None, list[TrialRecord]]:
        condition = " ".join(condition.split()).strip()
        if not condition:
            raise ValueError("condition is required")
        page_size = max(1, min(100, int(page_size)))

        term = " ".join(x.strip() for x in (other_terms or []) if x and x.strip())
        params: dict[str, str | int] = {
            "query.cond": condition,
            "pageSize": page_size,
            "format": "json",
        }
        if term:
            params["query.term"] = term

        data_timestamp = None
        try:
            data_timestamp = self.version()
        except ClinicalTrialsClientError:
            # Search may still succeed even when version metadata is temporarily unavailable.
            data_timestamp = None

        response = self._get_json("studies", params)
        records = []
        for raw in response.get("studies") or []:
            if isinstance(raw, dict):
                parsed = parse_study(raw)
                if parsed:
                    records.append(parsed)
        return data_timestamp, records
