"""Research search strategy: expand questions into PubMed queries."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from ecd_research.research.vocabulary import load_vocabulary

PRIMARY_DISEASE_TERM = "Erdheim-Chester disease"


class SearchStrategy(BaseModel):
    """Expanded search plan derived from a research question."""

    question: str
    focus_categories: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    pubmed_queries: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def expand_terms(
    question: str,
    *,
    vocabulary: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """Return vocabulary terms mentioned in the question, by category."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    vocab = vocabulary or load_vocabulary()
    haystack = _normalize(question)
    matched: dict[str, list[str]] = {}

    for category, terms in vocab.items():
        # Longer phrases first so "BRAF V600E" wins over "BRAF".
        for term in sorted(terms, key=len, reverse=True):
            needle = _normalize(term)
            if not needle:
                continue
            # Word-ish boundary for short tokens like ECD / MEK / CNS.
            if len(needle) <= 4:
                pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
                if not re.search(pattern, haystack):
                    continue
            elif needle not in haystack:
                continue
            matched.setdefault(category, [])
            if term not in matched[category]:
                matched[category].append(term)
    return matched


def generate_pubmed_queries(
    question: str,
    *,
    vocabulary: dict[str, list[str]] | None = None,
    max_queries: int = 12,
) -> list[str]:
    """Build PubMed Boolean queries from disease + matched facet terms."""
    if max_queries < 1:
        raise ValueError("max_queries must be >= 1")

    matched = expand_terms(question, vocabulary=vocabulary)
    queries: list[str] = [f'"{PRIMARY_DISEASE_TERM}"']

    # Prefer organ / molecular / treatment facets for AND expansions.
    priority: list[Literal["organ", "molecular", "treatment", "disease"]] = [
        "organ",
        "molecular",
        "treatment",
        "disease",
    ]
    for category in priority:
        for term in matched.get(category, []):
            if category == "disease" and _normalize(term) in {
                _normalize(PRIMARY_DISEASE_TERM),
                "ecd",
                "erdheim chester disease",
            }:
                continue
            candidate = f'"{PRIMARY_DISEASE_TERM}" AND "{term}"'
            if candidate not in queries:
                queries.append(candidate)
            if len(queries) >= max_queries:
                return queries

    # If nothing matched, add a few high-value default CNS/molecular probes
    # only when the question text suggests neurological or molecular intent.
    haystack = _normalize(question)
    defaults: list[str] = []
    if any(tok in haystack for tok in ("neuro", "cns", "brain", "cerebell")):
        defaults.extend(["CNS", "neurologic", "brain", "cerebellar"])
    if any(tok in haystack for tok in ("braf", "mek", "mapk", "molecular", "mutation")):
        defaults.extend(["BRAF", "MEK", "vemurafenib", "cobimetinib", "trametinib"])
    if any(tok in haystack for tok in ("treat", "therapy", "inhibitor", "drug")):
        defaults.extend(["vemurafenib", "cobimetinib", "trametinib", "interferon"])

    for term in defaults:
        candidate = f'"{PRIMARY_DISEASE_TERM}" AND "{term}"'
        if candidate not in queries:
            queries.append(candidate)
        if len(queries) >= max_queries:
            break

    return queries[:max_queries]


def generate_search_strategy(
    question: str,
    *,
    vocabulary: dict[str, list[str]] | None = None,
    max_queries: int = 12,
) -> SearchStrategy:
    """Produce a full search strategy object for a research question."""
    matched = expand_terms(question, vocabulary=vocabulary)
    queries = generate_pubmed_queries(
        question, vocabulary=vocabulary, max_queries=max_queries
    )
    flat_terms = [t for terms in matched.values() for t in terms]
    notes: list[str] = [
        "Queries are PubMed Boolean strings; disease term is always included.",
        "Vocabulary is loaded from configurable YAML (not hard-coded in callers).",
    ]
    if not flat_terms:
        notes.append(
            "No vocabulary terms matched directly; defaults may be added from question cues."
        )
    return SearchStrategy(
        question=question.strip(),
        focus_categories=sorted(matched.keys()),
        matched_terms=flat_terms,
        pubmed_queries=queries,
        notes=notes,
    )
