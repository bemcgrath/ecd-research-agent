"""Select PubMed articles likely to be case reports or case series."""

from __future__ import annotations

import re

from ecd_research.models import PubMedArticle
from ecd_research.research.search_strategy import expand_terms

_MIN_ABSTRACT_LEN = 80

_CASE_MARKERS = (
    "case report",
    "case series",
    "case presentation",
    "patients were",
    "patient was",
    "we report",
    "we describe",
    "here we report",
    "herein we report",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _case_report_score(article: PubMedArticle, question: str) -> int:
    """Higher = more likely a case report/series relevant to the question."""
    haystack = _normalize(
        " ".join(filter(None, [article.title, article.abstract, article.journal]))
    )
    score = 0

    if len(article.abstract or "") >= _MIN_ABSTRACT_LEN:
        score += 2
    elif article.title:
        score += 1

    for marker in _CASE_MARKERS:
        if marker in haystack:
            score += 4

    matched = expand_terms(question)
    for terms in matched.values():
        for term in terms:
            if _normalize(term) in haystack:
                score += 3

    for token in (
        "cns",
        "neuro",
        "brain",
        "cerebell",
        "braf",
        "mek",
        "dabrafenib",
        "trametinib",
        "vemurafenib",
        "histiocyt",
        "erdheim",
        "langerhans",
    ):
        if token in haystack:
            score += 2

    return score


def select_case_report_articles(
    articles: list[PubMedArticle],
    question: str,
    *,
    max_articles: int = 10,
    scan_limit: int = 40,
    min_score: int = 4,
) -> list[PubMedArticle]:
    """Pick case-report-like articles with abstracts, ranked by relevance."""
    if max_articles < 1:
        raise ValueError("max_articles must be >= 1")

    candidates = articles[:scan_limit]
    ranked = sorted(
        candidates,
        key=lambda a: (_case_report_score(a, question), len(a.abstract or "")),
        reverse=True,
    )

    selected: list[PubMedArticle] = []
    for article in ranked:
        if len(selected) >= max_articles:
            break
        if not (article.abstract and len(article.abstract.strip()) >= _MIN_ABSTRACT_LEN):
            continue
        if _case_report_score(article, question) < min_score:
            continue
        selected.append(article)
    return selected
