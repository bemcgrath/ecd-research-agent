"""Shared data models for ECD research tools."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class PubMedArticle(BaseModel):
    """A PubMed article with metadata taken only from NCBI responses."""

    pmid: str
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    journal: str | None = None
    publication_date: str | None = None
    abstract: str | None = None
    doi: str | None = None
    pubmed_url: HttpUrl
