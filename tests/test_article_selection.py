"""Tests for extraction article selection."""

from ecd_research.models import PubMedArticle
from ecd_research.research.article_selection import select_articles_for_extraction


def _art(pmid: str, title: str, abstract: str | None) -> PubMedArticle:
    return PubMedArticle(
        pmid=pmid,
        title=title,
        abstract=abstract,
        pubmed_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    )


def test_prefers_neurological_abstract_over_empty_newest() -> None:
    articles = [
        _art("1", "New ECD paper", None),
        _art("2", "Renal ECD", "x" * 100),
        _art(
            "3",
            "CNS involvement in Erdheim-Chester disease",
            "Neurological symptoms included cerebellar ataxia. " + ("x" * 100),
        ),
    ]
    selected = select_articles_for_extraction(
        articles,
        "What is the evidence for neurological ECD?",
        max_articles=2,
    )
    assert [a.pmid for a in selected] == ["3", "2"]
