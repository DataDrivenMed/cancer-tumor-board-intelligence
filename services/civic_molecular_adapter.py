from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from typing import Callable
from urllib.request import Request, urlopen

from schemas.molecular import (
    ClinicalActionability,
    MolecularEvidenceDirection,
    MolecularEvidenceRecord,
    MolecularEvidenceStore,
    MolecularEvidenceTier,
)


CIVIC_GRAPHQL_URL = "https://civicdb.org/api/graphql"
ADAPTER_VERSION = "1.0.0"


class CIViCClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class CIViCFetchResult:
    gene: str
    alteration: str | None
    disease: str
    records: tuple[MolecularEvidenceRecord, ...]
    warnings: tuple[str, ...] = ()


def _http_post(url: str, payload: bytes, headers: dict[str, str], timeout: float) -> bytes:
    req = Request(url, data=payload, headers=headers, method="POST")
    with urlopen(req, timeout=timeout) as response:  # nosec B310 - fixed HTTPS origin by default
        return response.read()


_QUERY = r"""
query MolecularEvidence($profile: String!, $disease: String!, $first: Int!) {
  evidenceItems(
    status: ACCEPTED,
    molecularProfileName: $profile,
    diseaseName: $disease,
    first: $first
  ) {
    totalCount
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      status
      name
      significance
      evidenceType
      evidenceLevel
      evidenceRating
      evidenceDirection
      description
      variantHgvs
      molecularProfile { id name }
      disease { id doid name displayName diseaseAliases }
      therapies { id name ncitId therapyAliases }
      source { citationId sourceType title pmcId ascoAbstractId }
    }
  }
}
"""


def _norm(value: object | None) -> str:
    return " ".join(str(value or "").replace("_", " ").split()).strip()


def _direction(evidence_type: str, significance: str, evidence_direction: str) -> MolecularEvidenceDirection:
    et = evidence_type.upper()
    sig = significance.upper()
    direction = evidence_direction.upper()

    if et == "PREDICTIVE":
        if sig in {"RESISTANCE", "REDUCED_SENSITIVITY", "ADVERSE_RESPONSE"}:
            return MolecularEvidenceDirection.SUPPORTS_RESISTANCE
        if sig == "SENSITIVITYRESPONSE" and direction != "DOES_NOT_SUPPORT":
            return MolecularEvidenceDirection.SUPPORTS_SENSITIVITY
        return MolecularEvidenceDirection.UNCLEAR
    if et == "PROGNOSTIC":
        return MolecularEvidenceDirection.PROGNOSTIC
    if et == "DIAGNOSTIC":
        return MolecularEvidenceDirection.DIAGNOSTIC
    if et in {"ONCOGENIC", "FUNCTIONAL"}:
        return MolecularEvidenceDirection.BIOLOGIC
    return MolecularEvidenceDirection.UNCLEAR


def _tier(level: str) -> MolecularEvidenceTier:
    level = level.upper()
    if level in {"A", "B", "C"}:
        return MolecularEvidenceTier.CLINICAL
    return MolecularEvidenceTier.PRECLINICAL


def _actionability(evidence_type: str, significance: str, level: str) -> ClinicalActionability:
    if evidence_type.upper() != "PREDICTIVE":
        return ClinicalActionability.NOT_ESTABLISHED

    sig = significance.upper()
    if sig not in {"SENSITIVITYRESPONSE", "RESISTANCE", "REDUCED_SENSITIVITY", "ADVERSE_RESPONSE"}:
        return ClinicalActionability.UNKNOWN

    level = level.upper()
    if level == "A":
        # CIViC Level A is strong/validated clinical evidence, but this adapter does
        # not promote a CIViC item to a regulatory or formal-guideline claim.
        return ClinicalActionability.EMERGING
    if level == "B":
        return ClinicalActionability.EMERGING
    if level == "C":
        return ClinicalActionability.INVESTIGATIONAL
    return ClinicalActionability.NOT_ESTABLISHED


def _record_from_node(
    node: dict,
    *,
    requested_gene: str,
    requested_alteration: str | None,
    accessed_date: date,
) -> MolecularEvidenceRecord:
    eid = int(node["id"])
    profile = (node.get("molecularProfile") or {}).get("name") or requested_gene
    disease = node.get("disease") or {}
    disease_names = [
        disease.get("displayName"),
        disease.get("name"),
        *(disease.get("diseaseAliases") or []),
    ]
    disease_terms = [x for x in dict.fromkeys(_norm(x) for x in disease_names) if x]

    therapies = [
        _norm(item.get("name"))
        for item in (node.get("therapies") or [])
        if _norm(item.get("name"))
    ]
    therapy = " + ".join(dict.fromkeys(therapies)) or None

    evidence_type = _norm(node.get("evidenceType"))
    evidence_level = _norm(node.get("evidenceLevel"))
    significance = _norm(node.get("significance"))
    evidence_direction = _norm(node.get("evidenceDirection"))
    description = _norm(node.get("description"))
    if not description:
        raise CIViCClientError(f"Accepted CIViC evidence item {eid} has no evidence statement.")

    alteration_terms = [x for x in dict.fromkeys([
        _norm(requested_alteration),
        _norm(profile),
        _norm(node.get("variantHgvs")),
    ]) if x]

    source = node.get("source") or {}
    citation_id = _norm(source.get("citationId"))
    source_title = _norm(source.get("title")) or f"CIViC Evidence Item {eid}"
    source_locator = f"CIViC EID {eid}"
    if citation_id:
        source_locator += f"; source citation {citation_id}"

    return MolecularEvidenceRecord(
        evidence_id=f"CIVIC-EID-{eid}",
        source_id=f"CIVIC-EID-{eid}",
        source_title=source_title,
        source_url=f"https://civicdb.org/links/evidence/{eid}",
        source_type=_tier(evidence_level),
        jurisdiction="international",
        publication_date=None,
        accessed_date=accessed_date,
        disease_terms=disease_terms,
        gene=requested_gene.strip().upper(),
        alteration_terms=alteration_terms,
        direction=_direction(evidence_type, significance, evidence_direction),
        actionability=_actionability(evidence_type, significance, evidence_level),
        therapy=therapy,
        evidence_summary=description,
        source_excerpt=description,
        source_locator=source_locator,
        source_verified=True,
        # Accepted CIViC status reflects external expert curation. The platform
        # nevertheless requires a separate local attestation before these records
        # may influence its clinical-actionability claim gate.
        human_verified=False,
        synthetic=False,
    )


class CIViCMolecularClient:
    """Read accepted CIViC evidence through the official GraphQL API.

    Anonymous reads are supported by CIViC. ``api_key`` is optional and is used only
    to avoid anonymous rate limits. The client retrieves evidence candidates; it does
    not auto-admit them to the production molecular store.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        transport: Callable[[str, bytes, dict[str, str], float], bytes] | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.transport = transport or _http_post
        self.timeout = timeout

    def fetch(
        self,
        *,
        gene: str,
        alteration: str | None,
        disease: str,
        limit: int = 25,
        accessed_date: date | None = None,
    ) -> CIViCFetchResult:
        gene = gene.strip().upper()
        alteration = _norm(alteration) or None
        disease = _norm(disease)
        if not gene or not disease:
            raise ValueError("gene and disease are required")

        profile = " ".join(x for x in (gene, alteration) if x)
        limit = max(1, min(100, int(limit)))
        request_body = json.dumps({
            "query": _QUERY,
            "variables": {"profile": profile, "disease": disease, "first": limit},
        }).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "CancerTumorBoardIntelligence/1.0 CIViC adapter",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            raw = self.transport(CIVIC_GRAPHQL_URL, request_body, headers, self.timeout)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise CIViCClientError(f"CIViC request failed: {exc}") from exc

        errors = payload.get("errors") or [] if isinstance(payload, dict) else []
        if errors:
            raise CIViCClientError(f"CIViC GraphQL returned errors: {errors}")

        connection = (((payload or {}).get("data") or {}).get("evidenceItems") or {})
        nodes = connection.get("nodes") or []
        warnings: list[str] = []
        if (connection.get("pageInfo") or {}).get("hasNextPage"):
            warnings.append(
                f"CIViC returned more than {limit} accepted matches; this bounded retrieval contains only the first page."
            )

        accessed = accessed_date or date.today()
        records = tuple(
            _record_from_node(
                node,
                requested_gene=gene,
                requested_alteration=alteration,
                accessed_date=accessed,
            )
            for node in nodes
            if isinstance(node, dict) and str(node.get("status", "")).upper() == "ACCEPTED"
        )
        return CIViCFetchResult(
            gene=gene,
            alteration=alteration,
            disease=disease,
            records=records,
            warnings=tuple(warnings),
        )


def attest_civic_records(
    records: list[MolecularEvidenceRecord] | tuple[MolecularEvidenceRecord, ...],
    *,
    verified_evidence_ids: set[str],
) -> MolecularEvidenceStore:
    """Apply explicit local human attestation without changing CIViC content."""
    out: list[MolecularEvidenceRecord] = []
    for record in records:
        copy = record.model_copy(deep=True)
        copy.human_verified = copy.evidence_id in verified_evidence_ids
        out.append(copy)
    return MolecularEvidenceStore(records=out)
