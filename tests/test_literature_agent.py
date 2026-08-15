from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from agents.literature import LiteratureAgent, build_pubmed_query
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MolecularFinding, Provenance
from services.pubmed_client import PubMedClient, PubMedClientError, parse_pubmed_xml


def _fact(field: str, value: str) -> Fact:
    return Fact(
        field=field,
        value=value,
        provenance=[Provenance(
            document_id="LIT-TEST",
            source_excerpt=value,
            source_segment_ids=["S0001"],
            source_verified=True,
        )],
    )


def _case(*, question_type: str = "management", question: str = "What treatment should be discussed?") -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="LIT-001",
        diagnosis=_fact("diagnosis", "acute myeloid leukemia"),
        disease_state=_fact("disease_state", "relapsed"),
        performance_status=_fact("ECOG", "1"),
        clinical_question=ClinicalQuestion(question_type=question_type, question=question),
    )


ESEARCH_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<eSearchResult><Count>2</Count><RetMax>2</RetMax><RetStart>0</RetStart><IdList><Id>111</Id><Id>222</Id></IdList></eSearchResult>
"""

EFETCH_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>111</PMID>
      <Article>
        <ArticleTitle>Relapsed acute myeloid leukemia therapy study</ArticleTitle>
        <Abstract><AbstractText>Structured abstract text for deterministic parser testing.</AbstractText></Abstract>
        <AuthorList><Author><LastName>Smith</LastName><Initials>AB</Initials></Author></AuthorList>
        <Journal><Title>Test Journal</Title><JournalIssue><PubDate><Year>2026</Year><Month>Aug</Month><Day>1</Day></PubDate></JournalIssue></Journal>
        <PublicationTypeList><PublicationType>Clinical Trial</PublicationType></PublicationTypeList>
      </Article>
    </MedlineCitation>
    <PubmedData><ArticleIdList><ArticleId IdType='pubmed'>111</ArticleId><ArticleId IdType='doi'>10.1000/test.111</ArticleId><ArticleId IdType='pmc'>PMC111</ArticleId></ArticleIdList></PubmedData>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>222</PMID>
      <Article>
        <ArticleTitle>Another AML treatment publication</ArticleTitle>
        <AuthorList><Author><CollectiveName>AML Study Group</CollectiveName></Author></AuthorList>
        <Journal><Title>Another Journal</Title><JournalIssue><PubDate><MedlineDate>2025 Dec-Jan</MedlineDate></PubDate></JournalIssue></Journal>
        <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
      </Article>
    </MedlineCitation>
    <PubmedData><ArticleIdList><ArticleId IdType='pubmed'>222</ArticleId></ArticleIdList></PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_build_query_uses_structured_concepts_not_free_text_question() -> None:
    case = _case(question="Patient John Doe asks whether treatment X should be used.")
    query, terms = build_pubmed_query(case)
    assert "acute myeloid leukemia" in query
    assert "relapsed" in query
    assert "John Doe" not in query
    assert "treatment X" not in query
    assert "treatment/therapy" in terms


def test_build_query_adds_molecular_gene_without_claiming_actionability() -> None:
    case = _case(question_type="molecular_management", question="How should FLT3 be considered?")
    case.molecular_findings.append(MolecularFinding(gene="FLT3", alteration_type="ITD"))
    query, terms = build_pubmed_query(case)
    assert '"FLT3"[Title/Abstract]' in query
    assert "FLT3" in terms


def test_parse_pubmed_xml_extracts_verified_metadata_and_hash() -> None:
    articles = parse_pubmed_xml(EFETCH_XML)
    assert [article.pmid for article in articles] == ["111", "222"]
    first = articles[0]
    assert first.title == "Relapsed acute myeloid leukemia therapy study"
    assert first.journal == "Test Journal"
    assert first.publication_date.isoformat() == "2026-08-01"
    assert first.authors == ["Smith AB"]
    assert first.doi == "10.1000/test.111"
    assert first.pmcid == "PMC111"
    assert first.abstract_available is True
    assert first.abstract_sha256 is not None
    assert first.source_verified is True
    second = articles[1]
    assert second.authors == ["AML Study Group"]
    assert second.publication_date.year == 2025
    assert second.abstract_available is False


def test_pubmed_client_uses_esearch_then_one_batched_efetch() -> None:
    calls: list[str] = []

    def transport(url: str, timeout: float) -> bytes:
        calls.append(url)
        if "esearch.fcgi" in url:
            return ESEARCH_XML
        if "efetch.fcgi" in url:
            return EFETCH_XML
        raise AssertionError(url)

    client = PubMedClient(email="test@example.org", transport=transport)
    search, articles = client.search_and_fetch('"acute myeloid leukemia"[Title/Abstract]', retmax=10)
    assert search.pmids == ("111", "222")
    assert [a.pmid for a in articles] == ["111", "222"]
    assert len(calls) == 2
    esearch_params = parse_qs(urlparse(calls[0]).query)
    assert esearch_params["db"] == ["pubmed"]
    assert esearch_params["tool"] == ["cancer_tumor_board_intelligence"]
    assert esearch_params["email"] == ["test@example.org"]
    efetch_params = parse_qs(urlparse(calls[1]).query)
    assert efetch_params["id"] == ["111,222"]


def test_literature_agent_fails_safe_when_no_client_is_configured() -> None:
    report = LiteratureAgent().run(_case())
    assert report.status == "source_unavailable"
    assert report.articles == []
    assert report.can_support_literature_claim is False


def test_literature_agent_retrieves_candidates_but_does_not_support_claim() -> None:
    def transport(url: str, timeout: float) -> bytes:
        return ESEARCH_XML if "esearch.fcgi" in url else EFETCH_XML

    client = PubMedClient(email="test@example.org", transport=transport)
    report = LiteratureAgent(client, retmax=10).run(_case())
    assert report.status == "completed_with_limitations"
    assert len(report.articles) == 2
    assert report.search_trace is not None
    assert report.search_trace.retrieved_pmids == ["111", "222"]
    assert report.can_support_literature_claim is False
    assert any("does not verify a clinical claim" in item for item in report.limitations)


def test_literature_agent_no_results_is_not_absence_of_evidence() -> None:
    empty_search = b"<eSearchResult><Count>0</Count><IdList></IdList></eSearchResult>"

    def transport(url: str, timeout: float) -> bytes:
        return empty_search

    client = PubMedClient(email="test@example.org", transport=transport)
    report = LiteratureAgent(client).run(_case())
    assert report.status == "no_evidence_found"
    assert report.articles == []
    assert any("does not establish absence of evidence" in item for item in report.limitations)


def test_literature_agent_tool_failure_propagates_no_claim() -> None:
    def transport(url: str, timeout: float) -> bytes:
        raise TimeoutError("synthetic timeout")

    client = PubMedClient(email="test@example.org", transport=transport)
    report = LiteratureAgent(client).run(_case())
    assert report.status == "tool_failure"
    assert report.articles == []
    assert report.can_support_literature_claim is False


def test_client_requires_contact_email() -> None:
    try:
        PubMedClient(email="")
    except ValueError as exc:
        assert "contact email" in str(exc)
    else:
        raise AssertionError("Expected PubMedClient to reject empty contact email")
