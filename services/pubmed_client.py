from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from schemas.literature import LiteratureArticle


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
PUBMED_BASE = "https://pubmed.ncbi.nlm.nih.gov"
CLIENT_VERSION = "1.0.0"


class PubMedClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class PubMedSearchResult:
    query: str
    pmids: tuple[str, ...]


def _http_get(url: str, timeout: float = 15.0) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "CancerTumorBoardIntelligence/1.0 (PubMed E-utilities client)"
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def _parse_date(article: ET.Element) -> tuple[date | None, str | None]:
    pub_date = article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate")
    if pub_date is None:
        return None, None

    year = _text(pub_date.find("Year"))
    month = _text(pub_date.find("Month"))
    day = _text(pub_date.find("Day"))
    medline_date = _text(pub_date.find("MedlineDate"))
    raw = " ".join(x for x in (year, month, day) if x).strip() or medline_date or None

    if not year and medline_date:
        import re

        match = re.search(r"\b(19|20)\d{2}\b", medline_date)
        year = match.group(0) if match else ""

    if not year:
        return None, raw

    month_map = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    month_num = 1
    if month:
        if month.isdigit():
            month_num = max(1, min(12, int(month)))
        else:
            month_num = month_map.get(month.lower(), 1)
    day_num = int(day) if day.isdigit() else 1
    try:
        return date(int(year), month_num, day_num), raw
    except ValueError:
        return date(int(year), 1, 1), raw


def _extract_identifiers(article: ET.Element) -> tuple[str | None, str | None]:
    doi = None
    pmcid = None
    for ident in article.findall("./PubmedData/ArticleIdList/ArticleId"):
        ident_type = ident.attrib.get("IdType", "").lower()
        value = _text(ident)
        if ident_type == "doi" and value:
            doi = value
        elif ident_type == "pmc" and value:
            pmcid = value
    return doi, pmcid


def parse_pubmed_xml(payload: bytes, *, max_abstract_excerpt_chars: int = 700) -> list[LiteratureArticle]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise PubMedClientError(f"PubMed XML parse failed: {exc}") from exc

    articles: list[LiteratureArticle] = []
    for pubmed_article in root.findall(".//PubmedArticle"):
        pmid = _text(pubmed_article.find("./MedlineCitation/PMID"))
        title = _text(pubmed_article.find("./MedlineCitation/Article/ArticleTitle"))
        if not pmid or not title:
            continue

        journal = _text(pubmed_article.find("./MedlineCitation/Article/Journal/Title")) or None
        publication_date, publication_date_text = _parse_date(pubmed_article)

        authors: list[str] = []
        for author in pubmed_article.findall("./MedlineCitation/Article/AuthorList/Author"):
            collective = _text(author.find("CollectiveName"))
            if collective:
                authors.append(collective)
                continue
            last = _text(author.find("LastName"))
            initials = _text(author.find("Initials"))
            name = " ".join(x for x in (last, initials) if x).strip()
            if name:
                authors.append(name)

        publication_types = [
            _text(node)
            for node in pubmed_article.findall("./MedlineCitation/Article/PublicationTypeList/PublicationType")
            if _text(node)
        ]

        abstract_parts = [
            _text(node)
            for node in pubmed_article.findall("./MedlineCitation/Article/Abstract/AbstractText")
            if _text(node)
        ]
        abstract = "\n".join(abstract_parts).strip()
        abstract_hash = sha256(abstract.encode("utf-8")).hexdigest() if abstract else None
        abstract_excerpt = None
        if abstract:
            abstract_excerpt = abstract[:max_abstract_excerpt_chars]
            if len(abstract) > max_abstract_excerpt_chars:
                abstract_excerpt = abstract_excerpt.rstrip() + "…"

        doi, pmcid = _extract_identifiers(pubmed_article)
        articles.append(
            LiteratureArticle(
                pmid=pmid,
                title=title,
                journal=journal,
                publication_date=publication_date,
                publication_date_text=publication_date_text,
                authors=authors,
                doi=doi,
                pmcid=pmcid,
                publication_types=publication_types,
                abstract_available=bool(abstract),
                abstract_sha256=abstract_hash,
                abstract_excerpt=abstract_excerpt,
                pubmed_url=f"{PUBMED_BASE}/{pmid}/",
                source_verified=True,
            )
        )
    return articles


class PubMedClient:
    """Small PubMed E-utilities client using ESearch followed by one batched EFetch.

    NCBI recommends including tool and email parameters on E-utility requests. The
    client performs only two requests per search, well below the default three
    requests/second ceiling for ordinary use without an API key.
    """

    def __init__(
        self,
        *,
        email: str,
        tool: str = "cancer_tumor_board_intelligence",
        api_key: str | None = None,
        transport: Callable[[str, float], bytes] | None = None,
        timeout: float = 15.0,
    ) -> None:
        if not email.strip():
            raise ValueError("PubMedClient requires a non-empty contact email for NCBI E-utilities.")
        self.email = email.strip()
        self.tool = tool.strip() or "cancer_tumor_board_intelligence"
        self.api_key = api_key.strip() if api_key else None
        self.transport = transport or _http_get
        self.timeout = timeout

    def _url(self, endpoint: str, params: dict[str, str | int]) -> str:
        common: dict[str, str | int] = {
            "tool": self.tool,
            "email": self.email,
        }
        if self.api_key:
            common["api_key"] = self.api_key
        common.update(params)
        return f"{EUTILS_BASE}/{endpoint}?{urlencode(common)}"

    def search(self, query: str, *, retmax: int = 10, sort: str = "pub date") -> PubMedSearchResult:
        if not query.strip():
            raise ValueError("PubMed search query cannot be empty.")
        retmax = max(1, min(50, int(retmax)))
        url = self._url(
            "esearch.fcgi",
            {
                "db": "pubmed",
                "term": query,
                "retmode": "xml",
                "retmax": retmax,
                "sort": sort,
            },
        )
        try:
            payload = self.transport(url, self.timeout)
            root = ET.fromstring(payload)
        except Exception as exc:
            raise PubMedClientError(f"PubMed ESearch failed: {exc}") from exc
        pmids = tuple(_text(node) for node in root.findall("./IdList/Id") if _text(node))
        return PubMedSearchResult(query=query, pmids=pmids)

    def fetch(self, pmids: list[str] | tuple[str, ...]) -> list[LiteratureArticle]:
        clean_pmids = [str(p).strip() for p in pmids if str(p).strip()]
        if not clean_pmids:
            return []
        url = self._url(
            "efetch.fcgi",
            {
                "db": "pubmed",
                "id": ",".join(clean_pmids),
                "retmode": "xml",
            },
        )
        try:
            payload = self.transport(url, self.timeout)
        except Exception as exc:
            raise PubMedClientError(f"PubMed EFetch failed: {exc}") from exc
        return parse_pubmed_xml(payload)

    def search_and_fetch(self, query: str, *, retmax: int = 10, sort: str = "pub date") -> tuple[PubMedSearchResult, list[LiteratureArticle]]:
        search_result = self.search(query, retmax=retmax, sort=sort)
        articles = self.fetch(search_result.pmids)
        order = {pmid: idx for idx, pmid in enumerate(search_result.pmids)}
        articles.sort(key=lambda article: order.get(article.pmid, 10**9))
        return search_result, articles
