from __future__ import annotations

from agents.literature import LiteratureAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact
from schemas.literature import LiteratureArticle


class StubClient:
    def __init__(self, articles):
        self.articles = articles

    def search_and_fetch(self, query, *, retmax=10, sort="pub date"):
        class SearchResult:
            pmids = tuple(article.pmid for article in self.articles)
        result = SearchResult()
        result.articles = self.articles
        return result, list(self.articles)


def _case(age):
    return CancerTumorBoardCase(
        case_id="lit-pop",
        age=age,
        diagnosis=Fact(field="diagnosis", value="Acute myeloid leukemia"),
        disease_state=Fact(field="disease_state", value="relapsed"),
        clinical_question=ClinicalQuestion(question_type="management", question="What treatment strategies are relevant?"),
    )


def _article(pmid, title):
    return LiteratureArticle(pmid=pmid, title=title, pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")


def test_pediatric_title_is_not_surfaced_for_older_adult():
    client = StubClient([
        _article("1", "Therapy in pediatric acute myeloid leukemia"),
        _article("2", "Therapy in relapsed acute myeloid leukemia"),
    ])
    report = LiteratureAgent(client).run(_case(68))
    assert report.status == "completed_with_limitations"
    assert [article.pmid for article in report.articles] == ["2"]
    assert any("age-population mismatch" in warning for warning in report.warnings)


def test_unknown_age_does_not_trigger_population_exclusion():
    client = StubClient([_article("1", "Therapy in pediatric acute myeloid leukemia")])
    report = LiteratureAgent(client).run(_case(None))
    assert report.status == "completed_with_limitations"
    assert len(report.articles) == 1
