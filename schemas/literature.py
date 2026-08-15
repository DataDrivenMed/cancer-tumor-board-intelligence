from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class LiteratureArticle(BaseModel):
    pmid: str
    title: str
    journal: str | None = None
    publication_date: date | None = None
    publication_date_text: str | None = None
    authors: list[str] = Field(default_factory=list)
    doi: str | None = None
    pmcid: str | None = None
    publication_types: list[str] = Field(default_factory=list)
    abstract_available: bool = False
    abstract_sha256: str | None = None
    abstract_excerpt: str | None = None
    pubmed_url: str
    source_verified: bool = True


class LiteratureSearchTrace(BaseModel):
    query: str
    database: str = "pubmed"
    sort: str = "pub date"
    requested_limit: int
    retrieved_pmids: list[str] = Field(default_factory=list)
    retrieved_count: int = 0
    query_terms: list[str] = Field(default_factory=list)


class LiteratureReport(BaseModel):
    agent_id: str = "literature"
    agent_version: str = "1.0.0"
    case_id: str
    status: Literal[
        "completed",
        "completed_with_limitations",
        "no_evidence_found",
        "source_unavailable",
        "tool_failure",
        "abstain_domain",
    ]
    search_trace: LiteratureSearchTrace | None = None
    articles: list[LiteratureArticle] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str
    can_support_literature_claim: bool = False
