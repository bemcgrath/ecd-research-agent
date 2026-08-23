"""Tests for ECD vocabulary and PubMed search strategy expansion."""

from __future__ import annotations

import pytest

from ecd_research.research.search_strategy import (
    expand_terms,
    generate_pubmed_queries,
    generate_search_strategy,
)
from ecd_research.research.vocabulary import load_vocabulary


def test_load_vocabulary_has_expected_categories() -> None:
    vocab = load_vocabulary()
    assert "disease" in vocab
    assert "molecular" in vocab
    assert "treatment" in vocab
    assert "organ" in vocab
    assert "Erdheim-Chester disease" in vocab["disease"]
    assert "Langerhans cell histiocytosis" in vocab["disease"]
    assert "BRAF V600E" in vocab["molecular"]


def test_expand_terms_matches_neuro_and_molecular() -> None:
    matched = expand_terms(
        "What treatments exist for neurological ECD with BRAF V600E?"
    )
    assert "organ" in matched
    assert any("neuro" in t.lower() or t.upper() == "CNS" for t in matched["organ"])
    assert "molecular" in matched
    assert "BRAF V600E" in matched["molecular"]


def test_generate_pubmed_queries_includes_disease_and_facets() -> None:
    queries = generate_pubmed_queries(
        "Evidence for MEK inhibition in CNS Erdheim-Chester disease"
    )
    assert queries[0] == '"Erdheim-Chester disease"'
    assert any("CNS" in q or "neurologic" in q for q in queries)
    assert any("MEK" in q or "trametinib" in q or "cobimetinib" in q for q in queries)


def test_generate_search_strategy_structure() -> None:
    strategy = generate_search_strategy(
        "How does BRAF status affect treatment of cardiac ECD?"
    )
    assert strategy.question.startswith("How does BRAF")
    assert "molecular" in strategy.focus_categories or "BRAF" in strategy.matched_terms
    assert strategy.pubmed_queries
    assert all("Erdheim-Chester disease" in q for q in strategy.pubmed_queries)


def test_invalid_question() -> None:
    with pytest.raises(ValueError):
        expand_terms("")
    with pytest.raises(ValueError):
        generate_pubmed_queries("ECD", max_queries=0)
