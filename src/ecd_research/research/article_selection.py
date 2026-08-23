"""Choose PubMed articles most suitable for abstract-limited extraction."""

from __future__ import annotations

import re

from ecd_research.models import PubMedArticle
from ecd_research.research.search_strategy import expand_terms

_MIN_ABSTRACT_LEN = 80


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _relevance_score(article: PubMedArticle, question: str) -> int:
    """Higher = more likely useful for the research question."""
    haystack = _normalize(
        " ".join(
            filter(
                None,
                [article.title, article.abstract, article.journal],
            )
        )
    )
    score = 0
    if len(article.abstract or "") >= _MIN_ABSTRACT_LEN:
        score += 2
    elif article.title:
        score += 1

    matched = expand_terms(question)
    for terms in matched.values():
        for term in terms:
            if _normalize(term) in haystack:
                score += 3

    # Lightweight cues when vocabulary didn't match query wording.
    for token in (
        "neuro",
        "cns",
        "brain",
        "cerebell",
        "suprasellar",
        "meninge",
        "stroke",
        "braf",
        "mek",
        "dabrafenib",
        "trametinib",
        "vemurafenib",
        "cobimetinib",
        "mapk",
        "mutation",
        "targeted",
    ):
        if token in haystack:
            score += 2

    return score


def select_articles_for_extraction(
    articles: list[PubMedArticle],
    question: str,
    *,
    max_articles: int = 5,
    scan_limit: int = 25,
) -> list[PubMedArticle]:
    """Pick up to ``max_articles`` with abstracts/relevance, scanning ``scan_limit`` candidates."""
    if max_articles < 1:
        raise ValueError("max_articles must be >= 1")

    candidates = articles[:scan_limit]
    ranked = sorted(
        candidates,
        key=lambda a: (_relevance_score(a, question), len(a.abstract or "")),
        reverse=True,
    )

    selected: list[PubMedArticle] = []
    for article in ranked:
        if len(selected) >= max_articles:
            break
        if not (article.abstract and len(article.abstract.strip()) >= _MIN_ABSTRACT_LEN):
            continue
        selected.append(article)
    return selected
